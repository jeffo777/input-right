import asyncio
import logging
import os
import aiohttp
from dotenv import load_dotenv

# Load environment variables *before* they are used
load_dotenv()

from livekit import agents
from livekit.agents import JobRequest
from livekit.plugins import deepgram, cartesia, google, silero

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

INTERNAL_API_URL = os.getenv("INTERNAL_API_URL")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

# This is the NEW, correct code
class ContractorAgent(agents.Agent):
    def __init__(self, contractor_profile: dict):
        instructions = (
            f"You are a friendly and helpful digital receptionist for {contractor_profile['business_name']}. "
            f"Your goal is to answer questions and capture new customer leads. "
            f"Use the following information to answer questions: {contractor_profile['knowledge_base']}"
        )
        super().__init__(instructions=instructions)

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
    llm = google.LLM(model="gemini-1.5-flash-latest")

    vad = silero.VAD.load()
    session = agents.AgentSession(stt=stt, llm=llm, tts=tts, vad=vad)
    agent = ContractorAgent(profile)
    
    # This is the NEW, correct code
    await session.start(room=ctx.room, agent=agent)
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