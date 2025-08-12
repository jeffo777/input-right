import asyncio
import logging
import os
import aiohttp
import json
from string import Template
from dotenv import load_dotenv

# Load environment variables from the .env file in this directory
load_dotenv()


from core_agent import BusinessAgent
from livekit import agents, rtc
from livekit.agents import JobRequest, UserStateChangedEvent
from livekit.agents import tts
from livekit.plugins import deepgram, groq, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get configuration from environment variables
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

async def entrypoint(ctx: agents.JobContext):
    logging.info(f"Agent received job: {ctx.job.id} for room {ctx.room.name}")
    
    session_ended = asyncio.Event()
    greeting_allowed = asyncio.Event()

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        if track.kind == rtc.TrackKind.KIND_AUDIO and not participant.identity.startswith("chat-to-form-agent"):
            logging.info("AGENT: User audio track subscribed. Allowing greeting.")
            greeting_allowed.set()

    @ctx.room.on("participant_disconnected")
    def on_participant_disconnected(participant):
        logging.info(f"Participant disconnected: {participant.identity}, closing session.")
        session_ended.set()

    try:
        # 1. Build the instructions from the local prompt.template and .env file
        with open("prompt.template", "r") as f:
            prompt_template = Template(f.read())
        
        instructions = prompt_template.substitute(
            business_name=os.getenv("BUSINESS_NAME", "the company"),
            knowledge_base=os.getenv("KNOWLEDGE_BASE", "No information provided.")
        )

        await ctx.connect()
        logging.info("Agent connected to the room.")

        # All model initialization and session logic is now safely inside the try block
        stt = deepgram.STT()
        llm = groq.LLM(model="llama-3.3-70b-versatile")
        tts = ctx.proc.userdata["tts"]
        vad = silero.VAD.load()
        turn = MultilingualModel()

        session = agents.AgentSession(stt=stt, llm=llm, tts=tts, vad=vad, turn_detection=turn)
        agent = BusinessAgent(instructions=instructions)

        @session.on("user_state_changed")
        def on_user_state_changed(ev: UserStateChangedEvent):
            if ev.new_state == "away" and agent._is_form_displayed:
                logging.info("User is viewing the form, ignoring away state.")
                return
            if ev.new_state == "away":
                logging.info("User is away and no form is displayed, closing session.")
                session_ended.set()

        async def submit_lead_form_handler(data: rtc.RpcInvocationData):
            session.interrupt()
            logging.info(f"Agent received submit_lead_form RPC with payload: {data.payload}")

            async def _process_submission():
                if not WEBHOOK_URL:
                    logging.error("WEBHOOK_URL is not set in the .env file. Cannot send lead.")
                    await session.say("I'm sorry, there is a configuration error and I can't save your information.")
                    return

                try:
                    agent._is_form_displayed = False
                    lead_data = json.loads(data.payload)
                    
                    async with aiohttp.ClientSession() as http_session:
                        headers = {"Content-Type": "application/json"}
                        async with http_session.post(WEBHOOK_URL, headers=headers, json=lead_data) as response:
                            if 200 <= response.status < 300:
                                logging.info(f"Successfully sent lead data to webhook: {WEBHOOK_URL}")
                                await session.say(
                                    "Thank you. Your information has been sent. Was there anything else I can help you with today?",
                                    allow_interruptions=True
                                )
                            else:
                                logging.error(f"Failed to send lead to webhook. Status: {response.status}")
                                await session.say("I'm sorry, there was an error sending your information.")
                except Exception as e:
                    logging.error(f"Error processing submit_lead_form RPC for webhook: {e}")
                    await session.say("I'm sorry, a technical error occurred.")

            asyncio.create_task(_process_submission())
            return "SUCCESS"

        await session.start(room=ctx.room, agent=agent)
        ctx.room.local_participant.register_rpc_method("submit_lead_form", submit_lead_form_handler)

        try:
            await asyncio.wait_for(greeting_allowed.wait(), timeout=20.0)
            await session.say(f"Thank you for calling {os.getenv('BUSINESS_NAME', 'the company')}. How can I help you today?", allow_interruptions=True)
        except asyncio.TimeoutError:
            logging.warning("Timed out waiting for user audio track. Not sending greeting.")
            session_ended.set()

        await session_ended.wait()
        await session.aclose()

    except Exception as e:
        logging.error(f"An unhandled error occurred in the entrypoint: {e}", exc_info=True)
    finally:
        ctx.shutdown()

async def request_fnc(req: JobRequest):
    logging.info(f"Accepting job {req.job.id} for open-source agent")
    await req.accept(identity="chat-to-form-agent")

def prewarm(proc: agents.JobProcess):
    # Load environment variables into the child process when it starts
    load_dotenv()
    logging.info("Prewarm: Environment variables loaded into child process.")

    # For stability, we will temporarily use only the Deepgram TTS client.
    proc.userdata["tts"] = deepgram.TTS(model="aura-asteria-en")
    logging.info("Prewarm complete for open-source agent: Deepgram TTS client initialized.")

if __name__ == "__main__":
    logging.info("Starting Chat To Form (Open Source) Agent Worker...")
    agents.cli.run_app(
        agents.WorkerOptions(
            request_fnc=request_fnc,
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm
        )
    )

