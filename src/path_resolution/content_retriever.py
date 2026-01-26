"""
Content Retrieval Engine for LearnFast Core.

Handles retrieval of learning chunks and lesson formatting.
"""

import logging
from typing import List, Dict, Any, Optional

from src.database.connections import postgres_conn
from src.models.schemas import LearningChunk

logger = logging.getLogger(__name__)


class ContentRetriever:
    """
    Retrieves and formats learning content.
    """
    
    def __init__(self):
        """Initialize the content retriever."""
        self.connection = postgres_conn
        
    def retrieve_chunks_by_concept(self, concept: str) -> List[LearningChunk]:
        """
        Retrieve all content chunks associated with a specific concept.
        
        Args:
            concept: Concept name
            
        Returns:
            List of LearningChunk objects
        """
        if not concept:
            return []
            
        try:
            query = """
                SELECT id, doc_source, content, concept_tag, created_at
                FROM learning_chunks
                WHERE lower(concept_tag) = lower(%s)
                ORDER BY id ASC
            """
            
            # Using execute_query from connection wrapper
            results = self.connection.execute_query(query, (concept,))
            
            chunks = []
            for row in results:
                # We do not retrieve embedding here to save bandwidth
                chunks.append(LearningChunk(
                    id=row['id'],
                    doc_source=row['doc_source'],
                    content=row['content'],
                    concept_tag=row['concept_tag'],
                    created_at=row['created_at']
                ))
                
            return chunks
            
        except Exception as e:
            logger.error(f"Error retrieving chunks for concept '{concept}': {str(e)}")
            return []

    def get_lesson_content(self, path_concepts: List[str]) -> str:
        """
        Generate a complete formatted lesson for a learning path.
        
        Retrieves chunks for each concept in order and formats them.
        
        Args:
            path_concepts: Ordered list of concept names
            
        Returns:
            Formatted Markdown string
        """
        if not path_concepts:
            return ""
            
        lesson_parts = []
        
        # Add Title
        lesson_parts.append(f"# Personalized Learning Path\n")
        lesson_parts.append(f"**Target Goal**: {path_concepts[-1].title()}\n")
        lesson_parts.append("---\n")
        
        for i, concept in enumerate(path_concepts):
            try:
                # Add Concept Header
                concept_title = concept.title()
                lesson_parts.append(f"## {i+1}. {concept_title}\n")
                
                # Retrieve content
                chunks = self.retrieve_chunks_by_concept(concept)
                
                if not chunks:
                    lesson_parts.append("*No content available for this concept.*\n")
                    continue
                
                # Add chunks
                for j, chunk in enumerate(chunks):
                    # We can add source info if needed
                    # lesson_parts.append(f"_{chunk.doc_source}_\n")
                    lesson_parts.append(f"{chunk.content}\n")
                    
                lesson_parts.append("---\n")
                
            except Exception as e:
                logger.error(f"Error processing concept '{concept}' for lesson: {str(e)}")
                lesson_parts.append(f"*Error loading content for {concept}*\n")
        
        return "\n".join(lesson_parts)

    def format_lesson(self, content_chunks: List[LearningChunk]) -> str:
        """
        Format a list of chunks into a lesson string.
        (Helper method if needed strictly for chunk list)
        """
        return "\n\n".join([c.content for c in content_chunks])
