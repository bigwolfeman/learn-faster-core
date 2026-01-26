"""
Property-based tests for Content Retrieval verification.
"""

import pytest
import uuid
from hypothesis import given, strategies as st, settings
from unittest.mock import MagicMock

from src.path_resolution.content_retriever import ContentRetriever
from src.models.schemas import LearningChunk

# Initialize retriever
retriever = ContentRetriever()

class TestContentRetrieval:
    """Property-based tests for content retrieval and formatting."""

    @given(st.lists(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))), min_size=1, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_content_ordering(self, concepts):
        """
        **Feature: learnfast-core-engine, Property 13: Content ordering consistency**
        **Validates: Requirements 3.4**
        
        The generated lesson must follow the exact order of concepts in basic input.
        """
        # Mock the retrieve_chunks_by_concept method to return dummy content
        # We need to mock the instance method
        
        original_retrieve = retriever.retrieve_chunks_by_concept
        
        def mock_retrieve(concept):
            return [LearningChunk(
                id=1, 
                doc_source="test.md", 
                content=f"Content for {concept}", 
                concept_tag=concept
            )]
            
        retriever.retrieve_chunks_by_concept = mock_retrieve
        
        try:
            lesson = retriever.get_lesson_content(concepts)
            
            # Verify order by checking indices of concept headers
            last_index = -1
            for i, concept in enumerate(concepts):
                header = f"## {i+1}. {concept.title()}"
                
                # Should be present
                idx = lesson.find(header)
                assert idx != -1, f"Header for {concept} missing"
                
                # Should be after the previous one
                assert idx > last_index, f"Header for {concept} out of order"
                last_index = idx
                
                # Content should be present
                content_snippet = f"Content for {concept}"
                assert content_snippet in lesson
                
        finally:
            retriever.retrieve_chunks_by_concept = original_retrieve

    @given(st.lists(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))), min_size=1, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_lesson_formatting(self, concepts):
        """
        **Feature: learnfast-core-engine, Property 14: Lesson formatting completeness**
        **Validates: Requirements 3.5**
        
        Lesson should contain title, target, and concept headers.
        """
        original_retrieve = retriever.retrieve_chunks_by_concept
        retriever.retrieve_chunks_by_concept = lambda c: [] # Empty content is fine for structure check
        
        try:
            lesson = retriever.get_lesson_content(concepts)
            
            # Check mandatory structural elements
            assert "# Personalized Learning Path" in lesson
            assert "**Target Goal**" in lesson
            assert str(concepts[-1].title()) in lesson
            
            for i, concept in enumerate(concepts):
                assert f"## {i+1}. {concept.title()}" in lesson
                
        finally:
            retriever.retrieve_chunks_by_concept = original_retrieve
