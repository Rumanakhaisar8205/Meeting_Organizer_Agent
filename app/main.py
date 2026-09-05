"""
Main FastAPI Application Entry Point for Meeting Organizer Agent
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="Meeting Organizer Agent API",
    description=(
        "Agentic AI Meeting Organizer implementing Lab 1 (Agent vs Chatbot: Goal-Plan-Act-Observe-Revise Loop) "
        "and Lab 2 (Tool-Using Agent: Centralized Execution, Structured Contracts, and Graceful Error Handling)."
    ),
    version="1.0.0",
)

# CORS middleware for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/", summary="Root status")
def root():
    return {
        "service": "Meeting Organizer Agent",
        "status": "online",
        "labs_implemented": ["Lab 1: Agent vs Chatbot Loop", "Lab 2: Tool-Using Agent with Centralized Execution"],
        "docs_url": "/docs",
    }


@app.get("/health", summary="Health check")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
