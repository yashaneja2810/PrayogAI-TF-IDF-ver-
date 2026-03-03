from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status, Header
from ..services.chat import ChatService
from ..utils.document_processor import DocumentProcessor, generate_widget_code
from ..models.schemas import ChatRequest, ChatResponse, DocumentUploadResponse, WebScrapeRequest, WebScrapeBotResponse
from fastapi import Body
from ..services.bot import BotService
from ..services.web_scraper import WebScraperService
from .dependencies import get_current_active_user, auth_service
from typing import List
from datetime import datetime
import uuid
import os
import shutil
import asyncio

router = APIRouter()
chat_service = ChatService()
doc_processor = DocumentProcessor()
bot_service = BotService()
web_scraper = WebScraperService()

from ..log_config import logger

@router.get("/bots")
async def get_user_bots(
    current_user: dict = Depends(get_current_active_user),
    authorization: str = Header(None)
):
    try:
        user_id = current_user["id"]
        # Extract token from Authorization header
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        bots = await auth_service.get_user_bots(user_id, token)
        return bots
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/stats")
async def get_bots_stats(current_user: dict = Depends(get_current_active_user)):
    """Get aggregated statistics for user's bots"""
    try:
        user_id = current_user["id"]
        # For now, return default stats since we don't have actual stats tracking yet
        return {
            "totalMessages": 0,
            "responseRate": 100,
            "avgResponseTime": 0.5,
            "errorRate": 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/bots/{bot_id}")
async def delete_bot(
    bot_id: str,
    current_user: dict = Depends(get_current_active_user),
    authorization: str = Header(None)
):
    """Delete a bot and all its associated data"""
    try:
        user_id = current_user["id"]
        # Extract token from Authorization header
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        await bot_service.delete_bot(bot_id, user_id, token)
        return {"message": "Bot deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/bots/{bot_id}/documents")
async def get_bot_documents(
    bot_id: str,
    current_user: dict = Depends(get_current_active_user),
    authorization: str = Header(None)
):
    try:
        from ..log_config import logger
        user_id = current_user["id"]
        logger.info(f"Fetching documents for bot {bot_id} requested by user {user_id}")
        
        # Extract token from Authorization header
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        
        # Verify bot ownership (check bot_id field, not id)
        bots = await auth_service.get_user_bots(user_id, token)
        if not any(bot["bot_id"] == bot_id for bot in bots):
            logger.error(f"Access denied: User {user_id} attempted to access bot {bot_id}")
            raise HTTPException(status_code=403, detail="Access denied to this bot")
            
        # Get documents from chat service
        try:
            documents = await chat_service.get_bot_documents(bot_id, user_id, token)
            logger.info(f"Successfully retrieved documents for bot {bot_id}")
            return documents  # Note: get_bot_documents already returns {"documents": [...]}
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}", exc_info=True)
            raise
    except Exception as e:
        logger.error(f"Error in get_bot_documents endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

from fastapi import Form

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    company_name: str = Form(...),
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_active_user)
):
    from ..log_config import logger
    temp_files = []  # Track temporary files for cleanup
    
    try:
        if not company_name:
            raise HTTPException(
                status_code=422,
                detail="Company name is required"
            )

        if not files:
            raise HTTPException(
                status_code=422,
                detail="At least one file is required"
            )

        # Validate file types
        for file in files:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext not in ['.pdf', '.txt', '.docx']:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unsupported file type: {ext}. Only .pdf, .txt, and .docx files are supported."
                )

        user_id = current_user["id"]
        logger.info(f"Processing upload request for user {user_id}")
        
        # Create a unique temporary directory for this upload
        temp_dir = f"temp_upload_{uuid.uuid4()}"
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Created temporary directory: {temp_dir}")
        
        try:
            # Create a bot for this document set
            bot_id = await auth_service.create_bot(user_id, name=company_name)
            logger.info(f"Created new bot {bot_id} for user {user_id}")
            
            # Process each file with retry mechanism
            all_chunks = []
            all_filenames = []
            all_file_sizes = []
            
            for file in files:
                file_ext = os.path.splitext(file.filename)[1].lower()
                temp_path = os.path.join(temp_dir, f"temp_{uuid.uuid4()}{file_ext}")
                temp_files.append(temp_path)
                
                max_retries = 3
                retry_delay = 1
                last_error = None
                
                for attempt in range(max_retries):
                    try:
                        content = await file.read()
                        file_size = len(content)  # Get actual file size in bytes
                        
                        with open(temp_path, "wb") as temp_file:
                            temp_file.write(content)
                            
                        chunks = doc_processor.process_file(temp_path, file.filename)
                        logger.info(f"Processed file {file.filename} ({file_size} bytes), got {len(chunks)} chunks")
                        
                        # Add chunks, filenames, and file sizes
                        all_chunks.extend(chunks)
                        all_filenames.extend([file.filename] * len(chunks))
                        all_file_sizes.extend([file_size] * len(chunks))
                        break
                        
                    except Exception as e:
                        last_error = e
                        if attempt < max_retries - 1:
                            logger.warning(f"Attempt {attempt + 1} failed for file {file.filename}, retrying in {retry_delay} seconds: {str(e)}")
                            await file.seek(0)  # Reset file pointer for next attempt
                            await asyncio.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            logger.error(f"Failed to process file {file.filename} after {max_retries} attempts: {str(e)}")
                            raise
            
            # Store in vector database with filenames and file sizes
            await chat_service.process_documents(bot_id, user_id, all_chunks, all_filenames, all_file_sizes)
            logger.info(f"Successfully stored {len(all_chunks)} chunks in vector database for bot {bot_id}")
            
            # Generate widget code
            widget_code = generate_widget_code(bot_id, company_name)
            logger.info(f"Generated widget code for bot {bot_id}")
            
            return DocumentUploadResponse(
                bot_id=bot_id,
                message="Documents processed successfully",
                widget_code=widget_code
            )
                
        finally:
            # Clean up all temporary files
            for temp_path in temp_files:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as e:
                    logger.error(f"Error cleaning up temporary file {temp_path}: {str(e)}")
            
            # Clean up temporary directory
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.error(f"Error cleaning up temporary directory {temp_dir}: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while processing the documents: {str(e)}"
        )

@router.post("/scrape", response_model=WebScrapeBotResponse)
async def scrape_website(
    request: WebScrapeRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """Create a dynamic bot by scraping a website."""
    from ..log_config import logger
    
    try:
        if not request.company_name:
            raise HTTPException(status_code=422, detail="Bot name is required")
        if not request.website_url:
            raise HTTPException(status_code=422, detail="Website URL is required")
        
        user_id = current_user["id"]
        logger.info(f"Scrape request from user {user_id}: {request.website_url}")
        
        # Step 1: Scrape the website
        try:
            scrape_result = await web_scraper.scrape_website(
                request.website_url,
                login_url=request.login_url,
                login_username=request.login_username,
                login_password=request.login_password,
                login_role=request.login_role,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        chunks = scrape_result["chunks"]
        metadata_list = scrape_result["metadata"]
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="No content could be extracted from the website."
            )
        
        logger.info(f"Scraped {scrape_result['pages_scraped']} pages, {len(chunks)} chunks")
        
        # Step 2: Create bot in Supabase
        bot_id = await auth_service.create_bot(user_id, name=request.company_name)
        logger.info(f"Created bot {bot_id} for scraped website")
        
        # Step 3: Build filenames + file_sizes arrays (for metadata compatibility)
        filenames = [f"web:{m.get('source_url', request.website_url)}" for m in metadata_list]
        file_sizes = [len(c.encode('utf-8')) for c in chunks]
        
        # Step 4: Store embeddings via existing pipeline
        await chat_service.process_documents(bot_id, user_id, chunks, filenames, file_sizes)
        logger.info(f"Stored {len(chunks)} chunks in Qdrant for bot {bot_id}")
        
        # Step 5: Generate widget code
        widget_code = generate_widget_code(bot_id, request.company_name)
        
        return WebScrapeBotResponse(
            bot_id=bot_id,
            message=f"Successfully scraped {scrape_result['pages_scraped']} pages and created bot",
            widget_code=widget_code,
            pages_scraped=scrape_result["pages_scraped"],
            total_chunks=scrape_result["total_chunks"],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in scrape endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error scraping website: {str(e)}"
        )

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest
):
    """
    Public chat endpoint for widgets and frontend. No authentication required.
    Allows chatting with any bot by bot_id.
    """
    try:
        from ..log_config import logger
        # user_id is None for anonymous/public users
        user_id = None
        logger.info(f"[Public] Chat request received for bot {request.bot_id}")
        # Skip user ownership check, allow any bot_id
        response = await chat_service.get_response(
            bot_id=request.bot_id,
            user_id=user_id,
            query=request.query
        )
        if not response:
            logger.error(f"[Public] Empty response received for bot {request.bot_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate response"
            )
        logger.info(f"[Public] Successfully generated response for bot {request.bot_id}")
        return ChatResponse(response=response)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Public] Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error processing chat request: {str(e)}"
        )

# New endpoint for widget compatibility: /api/bots/{bot_id}/chat
@router.post("/bots/{bot_id}/chat", response_model=ChatResponse)
async def chat_with_bot_id(
    bot_id: str,
    body: dict = Body(...),
    current_user: dict = Depends(get_current_active_user),
    authorization: str = Header(None)
):
    """
    Proxy endpoint for widget: expects { query: str } in body, bot_id in path.
    """
    try:
        from ..log_config import logger
        user_id = current_user["id"]
        query = body.get("query")
        if not query:
            raise HTTPException(status_code=400, detail="Missing 'query' in request body")
        
        # Extract token from Authorization header
        token = None
        if authorization and authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        
        logger.info(f"[Widget] Chat request for bot {bot_id} from user {user_id}")
        response = await chat_service.get_response(
            bot_id=bot_id,
            user_id=user_id,
            query=query,
            token=token
        )
        if not response:
            logger.error(f"[Widget] Empty response for bot {bot_id}")
            raise HTTPException(status_code=500, detail="Could not generate response")
        logger.info(f"[Widget] Successfully generated response for bot {bot_id}")
        return ChatResponse(response=response)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Widget] Error in chat_with_bot_id: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check endpoint that includes Qdrant status"""
    try:
        from ..services.vector_store import VectorStoreService
        vector_store = VectorStoreService()
        qdrant_health = vector_store.health_check()
        
        return {
            "status": "healthy" if qdrant_health["status"] == "healthy" else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "api": "healthy",
                "qdrant": qdrant_health
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "api": "healthy",
                "qdrant": {
                    "status": "unhealthy",
                    "message": str(e)
                }
            }
        }
