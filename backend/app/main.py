from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from .api.endpoints import router as main_router
from .api.auth import router as auth_router
from .core.config import get_settings
from .utils.json_encoder import CustomJSONEncoder
import json
import os

settings = get_settings()

class CustomJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            cls=CustomJSONEncoder,
            ensure_ascii=False
        ).encode("utf-8")

app = FastAPI(title="Chatbot Builder API", default_response_class=CustomJSONResponse)

# Configure CORS — allow all origins so widgets work on any website
# The public /api/chat endpoint doesn't use cookies, just Auth headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve widget.js from /static — avoids Vercel SPA rewrite intercepting it
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(main_router, prefix="/api", tags=["API"])
