from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import api

app = FastAPI(title="Contractor Leads Bot API")

# Define the origins that are allowed to make requests to this server.
# For development, we'll allow our local React server.
# For production, we would add our actual domain names.
origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router from our api module
app.include_router(api.router)

@app.get("/")
async def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Contractor Leads Bot Backend is running"}