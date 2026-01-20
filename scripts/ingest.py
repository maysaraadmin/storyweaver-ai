import json
import os
import logging
from pathlib import Path
from backend.vector_store import VectorStoreManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ingest_sample_book():
    """Ingest a sample children's book"""
    try:
        vector_store = VectorStoreManager()
        
        # Sample book data
        sample_book = {
            "story_id": "the_little_seed",
            "title": "The Little Seed",
            "pages": [
                {
                    "page_number": 1,
                    "text": "Once upon a time, there was a little seed sleeping in the soil."
                },
                {
                    "page_number": 2,
                    "text": "The sun smiled warmly, and the rain gave gentle kisses."
                },
                {
                    "page_number": 3,
                    "text": "The little seed woke up and stretched its tiny roots."
                },
                # ... more pages
            ]
        }
        
        # Prepare documents for vector store
        documents = []
        for page in sample_book["pages"]:
            documents.append({
                "text": page["text"],
                "metadata": {
                    "page_number": page["page_number"],
                    "title": sample_book["title"],
                    "story_id": sample_book["story_id"]
                }
            })
        
        # Add to vector store
        vector_store.add_documents(sample_book["story_id"], documents)
        
        logger.info(f"Ingested {len(documents)} pages from '{sample_book['title']}'")
        print(f"Ingested {len(documents)} pages from '{sample_book['title']}'")
        
    except Exception as e:
        logger.error(f"Error ingesting sample book: {e}")
        raise

def ingest_from_json(file_path):
    """Ingest book from JSON file"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if not file_path.lower().endswith('.json'):
        raise ValueError(f"File must be a JSON file: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {e}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Encoding error in file {file_path}: {e}")
    
    # Validate book data structure
    if not isinstance(book_data, dict):
        raise ValueError("Book data must be a dictionary")
    
    if "title" not in book_data:
        raise ValueError("Book data must contain a 'title' field")
    
    if "pages" not in book_data or not isinstance(book_data["pages"], list):
        raise ValueError("Book data must contain a 'pages' list")
    
    if len(book_data["pages"]) == 0:
        raise ValueError("Book must have at least one page")
    
    try:
        vector_store = VectorStoreManager()
        
        documents = []
        for i, page in enumerate(book_data["pages"]):
            if not isinstance(page, dict):
                logger.warning(f"Skipping invalid page {i}: not a dictionary")
                continue
            
            if "text" not in page:
                logger.warning(f"Skipping page {i}: missing 'text' field")
                continue
            
            documents.append({
                "text": page["text"],
                "metadata": {
                    "page_number": page.get("page_number", i + 1),
                    "title": book_data["title"],
                    "story_id": book_data.get("story_id", book_data["title"].lower().replace(" ", "_"))
                }
            })
        
        if not documents:
            raise ValueError("No valid pages found in the book data")
        
        story_id = book_data.get("story_id", book_data["title"].lower().replace(" ", "_"))
        vector_store.add_documents(story_id, documents)
        
        logger.info(f"Ingested {len(documents)} pages from '{book_data['title']}'")
        print(f"Ingested {len(documents)} pages from '{book_data['title']}'")
        
    except Exception as e:
        logger.error(f"Error processing book data: {e}")
        raise

if __name__ == "__main__":
    # Create sample book directory if it doesn't exist
    os.makedirs("data/books", exist_ok=True)
    
    # Create a sample book
    sample_book = {
        "title": "The Little Seed",
        "story_id": "the_little_seed",
        "author": "StoryBot AI",
        "pages": [
            {"page_number": 1, "text": "In a cozy garden, a tiny seed slept in the dark soil."},
            {"page_number": 2, "text": "Sunny the sun smiled down, sending warm rays of light."},
            {"page_number": 3, "text": "Raindrop visited with a gentle sprinkle of water."},
            {"page_number": 4, "text": "The seed felt the warmth and moisture, and began to wake."},
            {"page_number": 5, "text": "A small green shoot pushed up through the soil."},
            {"page_number": 6, "text": "The shoot grew taller each day, reaching for the sun."},
            {"page_number": 7, "text": "Leaves unfolded, spreading wide to catch sunlight."},
            {"page_number": 8, "text": "A bud formed at the top of the stem."},
            {"page_number": 9, "text": "One morning, the bud opened into a beautiful yellow flower."},
            {"page_number": 10, "text": "Bees buzzed happily around the new flower."},
            {"page_number": 11, "text": "The flower made new seeds for the next season."},
            {"page_number": 12, "text": "The little seed had become a beautiful plant, completing its journey."}
        ]
    }
    
    # Save sample book
    with open("data/books/sample_book.json", "w") as f:
        json.dump(sample_book, f, indent=2)
    
    # Ingest the sample book
    ingest_from_json("data/books/sample_book.json")