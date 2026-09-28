import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router

app = FastAPI(
    title="Meeting Organizer Agent API",
    description=(
        "Agentic AI Meeting Organizer implementing Lab 1 (Goal-Plan-Act-Observe-Revise Loop), "
        "Lab 2 (Tool-Using Agent: Centralized Execution & Verification), "
        "Lab 3 (Skill Creation: Reusable PlanSkill & FormatSkill), and "
        "Lab 4 (Memory & Retrieval: Session State, Knowledge Store & Similarity History)."
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

# Mount Static Directory for Web Frontend Dashboard
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", summary="Web Dashboard or Root Status")
def root(request: Request):
    accept = request.headers.get("accept", "")
    index_path = os.path.join(static_dir, "index.html")
    if "text/html" in accept and os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "service": "Meeting Organizer Agent",
        "status": "online",
        "labs_implemented": [
            "Lab 1: Agent vs Chatbot Loop",
            "Lab 2: Tool-Using Agent with Centralized Execution",
            "Lab 3: Skill Creation (Reusable Plan & Format Skills)",
            "Lab 4: Memory & Retrieval (Session State vs Stored Archives)",
        ],
        "docs_url": "/docs",
    }


@app.get("/health", summary="Health check")
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

