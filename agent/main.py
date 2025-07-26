
import aiohttp
from livekit.agents import Agent, AgentSession
from dotenv import load_dotenv

import asyncio
import logging
import os
from livekit import agents, rtc
from livekit.agents import JobRequest

# Configure logging
logging.basicConfig(level=logging.INFO, format='%Y-%m-%d %H:%M:%S - %(levelname)s - %(message)s')
load_dotenv()
INTERNAL_API_URL = os.getenv("INTERNAL_API_URL")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

class ContractorAgent(agents.Agent):
    def __init__(self, contractor_profile: dict):
        super().__init__()
        instructions = (
            f"You are a friendly and helpful digital receptionist for {contractor_profile['business_name']}. "
            f"Your goal is to answer questions and capture new customer leads. "
            f"Use the following information to answer questions: {contractor_profile['knowledge_base']}"
        )
        self.update_instructions(instructions)

async def fetch_contractor_profile(session: aiohttp.ClientSession, contractor_id: str) -> dict:
    url = f"{INTERNAL_API_URL}/api/internal/contractors/{contractor_id}"
    headers = {"Authorization": INTERNAL_API_KEY}
    async with session.get(url, headers=headers) as response:
        if response.status != 200:
            logging.error(f"Failed to fetch contractor profile: {response.status}")
            raise Exception(f"Contractor not found: {contractor_id}")
        return await response.json()

async def request_fnc(req: JobRequest):
    """
    This function is called when a new job is requested.
    We accept the job and set the agent's identity and kind.
    """
    logging.info(f"Accepting job {req.job.id}")
    await req.accept(
    identity="contractor-leads-bot-agent", # A consistent identity for our agent
)

async def entrypoint(ctx: agents.JobContext):
    logging.info(f"Agent received job: {ctx.job.id} for room {ctx.room.name}")
    
    contractor_id = ctx.room.name
    
    try:
        async with aiohttp.ClientSession() as http_session:
            profile = await fetch_contractor_profile(http_session, contractor_id)
    except Exception as e:
        logging.error(f"Could not start agent session, failed to get profile: {e}")
        return

    stt = google.STT()
    tts = google.TTS()
    llm = google.LLM()

    session = agents.AgentSession(stt=stt, llm=llm, tts=tts)
    agent = ContractorAgent(profile)
    
    await session.start(ctx.room, agent=agent)
    await session.say(f"Thank you for calling {profile['business_name']}. How can I help you today?", allow_interruptions=True)


if __name__ == "__main__":
    logging.info("Starting Contractor Leads Bot Agent Worker...")
    
    agents.cli.run_app(
        agents.WorkerOptions(
            request_fnc=request_fnc,
            entrypoint_fnc=entrypoint
        )
    )