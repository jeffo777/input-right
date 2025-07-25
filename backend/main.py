from fastapi import FastAPI
from app import api

app = FastAPI(title="Contractor Leads Bot API")

# Include the router from our api module
app.include_router(api.router)

@app.get("/")
async def read_root():
    """A simple root endpoint to confirm the API is running."""
    return {"message": "Contractor Leads Bot Backend is running"}