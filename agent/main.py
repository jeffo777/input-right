import asyncio
import logging
import os
import aiohttp
import json
from dotenv import load_dotenv

# Load environment variables *before* they are used
load_dotenv()

from livekit import agents
from livekit.agents import JobRequest, function_tool, get_job_context 
from livekit import rtc
from livekit.plugins import deepgram, cartesia, groq, silero

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
            f"Once you have naturally collected the user's name, their specific inquiry, and a contact detail (phone or email), "
            f"you MUST call the `present_verification_form` tool. Do not ask for the information again if you already have it, just call the tool. "
            f"If the user is just asking questions, simply answer them and remain helpful. Do not push to capture their details. "
            f"Business Information: {contractor_profile['knowledge_base']}"
        )
        super().__init__(instructions=instructions)

    @function_tool()
    async def present_verification_form(self, name: str, inquiry: str, contact_detail: str):
        """
        Call this tool ONLY when the user has asked to be contacted and you have collected their name, inquiry, and contact detail.
        This tool will display a form on the user's screen for them to verify their information.
        Args:
            name (str): The full name of the user.
            inquiry (str): A summary of what the user is asking for (e.g., 'quote for a leaky pipe').
            contact_detail (str): The user's phone number or email address.
        """
        logging.info(f"LLM triggered present_verification_form with: {name}, {inquiry}, {contact_detail}")
        
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
            "contact_detail": contact_detail,
        }
        try:
            await room.local_participant.perform_rpc(
                destination_identity=visitor_participant.identity,
                method="display_lead_form",
                payload=json.dumps(payload)
            )
            logging.info(f"Successfully sent RPC to {visitor_participant.identity}")
            return None
        except Exception as e:
            logging.error(f"Failed to send RPC: {e}")
            return f"Error: Failed to display the form to the user due to an internal error: {e}"

    async def _submit_lead_form_handler(self, data: rtc.RpcInvocationData):
        """This is the handler for the RPC call from the frontend."""
        logging.info(f"Agent received submit_lead_form RPC with payload: {data.payload}")
        try:
            lead_data = json.loads(data.payload)

            async with aiohttp.ClientSession() as http_session:
                url = f"{INTERNAL_API_URL}/api/internal/leads"
                headers = {"Authorization": INTERNAL_API_KEY}
                async with http_session.post(url, headers=headers, json=lead_data) as response:
                    if response.status == 201:
                        logging.info("Successfully saved lead to the database.")
                        await self.session.generate_reply(
                            instructions="The user's information has been successfully saved. Thank them and ask if there is anything else you can help with."
                        )
                    else:
                        logging.error(f"Failed to save lead. Status: {response.status}, Body: {await response.text()}")
                        await self.session.say("I'm sorry, there was an error saving your information. Please try again in a moment.")

        except Exception as e:
            logging.error(f"Error processing submit_lead_form RPC: {e}")
            await self.session.say("I'm sorry, a technical error occurred. Please try again.")

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
    
    contractor_id = ctx.room.name
    
    try:
        async with aiohttp.ClientSession() as http_session:
            profile = await fetch_contractor_profile(http_session, contractor_id)
    except Exception as e:
        logging.error(f"Could not start agent session, failed to get profile: {e}")
        return

    stt = deepgram.STT()
    tts = cartesia.TTS()
    llm = groq.LLM(model="llama-3.3-70b-versatile")
    vad = silero.VAD.load()

    session = agents.AgentSession(stt=stt, llm=llm, tts=tts, vad=vad)
    agent = ContractorAgent(profile)
    
    await session.start(room=ctx.room, agent=agent)

    # Register the RPC handler after the session has started
    ctx.room.local_participant.register_rpc_method(
        "submit_lead_form", agent._submit_lead_form_handler
    )

    await session.say(f"Thank you for calling {profile['business_name']}. How can I help you today?", allow_interruptions=True)

async def request_fnc(req: JobRequest):
    logging.info(f"Accepting job {req.job.id}")
    await req.accept(identity="contractor-leads-bot-agent")

if __name__ == "__main__":
    logging.info("Starting Contractor Leads Bot Agent Worker...")
    
    agents.cli.run_app(
        agents.WorkerOptions(
            request_fnc=request_fnc,
            entrypoint_fnc=entrypoint
        )
    )