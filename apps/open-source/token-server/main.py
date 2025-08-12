import os
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api
from dotenv import load_dotenv

# Load environment variables from the .env file in the parent directory
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

app = FastAPI()

# Configure CORS to allow requests from our frontend (running on localhost:3000 or 3001)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TokenRequest(BaseModel):
    business_id: str
    room_name: str

@app.post("/api/token")
async def get_token(request: TokenRequest):
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(status_code=500, detail="LiveKit server credentials not configured in .env file.")
    
    room_name = request.room_name
    # For the open-source version, the participant identity is simple
    participant_identity = f"visitor-{uuid.uuid4()}"

    token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET) \
        .with_identity(participant_identity) \
        .with_name("Website Visitor") \
        .with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            can_publish_data=True,
        )).to_jwt()

    return {"token": token}

@app.get("/")
async def root():
    return {"message": "Chat To Form (Open Source) Token Server is running."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
