import asyncio
from ..core.config import get_settings

settings = get_settings()

from threading import Lock

class AIService:
    _instance = None
    _client = None
    _lock = Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AIService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if not self._initialized:
                self._client = None
                self._initialized = True

    @property
    def client(self):
        if self._client is None:
            try:
                from google import genai
                # google-genai (new SDK) — 1,500 req/day free on gemini-1.5-flash
                self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            except ImportError:
                raise RuntimeError("Failed to initialize Google AI client. Please check your installation.")
        return self._client

    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate a response using the AI model (non-blocking via asyncio.to_thread)"""
        try:
            from google.genai import types
            client = self.client
            full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}" if context else prompt
            config = types.GenerateContentConfig(
                max_output_tokens=400,
                temperature=0.4,
            )
            # generate_content is synchronous — run in thread pool to avoid blocking event loop
            response = await asyncio.to_thread(
                client.models.generate_content,
                model='gemini-1.5-flash',
                contents=full_prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Error generating AI response: {str(e)}")