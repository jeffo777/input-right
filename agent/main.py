import asyncio
import logging
import os
import aiohttp
import json
from dotenv import load_dotenv

# Load environment variables *before* they are used
load_dotenv()

from livekit import agents
# This is the corrected import path for the event and state enum
from livekit.agents import JobRequest, function_tool, get_job_context, UserStateChangedEvent
from livekit import rtc
from livekit.plugins import deepgram, groq, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INTERNAL_API_URL = os.getenv("INTERNAL_API_URL")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

class ContractorAgent(agents.Agent):
    def __init__(self, contractor_profile: dict):
        instructions = (
            f"You are a friendly and helpful digital receptionist for {contractor_profile['business_name']}. "
            f"Your primary goal is to answer the user's questions based on the business information provided. "
            f"Your secondary goal is to capture new customer leads, but ONLY if the user expresses a desire to be contacted. "
            f"If the user asks for a quote, a callback, or a service visit, that is your cue to collect their information. "
            f"You must collect their name, their specific inquiry, and their email address. A phone number is optional, but you can ask for it if it seems appropriate. "
            f"Once you have naturally collected the user's name, their inquiry, and their email address, "
            f"you MUST call the `present_verification_form` tool. "
            f"After you call the tool and receive the confirmation message 'The verification form was successfully displayed to the user.', "
            f"your next response MUST be to instruct the user to check the details on the form and click the send button if they are correct. "
            f"Also, let them know they can either edit the form directly or tell you if they want to make any changes. "
            f"If the user asks you to change any of the details while the form is displayed, you MUST call the `present_verification_form` tool again with the updated information. "
            f"If the user is just asking questions, simply answer them and remain helpful. Do not push to capture their details. "
            f"Business Information: {contractor_profile['knowledge_base']}"
        )
        super().__init__(instructions=instructions)
        # This flag tracks if the form is active on the user's screen
        self._is_form_displayed = False

    @function_tool()
    async def present_verification_form(self, name: str, inquiry: str, email: str, phone: str | None = None):
        """
        Call this tool ONLY when the user has asked to be contacted and you have collected their name, inquiry, and email address.
        This tool will display a form on the user's screen for them to verify their information.
        Args:
            name (str): The full name of the user.
            inquiry (str): A summary of what the user is asking for (e.g., 'quote for a leaky pipe').
            email (str): The user's email address. This is required.
            phone (str, optional): The user's phone number. This is optional.
        """
        logging.info(f"LLM triggered present_verification_form with: name='{name}', inquiry='{inquiry}', email='{email}', phone='{phone}'")

        ctx = get_job_context()
        room = ctx.room

        await self.session.say("Great. Please take a moment to verify your details on the screen.", allow_interruptions=False)

        visitor_participant = next(iter(room.remote_participants.values()), None)
        if not visitor_participant:
            logging.error("Could not find a remote participant to send RPC to.")
            return "Error: Could not find the user to display the form."

        payload = {
            "name": name,
            "inquiry": inquiry,
            "email": email,
            "phone": phone,
        }
        try:
            await room.local_participant.perform_rpc(
                destination_identity=visitor_participant.identity,
                method="display_lead_form",
                payload=json.dumps(payload)
            )
            logging.info(f"Successfully sent RPC to {visitor_participant.identity}")
            self._is_form_displayed = True # Set the flag to True
            return "The verification form was successfully displayed to the user."
        except Exception as e:
            logging.error(f"Failed to send RPC: {e}")
            return "Error: There was a technical problem displaying the form to the user."

async def fetch_contractor_profile(session: aiohttp.ClientSession, contractor_id: str) -> dict:
    url = f"{INTERNAL_API_URL}/api/internal/contractors/{contractor_id}"
    headers = {"Authorization": INTERNAL_API_KEY}
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            logging.error(f"Failed to fetch contractor profile: {response.status}")
            raise Exception(f"Contractor not found: {contractor_id}")
        return await response.json()

async def entrypoint(ctx: agents.JobContext):
    logging.info(f"Agent received job: {ctx.job.id} for room {ctx.room.name}")
    
    session_ended = asyncio.Event()
    greeting_allowed = asyncio.Event()

    # Set up event listeners before connecting to the room to avoid missing initial events.
    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        # Once we have subscribed to the user's audio track, we can greet them
        if track.kind == rtc.TrackKind.KIND_AUDIO and not participant.identity.startswith("contractor-leads-bot-agent"):
            logging.info("AGENT: User audio track subscribed. Allowing greeting.")
            greeting_allowed.set()

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        logging.info(f"Participant disconnected: {participant.identity}, closing session.")
        session_ended.set()

    async with aiohttp.ClientSession() as http_session:
        try:
            # The room name is now "contractor_id-conversation_id".
            # We need to extract just the contractor_id part.
            # This splits the string by '-' and rejoins all but the last part.
            # The room name is now "contractor_id_conversation_id".
            # We can reliably split by the first underscore.
            contractor_id = ctx.room.name.split('_')[0]
            profile = await fetch_contractor_profile(http_session, contractor_id)

            # Now, connect to the room
            await ctx.connect()
            logging.info("Agent connected to the room.")

        except Exception as e:
            logging.error(f"Could not start agent session during setup: {e}")
            ctx.shutdown()
            return

        stt = deepgram.STT()
        tts = ctx.proc.userdata["tts"]
        llm = groq.LLM(model="llama-3.3-70b-versatile")
        vad = silero.VAD.load()
        turn = MultilingualModel()

        session = agents.AgentSession(stt=stt, llm=llm, tts=tts, vad=vad, turn_detection=turn)
        agent = ContractorAgent(profile)

        @session.on("user_state_changed")
        def on_user_state_changed(ev: UserStateChangedEvent):
            if ev.new_state == "away" and agent._is_form_displayed:
                logging.info("User is viewing the form, ignoring away state to prevent session timeout.")
                return
            if ev.new_state == "away":
                logging.info("User is away and no form is displayed, closing session.")
                session_ended.set()

        async def submit_lead_form_handler(data: rtc.RpcInvocationData):
            """
            This handler is called when the frontend sends the 'submit_lead_form' RPC.
            It immediately interrupts any agent speech, acknowledges the RPC to prevent a timeout,
            and then processes the lead submission in the background.
            """
            # 1. Immediately interrupt any ongoing speech for a responsive feel.
            session.interrupt()
            logging.info(f"Agent received submit_lead_form RPC with payload: {data.payload}")

            async def _process_submission():
                """Inner function to handle the actual logic in the background."""
                try:
                    agent._is_form_displayed = False
                    frontend_data = json.loads(data.payload)
                    
                    contractor_id = ctx.room.name.split('_')[0]

                    backend_payload = {
                        "contractor_id": contractor_id,
                        "visitor_name": frontend_data.get("name"),
                        "inquiry": frontend_data.get("inquiry"),
                        "visitor_email": frontend_data.get("email"),
                        "visitor_phone": frontend_data.get("phone"),
                    }
                    url = f"{INTERNAL_API_URL}/api/internal/leads"
                    headers = {"Authorization": INTERNAL_API_KEY}
                    async with http_session.post(url, headers=headers, json=backend_payload) as response:
                        if response.status == 201:
                            logging.info("Successfully saved lead to the database.")
                            await session.say(
                                "Thank you. Your information has been sent. Was there anything else I can help you with today?",
                                allow_interruptions=True
                            )
                        else:
                            logging.error(f"Failed to save lead. Status: {response.status}, Body: {await response.text()}")
                            await session.say("I'm sorry, there was an error saving your information. Please try again in a moment.")
                except Exception as e:
                    logging.error(f"Error processing submit_lead_form RPC in background: {e}")
                    await session.say("I'm sorry, a technical error occurred. Please try again.")

            # 2. Start the submission processing in the background.
            asyncio.create_task(_process_submission())

            # 3. Immediately return a success message to the frontend to prevent timeout.
            return "SUCCESS"

        logging.info("AGENT: Attempting to start AgentSession...")
        await session.start(room=ctx.room, agent=agent)
        logging.info("AGENT: AgentSession started.")

        ctx.room.local_participant.register_rpc_method(
            "submit_lead_form", submit_lead_form_handler
        )

        try:
            logging.info("AGENT: Waiting for a user to connect with an audio track...")
            await asyncio.wait_for(greeting_allowed.wait(), timeout=20.0)
            logging.info("AGENT: Greeting is allowed. Attempting to say initial greeting...")
            await session.say(f"Thank you for calling {profile['business_name']}. How can I help you today?", allow_interruptions=True)
            logging.info("AGENT: Finished saying initial greeting.")
        except asyncio.TimeoutError:
            logging.warning("AGENT: Timed out waiting for user audio track. Not sending greeting.")
            session_ended.set()

        await session_ended.wait()
        await session.aclose()

    ctx.shutdown()

async def request_fnc(req: JobRequest):
    logging.info(f"Accepting job {req.job.id}")
    await req.accept(identity="contractor-leads-bot-agent")

# v-- THIS ENTIRE FUNCTION IS NEW --v
def prewarm(proc: agents.JobProcess):
    # This function is called once when the worker process starts.
    # We create the TTS client here to handle its slow initial setup.
    proc.userdata["tts"] = groq.TTS(model="playai-tts", voice="Arista-PlayAI")
# ^-- THIS ENTIRE FUNCTION IS NEW --^

if __name__ == "__main__":
    logging.info("Starting Contractor Leads Bot Agent Worker...")

    agents.cli.run_app(
    agents.WorkerOptions(
        request_fnc=request_fnc,
        entrypoint_fnc=entrypoint,
        prewarm_fnc=prewarm  # <-- THIS LINE IS ADDED
    )
)