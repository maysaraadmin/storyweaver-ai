import chromadb
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import uuid
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Manages vector storage using ChromaDB and sentence transformers"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.embedding_model = None
        self.client = None
        self.collections = {}
        self._initialize()
    
    def _initialize(self):
        """Initialize the vector store"""
        try:
            # Initialize embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded successfully")
            
            # Initialize ChromaDB client
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            logger.info("ChromaDB client initialized")
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {e}")
            raise
    
    def _get_or_create_collection(self, story_id: str):
        """Get or create a collection for a specific story"""
        if story_id not in self.collections:
            try:
                collection = self.client.get_or_create_collection(
                    name=story_id,
                    metadata={"hnsw:space": "cosine", "story_id": story_id, "created_at": datetime.now().isoformat()}
                )
                self.collections[story_id] = collection
                logger.info(f"Collection '{story_id}' created or retrieved")
            except Exception as e:
                logger.error(f"Error creating collection '{story_id}': {e}")
                raise
        
        return self.collections[story_id]
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        try:
            embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def add_documents(self, story_id: str, documents: List[Dict[str, Any]]):
        """Add documents to the vector store"""
        if not documents:
            logger.warning("No documents to add")
            return
        
        try:
            collection = self._get_or_create_collection(story_id)
            
            # Prepare data for insertion
            ids = [str(uuid.uuid4()) for _ in documents]
            texts = [doc["text"] for doc in documents]
            metadatas = []
            
            for doc in documents:
                metadata = doc.get("metadata", {})
                metadata["text"] = doc["text"]
                metadata["story_id"] = story_id
                metadata["created_at"] = datetime.now().isoformat()
                metadatas.append(metadata)
            
            # Generate embeddings
            embeddings = self._generate_embeddings(texts)
            
            # Add to collection
            collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(documents)} documents to collection '{story_id}'")
            
        except Exception as e:
            logger.error(f"Error adding documents to collection '{story_id}': {e}")
            raise
    
    def retrieve_relevant(self, story_id: str, query: str, k: int = 5) -> Dict[str, Any]:
        """Retrieve relevant documents for a query"""
        try:
            collection = self._get_or_create_collection(story_id)
            
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])[0]
            
            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "text": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None
                })
            
            logger.info(f"Found {len(formatted_results)} results for query in '{story_id}'")
            
            return {
                "query": query,
                "results": formatted_results,
                "story_id": story_id
            }
            
        except Exception as e:
            logger.error(f"Error searching in collection '{story_id}': {e}")
            raise
    
    def search_all_stories(self, query: str, n_results: int = 10) -> Dict[str, Any]:
        """Search across all story collections"""
        try:
            # Get all collections
            all_collections = self.client.list_collections()
            all_results = []
            
            for collection_info in all_collections:
                story_id = collection_info.name
                try:
                    story_results = self.retrieve_relevant(story_id, query, n_results)
                    for result in story_results["results"]:
                        result["story_id"] = story_id
                        all_results.append(result)
                except Exception as e:
                    logger.warning(f"Error searching in collection '{story_id}': {e}")
                    continue
            
            # Sort by distance if available
            if all_results and all_results[0].get("distance") is not None:
                all_results.sort(key=lambda x: x["distance"])
            
            # Limit results
            all_results = all_results[:n_results]
            
            logger.info(f"Found {len(all_results)} total results across all stories")
            
            return {
                "query": query,
                "results": all_results,
                "total_collections": len(all_collections)
            }
            
        except Exception as e:
            logger.error(f"Error searching across all stories: {e}")
            raise
    
    def get_all_documents(self, story_id: str) -> Dict[str, Any]:
        """Get all documents from a collection"""
        try:
            collection = self._get_or_create_collection(story_id)
            return collection.get()
        except Exception as e:
            logger.error(f"Error getting all documents from collection '{story_id}': {e}")
            raise
    
    def get_story_info(self, story_id: str) -> Dict[str, Any]:
        """Get information about a story collection"""
        try:
            collection = self._get_or_create_collection(story_id)
            count = collection.count()
            
            return {
                "story_id": story_id,
                "document_count": count,
                "metadata": collection.metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Error getting info for collection '{story_id}': {e}")
            raise
    
    def list_stories(self) -> List[Dict[str, Any]]:
        """List all available story collections"""
        try:
            collections = self.client.list_collections()
            stories = []
            
            for collection in collections:
                story_id = collection.name
                info = self.get_story_info(story_id)
                stories.append(info)
            
            logger.info(f"Found {len(stories)} story collections")
            return stories
            
        except Exception as e:
            logger.error(f"Error listing stories: {e}")
            raise
    
    def delete_story(self, story_id: str) -> bool:
        """Delete a story collection"""
        try:
            self.client.delete_collection(name=story_id)
            if story_id in self.collections:
                del self.collections[story_id]
            
            logger.info(f"Deleted collection '{story_id}'")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting collection '{story_id}': {e}")
            return False