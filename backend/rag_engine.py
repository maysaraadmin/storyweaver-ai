from typing import List, Dict, Any, Optional
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_community.llms import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
from vector_store import VectorStoreManager
from story_logic import StoryLogicExtractor
from models import StoryLogicDataset, ChatResponse, ExpansionProposal

class RAGChatbot:
    def __init__(self, model_name="microsoft/DialoGPT-medium"):
        self.vector_store = VectorStoreManager()
        self.logic_extractor = StoryLogicExtractor()
        self.story_datasets = {}  # story_id -> StoryLogicDataset
        
        # Load local LLM
        self.llm = self._load_local_llm(model_name)
        
        # Define prompts
        self.qa_prompt = PromptTemplate(
            input_variables=["context", "question", "story_logic"],
            template="""
            You are a helpful assistant for a children's illustration book website.
            You have access to the following story context and logic rules.
            
            STORY CONTEXT:
            {context}
            
            STORY LOGIC RULES:
            {story_logic}
            
            USER QUESTION: {question}
            
            Answer the question based on the story context while respecting the story logic rules.
            If you cannot answer from the context, say so politely.
            Keep responses friendly, engaging, and appropriate for children.
            """
        )
        
        self.validation_prompt = PromptTemplate(
            input_variables=["proposal", "story_logic", "existing_context"],
            template="""
            Validate if this story expansion proposal is permissible:
            
            PROPOSAL: {proposal}
            
            EXISTING STORY LOGIC:
            {story_logic}
            
            EXISTING CONTEXT:
            {existing_context}
            
            Check for:
            1. Consistency with established characters
            2. Adherence to world rules
            3. Logical cause-and-effect
            4. Thematic alignment
            
            Return validation result as JSON:
            {{
                "is_permissible": true/false,
                "reasoning": "explanation",
                "suggestions": ["suggestion1", "suggestion2"]
            }}
            """
        )
        
        self.qa_chain = LLMChain(llm=self.llm, prompt=self.qa_prompt)
    
    def _load_local_llm(self, model_name: str):
        """Load a local Hugging Face model"""
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            low_cpu_mem_usage=True
        )
        
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=256,
            temperature=0.7,
            do_sample=True
        )
        
        return HuggingFacePipeline(pipeline=pipe)
    
    def query_story(self, story_id: str, question: str) -> ChatResponse:
        """Query a specific story with RAG"""
        # Retrieve relevant documents
        results = self.vector_store.retrieve_relevant(story_id, question)
        
        # Format context
        context = "\n".join(results['documents'][0]) if results['documents'] else "No relevant context found."
        
        # Get story logic
        story_logic = self._format_story_logic(story_id)
        
        # Generate response
        response = self.qa_chain.run(
            context=context,
            question=question,
            story_logic=story_logic
        )
        
        return ChatResponse(
            response=response,
            is_permissible=True,
            reasoning="Standard query response"
        )
    
    def propose_expansion(self, proposal: ExpansionProposal) -> ChatResponse:
        """Validate and respond to story expansion proposal"""
        story_id = proposal.story_id
        
        if story_id not in self.story_datasets:
            return ChatResponse(
                response="Story not found in dataset.",
                is_permissible=False,
                reasoning="Story ID does not exist"
            )
        
        dataset = self.story_datasets[story_id]
        
        # Get relevant context for validation
        results = self.vector_store.retrieve_relevant(story_id, proposal.new_content, k=3)
        existing_context = "\n".join(results['documents'][0]) if results['documents'] else ""
        
        # Format story logic for validation
        story_logic_str = self._format_story_logic(story_id)
        
        # Validate with LLM
        validation_input = self.validation_prompt.format(
            proposal=proposal.new_content,
            story_logic=story_logic_str,
            existing_context=existing_context
        )
        
        validation_result = self.llm(validation_input)
        
        # Parse validation result (simplified - in practice would parse JSON)
        is_permissible = "true" in validation_result.lower() or "permissible" in validation_result.lower()
        
        return ChatResponse(
            response=f"Your expansion proposal has been {'approved' if is_permissible else 'rejected'}.",
            is_permissible=is_permissible,
            reasoning=validation_result,
            suggestions=["Consider character consistency", "Check timeline alignment"]
        )
    
    def _format_story_logic(self, story_id: str) -> str:
        """Format story logic dataset as string"""
        if story_id not in self.story_datasets:
            return "No story logic available."
        
        dataset = self.story_datasets[story_id]
        logic_str = f"Title: {dataset.title}\n\n"
        
        # Group elements by type
        by_type = {}
        for element in dataset.elements:
            by_type.setdefault(element.element_type.value, []).append(element)
        
        for element_type, elements in by_type.items():
            logic_str += f"\n{element_type.upper()}S:\n"
            for element in elements:
                logic_str += f"- {element.name}: {element.description}\n"
        
        if dataset.rules:
            logic_str += "\nRULES:\n"
            for rule in dataset.rules:
                logic_str += f"- {rule.get('description', '')}\n"
        
        return logic_str
    
    def update_dataset(self, story_id: str, new_content: Dict):
        """Update story dataset with new content"""
        if story_id not in self.story_datasets:
            # Create new dataset
            self.story_datasets[story_id] = StoryLogicDataset(
                story_id=story_id,
                title=new_content.get("title", "Untitled"),
                elements=[],
                rules=[],
                contradictions=[],
                last_updated=datetime.now()
            )
        
        # Extract elements from new content
        new_elements = self.logic_extractor.extract_story_elements([new_content])
        
        # Check consistency and add if permissible
        for element in new_elements:
            consistency_check = self.logic_extractor.check_consistency(
                element, self.story_datasets[story_id]
            )
            
            if consistency_check["is_consistent"]:
                self.story_datasets[story_id].elements.append(element)
                self.story_datasets[story_id].version += 1
        
        # Update vector store
        self.vector_store.add_documents(story_id, [{
            "text": new_content.get("text", ""),
            "metadata": {
                "page": new_content.get("page_number", 0),
                "type": "expansion",
                "timestamp": datetime.now().isoformat()
            }
        }])