
import asyncio
import logging
from livekit import agents, rtc
from livekit.agents import JobRequest

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    """
    This is the entrypoint for our agent job.
    It's called when a new visitor joins a room.
    """
    logging.info(f"Agent received job: {ctx.job.id} for room {ctx.room.name}")
    
    await ctx.connect()
    logging.info(f"Agent connected to room: {ctx.room.name}")

 # --- START OF NEW LOGGING ---
    def on_participant_connected(participant: rtc.RemoteParticipant):
        logging.info(f"Agent saw a participant connect: "
                     f"identity={participant.identity}, "
                     f"sid={participant.sid}, "
                     f"kind={participant.kind}")

    ctx.room.on("participant_connected", on_participant_connected)

    # Also log any participants already in the room
    for p in ctx.room.remote_participants.values():
        on_participant_connected(p)
    # --- END OF NEW LOGGING ---


    # Keep the agent alive until the job is done
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    logging.info("Starting Contractor Leads Bot Agent Worker...")
    
    agents.cli.run_app(
        agents.WorkerOptions(
            request_fnc=request_fnc,
            entrypoint_fnc=entrypoint
        )
    )