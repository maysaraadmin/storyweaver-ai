import logging
import subprocess
import sys
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException, status, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PyPDF2 import PdfReader
import io
import uvicorn
from pathlib import Path
import threading
import time
import webbrowser
import os
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log', mode='w', encoding='utf-8')  # Use 'w' mode to overwrite the file each run
    ],
    force=True  # Force reconfiguration
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with CORS
app = FastAPI(
    title="Storybook Adventure Chat API",
    description="Backend API for the Storybook Adventure Chat application",
    version="1.0.0"
)

# Serve static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# Add middleware to disable caching for static files
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage (replace with a database in production)
stories_db = {}
chats_db = {}
story_elements_db = {}

# Data Models
class StoryElement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # 'character', 'location', 'item', etc.
    description: str
    story_id: str

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    sender: str  # 'user' or 'bot'
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    story_id: str

class Story(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    elements: List[StoryElement] = []
    messages: List[Message] = []

class StoryCreate(BaseModel):
    title: str
    content: str

class MessageCreate(BaseModel):
    content: str
    sender: str = "user"

class StoryElementCreate(BaseModel):
    name: str
    type: str
    description: str

class StoriesResponse(BaseModel):
    stories: List[Story]

class PDFUploadResponse(BaseModel):
    status: str
    story_id: str
    title: str

# Initialize with some sample data
sample_story = Story(
    id="1",
    title="The Little Seed",
    content="Once upon a time, there was a little seed...",
    elements=[
        StoryElement(
            id="1-1",
            name="The Little Seed",
            type="character",
            description="The main character of the story, a small seed with big dreams.",
            story_id="1"
        ),
        StoryElement(
            id="1-2",
            name="Garden",
            type="location",
            description="A beautiful garden where the story takes place.",
            story_id="1"
        )
    ],
    messages=[
        Message(
            id="m1",
            content="Hello! I'm here to help you explore and expand this story.",
            sender="bot",
            story_id="1"
        )
    ]
)

stories_db[sample_story.id] = sample_story

frontend_process = None

# Serve static files from frontend directory
static_dir = Path("frontend")
if not static_dir.exists():
    static_dir.mkdir()
    (static_dir / "index.html").write_text("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Full Stack App</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            .status { margin: 20px 0; padding: 10px; background: #f0f0f0; }
        </style>
    </head>
    <body>
        <h1>Welcome to Full Stack App</h1>
        <div class="status" id="status">Backend is running!</div>
        <p>Check the console for detailed logs.</p>
        <script>
            // Simple frontend JavaScript
            document.addEventListener('DOMContentLoaded', () => {
                console.log('Frontend loaded');
                fetch('/api/health')
                    .then(response => response.json())
                    .then(data => {
                        console.log('Health check:', data);
                        document.getElementById('status').textContent = 
                            `Backend status: ${data.status}`;
                    });
            });
        </script>
    </body>
    </html>
    """)

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return FileResponse('frontend/index.html')

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint to verify the API is running."""
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

# Story endpoints
@app.get("/api/stories", response_model=StoriesResponse)
async def get_stories():
    """Get all stories."""
    return {"stories": list(stories_db.values())}

@app.post("/api/stories", response_model=Story, status_code=status.HTTP_201_CREATED)
async def create_story(story: StoryCreate):
    """Create a new story."""
    new_story = Story(
        title=story.title,
        content=story.content,
        elements=[],
        messages=[]
    )
    stories_db[new_story.id] = new_story
    return new_story

@app.get("/api/stories/{story_id}", response_model=Story)
async def get_story(story_id: str):
    """Get a specific story by ID."""
    if story_id not in stories_db:
        raise HTTPException(status_code=404, detail="Story not found")
    return stories_db[story_id]

# Message endpoints
@app.get("/api/stories/{story_id}/messages", response_model=List[Message])
async def get_messages(story_id: str):
    """Get all messages for a story."""
    if story_id not in stories_db:
        raise HTTPException(status_code=404, detail="Story not found")
    return stories_db[story_id].messages

@app.post("/api/stories/{story_id}/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
async def create_message(story_id: str, message: MessageCreate):
    """Add a new message to a story."""
    if story_id not in stories_db:
        raise HTTPException(status_code=404, detail="Story not found")
    
    new_message = Message(
        content=message.content,
        sender=message.sender,
        story_id=story_id
    )
    
    stories_db[story_id].messages.append(new_message)
    stories_db[story_id].updated_at = datetime.utcnow().isoformat()
    
    # Generate a more intelligent bot response
    if message.sender == "user":
        bot_response_content = generate_bot_response(message.content, stories_db[story_id])
        bot_response = Message(
            content=bot_response_content,
            sender="bot",
            story_id=story_id
        )
        stories_db[story_id].messages.append(bot_response)
    
    return new_message

def generate_bot_response(user_message: str, story: Story) -> str:
    """Generate an intelligent bot response based on the user message and story context."""
    user_message_lower = user_message.lower()
    
    # Greeting responses
    if any(greeting in user_message_lower for greeting in ["hi", "hello", "hey", "greetings"]):
        return f"Hello! I'm here to help you explore '{story.title}'. What would you like to know about this story?"
    
    # Story information requests
    if any(word in user_message_lower for word in ["what", "tell me", "about", "summary"]):
        return f"'{story.title}' is about: {story.content[:200]}... Would you like me to elaborate on any part of the story?"
    
    # Character questions
    if "character" in user_message_lower or "who" in user_message_lower:
        characters = [elem for elem in story.elements if elem.type == "character"]
        if characters:
            char_names = ", ".join([c.name for c in characters])
            return f"The main characters in this story are: {char_names}. Which character would you like to know more about?"
        else:
            return "This story doesn't have any defined characters yet. Would you like to add some?"
    
    # Location questions
    if "where" in user_message_lower or "location" in user_message_lower or "place" in user_message_lower:
        locations = [elem for elem in story.elements if elem.type == "location"]
        if locations:
            loc_names = ", ".join([l.name for l in locations])
            return f"The story takes place in: {loc_names}. Would you like to explore any of these locations?"
        else:
            return "The story's setting isn't fully described yet. Where would you like the story to take place?"
    
    # Expansion requests
    if any(word in user_message_lower for word in ["expand", "continue", "what happens next", "add"]):
        return f"That's a great idea! To expand '{story.title}', you could add new characters, events, or explore what happens next. What specific expansion would you like to propose?"
    
    # Help requests
    if any(word in user_message_lower for word in ["help", "how", "can I"]):
        return """I can help you with this story in several ways:
• Ask questions about the plot or characters
• Suggest story expansions or new elements
• Discuss story themes and ideas
• Help maintain story consistency

What would you like to do?"""
    
    # More specific contextual responses
    if "seed" in user_message_lower or "little seed" in user_message_lower:
        return "The Little Seed is the main character of our story! It's a small seed with big dreams, waiting to grow into something wonderful. What would you like to know about the seed's journey?"
    
    if "garden" in user_message_lower:
        return "The garden is where our story takes place! It's a beautiful setting full of life and possibilities. Would you like to explore what happens in the garden?"
    
    if "grow" in user_message_lower or "growth" in user_message_lower:
        return "Growth is a central theme in this story! The little seed's journey represents patience, hope, and transformation. What aspect of growth interests you most?"
    
    # Conversational responses
    if any(word in user_message_lower for word in ["interesting", "cool", "nice", "good"]):
        return "I'm glad you find it interesting! There's so much more to explore in this story. What would you like to discover next?"
    
    if any(word in user_message_lower for word in ["yes", "yeah", "sure", "ok"]):
        return "Great! Let's continue exploring. What aspect of the story would you like to focus on - the characters, the setting, or perhaps what happens next?"
    
    # Default intelligent response (more varied and contextual)
    import random
    contextual_responses = [
        f"Let's explore '{story.title}' together! We could look at the characters, the setting, or imagine what happens next. What interests you?",
        f"There's so much to discover in '{story.title}'. Would you like to discuss the themes, characters, or plot development?",
        f"I'd love to help you dive deeper into '{story.title}'. What part of the story captures your imagination the most?",
        f"Every story has many layers. In '{story.title}', we could explore character motivations, setting details, or future possibilities. What shall we focus on?",
        f"Stories are like journeys. In '{story.title}', where would you like our journey to take us next - character development, plot twists, or world-building?"
    ]
    
    return random.choice(contextual_responses)

@app.post("/api/stories/{story_id}/elements", response_model=StoryElement, status_code=status.HTTP_201_CREATED)
async def create_story_element(story_id: str, element: StoryElementCreate):
    """Add a new element to a story."""
    if story_id not in stories_db:
        raise HTTPException(status_code=404, detail="Story not found")
    
    new_element = StoryElement(
        name=element.name,
        type=element.type,
        description=element.description,
        story_id=story_id
    )
    
    stories_db[story_id].elements.append(new_element)
    stories_db[story_id].updated_at = datetime.utcnow().isoformat()
    
    return new_element

# PDF Upload endpoint
@app.post("/api/upload-pdf/", response_model=PDFUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file."""
    try:
        # Read the uploaded file
        contents = await file.read()
        
        # Create a PDF reader object
        pdf_reader = PdfReader(io.BytesIO(contents))
        
        # Extract text from all pages
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n\n"
        
        # Create a new story from the PDF content
        story_id = str(len(stories_db) + 1)
        new_story = Story(
            id=story_id,
            title=file.filename.replace('.pdf', ''),
            content=text[:500] + "..." if len(text) > 500 else text,  # First 500 chars as preview
            elements=[],
            messages=[]
        )
        
        # Add the full text as the first message
        new_story.messages.append(Message(
            content=f"PDF content:\n\n{text}",
            sender="system",
            story_id=story_id
        ))
        
        # Add to database
        stories_db[story_id] = new_story
        
        return {"status": "success", "story_id": story_id, "title": new_story.title}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def start_frontend():
    """Start the frontend development server"""
    try:
        logger.info("Starting frontend development server...")
        frontend = subprocess.Popen(
            [sys.executable, "-m", "http.server", "8001", "--directory", "frontend"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Log frontend server output
        def log_output(pipe, logger_func):
            for line in pipe:
                logger_func(line.strip())
        
        threading.Thread(
            target=log_output,
            args=(frontend.stdout, logger.info),
            daemon=True
        ).start()
        
        threading.Thread(
            target=log_output,
            args=(frontend.stderr, logger.error),
            daemon=True
        ).start()
        
        return frontend
    except Exception as e:
        logger.error(f"Error starting frontend server: {e}")
        return None

async def run():
    global frontend_process
    try:
        # Create frontend directory if it doesn't exist
        frontend_dir = Path("frontend")
        frontend_dir.mkdir(exist_ok=True)
        
        # Start frontend in a separate thread
        frontend_process = start_frontend()
        if not frontend_process:
            raise Exception("Failed to start frontend server")
        
        # Start backend in the main thread
        logger.info("Storybook Adventure Chat API starting...")
        logger.info(f"API Documentation: http://localhost:8000/docs")
        logger.info(f"Frontend: http://localhost:8000")
        
        # Open browser after a short delay to ensure server is ready
        async def open_browser():
            await asyncio.sleep(1)
            webbrowser.open("http://localhost:8000")
        
        asyncio.create_task(open_browser())
        
        # Start the FastAPI server
        config = uvicorn.Config(
            "run:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disable auto-reload in production
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        if frontend_process:
            frontend_process.terminate()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        if frontend_process:
            frontend_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run())