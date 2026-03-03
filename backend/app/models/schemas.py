from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    bot_id: str
    query: str # Frontend sends 'message', but we use 'query' internally

class ChatResponse(BaseModel):
    response: str

class DocumentUploadResponse(BaseModel):
    bot_id: str
    message: str
    widget_code: str

class WebScrapeRequest(BaseModel):
    company_name: str
    website_url: str
    login_url: Optional[str] = None
    login_username: Optional[str] = None
    login_password: Optional[str] = None
    login_role: Optional[str] = None  # e.g. "Student", "Employee", "Admin"

class WebScrapeBotResponse(BaseModel):
    bot_id: str
    message: str
    widget_code: str
    pages_scraped: int
    total_chunks: int

class Bot(BaseModel):
    id: str
    name: str
    company_name: str
    collection_name: str
