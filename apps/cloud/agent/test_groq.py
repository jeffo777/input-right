import asyncio
import os
from dotenv import load_dotenv
from livekit.plugins import groq
from livekit.agents.llm import ChatContext

# Load environment variables from our .env file
load_dotenv()

async def main():
    print("Attempting to connect to Groq...")

    # Check if the API key is loaded
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY is not set in the .env file.")
        return

    print("API Key found. Initializing Groq LLM...")

    try:
        # Create an instance of the Groq LLM, just like in our agent
        llm = groq.LLM(model="llama-3.3-70b-versatile")

        # Create a simple conversation context
        chat_context = ChatContext()
        chat_context.add_message(role="user", content="Hello, are you working?")

        print("Sending a test message to Groq...")
        
        # Try to get a response using the documented argument name
        response_stream = llm.chat(chat_ctx=chat_context)
        
        print("Groq is responding:")
        
        full_response = ""
        async for chunk in response_stream:
            if chunk.delta and chunk.delta.content:
                print(chunk.delta.content, end="", flush=True)
                full_response += chunk.delta.content
        
        print("\n\nTest successful! Received a full response.")

    except Exception as e:
        print(f"\n\n--- TEST FAILED ---")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())