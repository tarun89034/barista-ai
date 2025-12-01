"""Memory Agent for storing and retrieving portfolio context using vector database."""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import json

from src.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class MemoryAgent(BaseAgent):
    """Agent for managing portfolio memory and historical context."""
    
    def __init__(self, collection_name: str = "portfolio_memory", 
                 use_vector_db: bool = False):
        super().__init__("MemoryAgent")
        self.collection_name = collection_name
        self.use_vector_db = use_vector_db
        self.memory_store = []
        
        if use_vector_db:
            try:
                import chromadb
                self.client = chromadb.Client()
                self.collection = self.client.create_collection(
                    name=collection_name,
                    get_or_create=True
                )
                logger.info(f"Memory Agent initialized with ChromaDB collection: {collection_name}")
            except ImportError:
                logger.warning("ChromaDB not available, falling back to in-memory storage")
                self.use_vector_db = False
        else:
            logger.info(f"Memory Agent initialized with in-memory storage")
    
    def execute(self, action: str, data: Dict) -> Dict:
        try:
            self.update_state("running")
            
            if action == "store":
                result = self.store_memory(data)
            elif action == "retrieve":
                result = self.retrieve_memories(data.get("query", ""), data.get("limit", 5))
            elif action == "search":
                result = self.search_similar(data.get("query", ""), data.get("limit", 5))
            else:
                raise ValueError(f"Unknown action: {action}")
            
            self.update_state("completed")
            return result
            
        except Exception as e:
            self.update_state("failed")
            self.handle_error(e, f"Error executing memory action: {action}")
            raise
    
    def store_memory(self, data: Dict) -> Dict:
        memory_id = f"mem_{len(self.memory_store) + 1}"
        memory_entry = {
            "id": memory_id,
            "timestamp": datetime.now().isoformat(),
            "type": data.get("type", "general"),
            "content": data.get("content", ""),
            "metadata": data.get("metadata", {})
        }
        
        self.memory_store.append(memory_entry)
        logger.info(f"Stored memory entry: {memory_id}")
        
        return {"success": True, "memory_id": memory_id}
    
    def retrieve_memories(self, query: str = "", limit: int = 5) -> Dict:
        memories = sorted(self.memory_store, key=lambda x: x["timestamp"], reverse=True)[:limit]
        return {"success": True, "count": len(memories), "memories": memories}
    
    def search_similar(self, query: str, limit: int = 5) -> Dict:
        results = []
        query_lower = query.lower()
        
        for memory in self.memory_store:
            if query_lower in memory.get("content", "").lower():
                results.append(memory)
        
        return {"success": True, "query": query, "count": len(results[:limit]), "results": results[:limit]}