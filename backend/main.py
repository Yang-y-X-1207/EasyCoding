"""
Coding-CLI Backend - FastAPI Entry Point
Phase 1: Minimal Viable System
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import chat, health

app = FastAPI(
    title="Coding-CLI Backend",
    description="AI Coding Assistant CLI Backend",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(session.router, prefix="/api/v1", tags=["session"])
app.include_router(task.router, prefix="/api/v1", tags=["task"])
app.include_router(health.router, tags=["health"])


@app.get("/")
async def root():
    return {"message": "Coding-CLI Backend", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
