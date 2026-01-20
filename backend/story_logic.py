import spacy
import logging
import subprocess
import sys
from typing import List, Dict, Any
import json
from models import StoryElement, StoryElementType, StoryLogicDataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StoryLogicExtractor:
    def __init__(self):
        self.nlp = self._load_spacy_model()
    
    def _load_spacy_model(self):
        """Load spaCy model with proper error handling"""
        try:
            return spacy.load("en_core_web_sm")
        except OSError:
            logger.info("spaCy model not found, downloading...")
            try:
                subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
                logger.info("spaCy model downloaded successfully")
                return spacy.load("en_core_web_sm")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to download spaCy model: {e}")
                raise RuntimeError(f"Failed to download spaCy model: {e}")
            except Exception as e:
                logger.error(f"Unexpected error loading spaCy model: {e}")
                raise RuntimeError(f"Unexpected error loading spaCy model: {e}")
    
    def extract_5w1h(self, text: str) -> Dict[str, List[str]]:
        """Extract Who, What, When, Where, Why, How"""
        doc = self.nlp(text)
        
        result = {
            "who": [],
            "what": [],
            "when": [],
            "where": [],
            "why": [],
            "how": []
        }
        
        for token in doc:
            # Simple rule-based extraction (can be enhanced)
            if token.pos_ in ["PROPN", "NOUN"] and token.dep_ in ["nsubj", "nsubjpass"]:
                result["who"].append(token.text)
            elif token.pos_ == "VERB":
                result["what"].append(token.lemma_)
            elif token.ent_type_ == "TIME":
                result["when"].append(token.text)
            elif token.ent_type_ == "GPE" or token.ent_type_ == "LOC":
                result["where"].append(token.text)
        
        return result
    
    def extract_story_elements(self, pages: List[Dict]) -> List[StoryElement]:
        """Extract story elements from pages"""
        elements = []
        element_counter = {}
        
        for page in pages:
            page_num = page.get("page_number", 0)
            text = page.get("text", "")
            doc = self.nlp(text)
            
            # Extract characters (proper nouns)
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    char_id = f"char_{ent.text.lower().replace(' ', '_')}"
                    if char_id not in element_counter:
                        element = StoryElement(
                            element_id=char_id,
                            element_type=StoryElementType.CHARACTER,
                            name=ent.text,
                            description=f"Character appearing on page {page_num}",
                            attributes={"first_appearance": page_num},
                            relationships=[],
                            source_page=page_num
                        )
                        elements.append(element)
                        element_counter[char_id] = element
            
            # Extract locations
            for ent in doc.ents:
                if ent.label_ in ["GPE", "LOC", "FAC"]:
                    loc_id = f"loc_{ent.text.lower().replace(' ', '_')}"
                    if loc_id not in element_counter:
                        element = StoryElement(
                            element_id=loc_id,
                            element_type=StoryElementType.LOCATION,
                            name=ent.text,
                            description=f"Location mentioned on page {page_num}",
                            attributes={},
                            relationships=[],
                            source_page=page_num
                        )
                        elements.append(element)
                        element_counter[loc_id] = element
        
        return elements
    
    def check_consistency(self, new_element: StoryElement, dataset: StoryLogicDataset) -> Dict[str, Any]:
        """Check if new element is consistent with existing story logic"""
        contradictions = []
        suggestions = []
        
        for existing in dataset.elements:
            # Check for character consistency
            if existing.element_type == StoryElementType.CHARACTER and new_element.element_type == StoryElementType.CHARACTER:
                if existing.name.lower() == new_element.name.lower() and existing.attributes.get("species") != new_element.attributes.get("species"):
                    contradictions.append(f"Character {existing.name} has inconsistent attributes")
            
            # Check location rules
            if existing.element_type == StoryElementType.RULE and "location" in existing.description.lower():
                # Implement rule checking logic here
                pass
        
        return {
            "is_consistent": len(contradictions) == 0,
            "contradictions": contradictions,
            "suggestions": suggestions
        }