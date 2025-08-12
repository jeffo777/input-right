import logging
import json
from livekit import agents, rtc
from livekit.agents import function_tool, get_job_context

class BusinessAgent(agents.Agent):
    def __init__(self, instructions: str):
        """
        Initializes the BusinessAgent.
        This agent is now generic and receives its full instructions upon creation.
        It does not know how the instructions were created, only that it must follow them.
        """
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