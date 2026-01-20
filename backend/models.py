from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

class StoryElementType(str, Enum):
    CHARACTER = "character"
    LOCATION = "location"
    RULE = "rule"
    EVENT = "event"
    THEME = "theme"
    RELATIONSHIP = "relationship"
    OBJECT = "object"

class StoryElement(BaseModel):
    element_id: str
    element_type: StoryElementType
    name: str
    description: str
    attributes: Dict[str, Any] = {}
    relationships: List[str] = []
    source_page: int
    confidence: float = 1.0
    created_at: datetime = datetime.now()
    
    @validator('element_id')
    def validate_element_id(cls, v):
        if not v or not v.strip():
            raise ValueError('element_id cannot be empty')
        return v.strip()
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('name cannot be empty')
        return v.strip()
    
    @validator('source_page')
    def validate_source_page(cls, v):
        if v < 1:
            raise ValueError('source_page must be >= 1')
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('confidence must be between 0 and 1')
        return v

class StoryLogicDataset(BaseModel):
    story_id: str
    title: str
    elements: List[StoryElement] = []
    rules: List[Dict[str, Any]] = []
    contradictions: List[Dict[str, str]] = []
    last_updated: datetime = datetime.now()
    version: int = 1
    
    @validator('story_id')
    def validate_story_id(cls, v):
        if not v or not v.strip():
            raise ValueError('story_id cannot be empty')
        return v.strip()
    
    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('title cannot be empty')
        return v.strip()
    
    @validator('version')
    def validate_version(cls, v):
        if v < 1:
            raise ValueError('version must be >= 1')
        return v

class UserQuery(BaseModel):
    message: str
    story_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('message cannot be empty')
        return v.strip()

class ChatResponse(BaseModel):
    response: str
    is_permissible: bool
    reasoning: Optional[str] = None
    suggestions: Optional[List[str]] = None
    updated_dataset: Optional[bool] = False
    
    @validator('response')
    def validate_response(cls, v):
        if not v or not v.strip():
            raise ValueError('response cannot be empty')
        return v.strip()

class ExpansionProposal(BaseModel):
    story_id: str
    new_content: str
    page_number: int
    element_references: List[str] = []
    user_context: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = datetime.now()
    
    @validator('story_id')
    def validate_story_id(cls, v):
        if not v or not v.strip():
            raise ValueError('story_id cannot be empty')
        return v.strip()
    
    @validator('new_content')
    def validate_new_content(cls, v):
        if not v or not v.strip():
            raise ValueError('new_content cannot be empty')
        return v.strip()
    
    @validator('page_number')
    def validate_page_number(cls, v):
        if v < 1:
            raise ValueError('page_number must be >= 1')
        return v
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ["pending", "approved", "rejected"]
        if v not in allowed_statuses:
            raise ValueError(f'status must be one of {allowed_statuses}')
        return v

class PageData(BaseModel):
    page_number: int
    text: str
    elements: List[str] = []
    
    @validator('page_number')
    def validate_page_number(cls, v):
        if v < 1:
            raise ValueError('page_number must be >= 1')
        return v
    
    @validator('text')
    def validate_text(cls, v):
        if not v or not v.strip():
            raise ValueError('text cannot be empty')
        return v.strip()

class BookData(BaseModel):
    title: str
    story_id: Optional[str] = None
    author: Optional[str] = None
    pages: List[PageData]
    elements: List[StoryElement] = []
    created_at: datetime = datetime.now()
    
    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('title cannot be empty')
        return v.strip()
    
    @validator('pages')
    def validate_pages(cls, v):
        if not v:
            raise ValueError('Book must have at least one page')
        return v
    
    @validator('story_id', always=True)
    def generate_story_id(cls, v, values):
        if v is None and 'title' in values:
            return values['title'].lower().replace(' ', '_').replace('-', '_')
        return v

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    errors: List[str] = []
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('message cannot be empty')
        return v.strip()

class SearchQuery(BaseModel):
    query: str
    story_id: Optional[str] = None
    max_results: int = 10
    filters: Dict[str, Any] = {}
    
    @validator('query')
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError('query cannot be empty')
        return v.strip()
    
    @validator('max_results')
    def validate_max_results(cls, v):
        if v < 1:
            raise ValueError('max_results must be >= 1')
        if v > 100:
            raise ValueError('max_results must be <= 100')
        return v