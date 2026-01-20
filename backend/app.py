from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import logging
import uuid
from typing import List, Optional, Dict, Any
import os
import uvicorn

from models import (
    UserQuery, ChatResponse, ExpansionProposal, APIResponse,
    SearchQuery, BookData, StoryLogicDataset
)
from story_logic import StoryLogicExtractor
from vector_store import VectorStoreManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="StoryWeaver AI API",
    description="API for collaborative children's storytelling with semantic governance",
    version="1.0.0"
)

# Security middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Serve static files
if os.path.exists("../frontend"):
    app.mount("/static", StaticFiles(directory="../frontend"), name="static")

# Global instances
story_extractor = StoryLogicExtractor()
vector_store = VectorStoreManager()

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error", "errors": [str(exc)]}
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "StoryWeaver AI API", "version": "1.0.0"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

@app.post("/api/chat", response_model=APIResponse)
async def chat(query: UserQuery):
    """Chat with the story assistant"""
    try:
        # Simulate chat response (replace with actual RAG implementation)
        response_text = f"I understand you're asking about: {query.message}"
        
        # Extract story elements if story_id is provided
        elements = []
        if query.story_id:
            # This would integrate with vector store and story logic
            pass
        
        chat_response = ChatResponse(
            response=response_text,
            is_permissible=True,
            reasoning="Query is within story context",
            suggestions=["Consider adding more details", "Explore character motivations"]
        )
        
        return APIResponse(
            success=True,
            message="Chat response generated successfully",
            data=chat_response.dict()
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search", response_model=APIResponse)
async def search_stories(query: SearchQuery):
    """Search through stories and content"""
    try:
        # Simulate search (replace with actual vector search)
        results = [
            {
                "story_id": "the_little_seed",
                "title": "The Little Seed",
                "page_number": 1,
                "text": "Once upon a time, there was a little seed...",
                "score": 0.95
            }
        ]
        
        return APIResponse(
            success=True,
            message=f"Found {len(results)} results",
            data={"results": results, "query": query.query}
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/propose-expansion", response_model=APIResponse)
async def propose_expansion(proposal: ExpansionProposal):
    """Submit a story expansion proposal"""
    try:
        # Validate proposal consistency
        dataset = StoryLogicDataset(
            story_id=proposal.story_id,
            title="Sample Story",
            elements=[],
            rules=[],
            contradictions=[]
        )
        
        # This would integrate with story logic validation
        consistency_check = {
            "is_consistent": True,
            "contradictions": [],
            "suggestions": ["Consider character development"]
        }
        
        return APIResponse(
            success=True,
            message="Expansion proposal submitted successfully",
            data={
                "proposal_id": str(uuid.uuid4()),
                "consistency_check": consistency_check
            }
        )
        
    except Exception as e:
        logger.error(f"Proposal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingest", response_model=APIResponse)
async def ingest_book(book_data: BookData, background_tasks: BackgroundTasks):
    """Ingest a book into the system"""
    try:
        # Add background task for processing
        background_tasks.add_task(process_book_ingestion, book_data)
        
        return APIResponse(
            success=True,
            message="Book ingestion started",
            data={"story_id": book_data.story_id, "pages_count": len(book_data.pages)}
        )
        
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stories/{story_id}", response_model=APIResponse)
async def get_story(story_id: str):
    """Get story details"""
    try:
        # Simulate story retrieval
        story_data = {
            "story_id": story_id,
            "title": "The Little Seed",
            "pages": [
                {"page_number": 1, "text": "Once upon a time..."},
                {"page_number": 2, "text": "The sun smiled..."}
            ],
            "elements": [
                {"element_id": "char_seed", "name": "Little Seed", "type": "character"}
            ]
        }
        
        return APIResponse(
            success=True,
            message="Story retrieved successfully",
            data=story_data
        )
        
    except Exception as e:
        logger.error(f"Story retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stories", response_model=APIResponse)
async def list_stories():
    """List all available stories"""
    try:
        stories = [
            {"story_id": "the_little_seed", "title": "The Little Seed", "pages": 12},
            {"story_id": "dragon_adventure", "title": "Dragon's Adventure", "pages": 15}
        ]
        
        return APIResponse(
            success=True,
            message="Stories retrieved successfully",
            data={"stories": stories}
        )
        
    except Exception as e:
        logger.error(f"Stories list error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_book_ingestion(book_data: BookData):
    """Background task for book ingestion"""
    try:
        logger.info(f"Processing ingestion for story: {book_data.story_id}")
        
        # Extract story elements
        pages = [{"page_number": p.page_number, "text": p.text} for p in book_data.pages]
        elements = story_extractor.extract_story_elements(pages)
        
        # Add to vector store
        documents = []
        for page in book_data.pages:
            documents.append({
                "text": page.text,
                "metadata": {
                    "page_number": page.page_number,
                    "title": book_data.title,
                    "story_id": book_data.story_id
                }
            })
        
        vector_store.add_documents(book_data.story_id, documents)
        
        logger.info(f"Successfully ingested {len(documents)} pages and {len(elements)} elements")
        
    except Exception as e:
        logger.error(f"Background ingestion error: {e}")
        raise

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)