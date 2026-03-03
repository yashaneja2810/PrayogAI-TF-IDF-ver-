from ..core.config import get_settings

settings = get_settings()

from threading import Lock

class AIService:
    _instance = None
    _model = None
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
                self._model = None
                self._initialized = True

    @property
    def model(self):
        if self._model is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                self._model = genai.GenerativeModel('gemini-2.5-pro')
            except ImportError:
                raise RuntimeError("Failed to initialize Google AI model. Please check your installation.")
        return self._model

    async def generate_response(self, prompt: str, context: str = "") -> str:
        """Generate a response using the AI model"""
        try:
            model = self.model  # This will lazily initialize the model
            full_prompt = f"Context:\n{context}\n\nQuestion: {prompt}" if context else prompt
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            raise RuntimeError(f"Error generating AI response: {str(e)}")