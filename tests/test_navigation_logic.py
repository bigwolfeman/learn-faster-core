"""
Property-based tests for Navigation Engine verification.
"""

import pytest
import uuid
from hypothesis import given, strategies as st, settings
from src.database.graph_storage import graph_storage
from src.navigation.navigation_engine import NavigationEngine
from src.navigation.user_tracker import UserProgressTracker
from src.models.schemas import ConceptNode, PrerequisiteLink

# Initialize engines
nav_engine = NavigationEngine()
user_tracker = UserProgressTracker()

class TestNavigationEngine:
    """Property-based tests for navigation logic."""
    
    @classmethod
    def setup_class(cls):
        """Set up test environment."""
        try:
            graph_storage.initialize_constraints()
        except Exception:
            pass
        cls.session_id = str(uuid.uuid4())[:8]
        
    def teardown_method(self):
        """Clean up after each test."""
        try:
            # Clean up session data
            graph_storage.connection.execute_write_query(
                f"MATCH (n) WHERE n.name STARTS WITH 'test_{self.session_id}_' OR n.uid STARTS WITH 'user_{self.session_id}_' DETACH DELETE n"
            )
        except Exception:
            pass

    @given(st.lists(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('L',))), min_size=1, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_root_concept_identification(self, concept_names):
        """
        **Feature: learnfast-core-engine, Property 6: Root concept identification**
        **Validates: Requirements 2.1**
        
        Concepts with no prerequisites must be identified as root concepts.
        """
        if not graph_storage.verify_constraints():
            pytest.skip("Database constraints not active")
            
        test_id = str(uuid.uuid4())[:8]
        prefix = f"test_{self.session_id}_{test_id}_"
        
        # Create concepts
        full_names = [prefix + name for name in concept_names]
        nodes = [ConceptNode(name=name) for name in full_names]
        graph_storage.store_concepts_batch(nodes)
        
        # Don't add any prerequisites
        
        roots = nav_engine.find_root_concepts()
        
        # All our created concepts should be in the roots list (normalized)
        normalized_inputs = [n.lower() for n in full_names]
        for name in normalized_inputs:
            assert name in roots, f"Concept {name} should be a root concept"

    @given(depth=st.integers(min_value=1, max_value=5))
    @settings(max_examples=20, deadline=None)
    def test_path_preview_depth(self, depth):
        """
        **Feature: learnfast-core-engine, Property 7: Path preview depth constraint**
        **Validates: Requirements 2.2**
        
        Path preview should respect the depth limit.
        """
        test_id = str(uuid.uuid4())[:8]
        prefix = f"test_{self.session_id}_{test_id}_"
        
        # Create a linear chain: A -> B -> C -> D -> E -> F
        chain_len = 6
        concepts = [f"{prefix}node_{i}" for i in range(chain_len)]
        nodes = [ConceptNode(name=name) for name in concepts]
        graph_storage.store_concepts_batch(nodes)
        
        for i in range(chain_len - 1):
            link = PrerequisiteLink(
                source_concept=concepts[i],
                target_concept=concepts[i+1],
                weight=1.0,
                reasoning="chain"
            )
            graph_storage.store_prerequisite_relationship(link)
            
        root = concepts[0]
        preview = nav_engine.get_path_preview(root, depth=depth)
        
        expected_len = min(chain_len, depth + 1)
        
        assert len(preview) == expected_len, \
            f"Expected {expected_len} nodes in preview (depth {depth}), got {len(preview)}"
            
        # Verify order
        for i in range(len(preview)):
            assert preview[i] == concepts[i].lower(), f"Preview order mismatch at index {i}"

    @given(st.data())
    @settings(max_examples=50, deadline=None)
    def test_prerequisite_validation(self, data):
        """
        **Feature: learnfast-core-engine, Property 8: Prerequisite completion validation**
        **Validates: Requirements 2.3, 2.4**
        
        A concept is only valid if all its prerequisites are completed.
        """
        if not graph_storage.verify_constraints():
            pytest.skip("Database constraints not active")
            
        test_id = str(uuid.uuid4())[:8]
        prefix = f"test_{self.session_id}_{test_id}_"
        user_id = f"user_{self.session_id}_{test_id}"
        
        # Create A -> B structure
        concept_a = f"{prefix}A"
        concept_b = f"{prefix}B"
        
        nodes = [ConceptNode(name=concept_a), ConceptNode(name=concept_b)]
        graph_storage.store_concepts_batch(nodes)
        
        link = PrerequisiteLink(
            source_concept=concept_a,
            target_concept=concept_b,
            weight=1.0,
            reasoning="A strict prereq for B"
        )
        graph_storage.store_prerequisite_relationship(link)
        
        # Case 1: Nothing completed
        assert nav_engine.validate_prerequisites(user_id, concept_a) is True, \
            "Root concept should be valid even if nothing completed"
        assert nav_engine.validate_prerequisites(user_id, concept_b) is False, \
            "Dependent concept should be invalid if prereq not completed"
            
        # Case 2: Complete A
        user_tracker.mark_completed(user_id, concept_a)
        
        assert nav_engine.validate_prerequisites(user_id, concept_b) is True, \
            "Dependent concept should be valid after prereq completed"

    @given(st.data())
    @settings(max_examples=50, deadline=None)
    def test_progress_persistence(self, data):
        """
        **Feature: learnfast-core-engine, Property 15: Progress state persistence**
        **Validates: Requirements 4.1, 4.2**
        
        User progress (IN_PROGRESS, COMPLETED) must be persisted correctly.
        """
        if not graph_storage.verify_constraints():
            pytest.skip("Database constraints not active")
            
        test_id = str(uuid.uuid4())[:8]
        prefix = f"test_{self.session_id}_{test_id}_"
        user_id = f"user_{self.session_id}_{test_id}"
        
        concept = f"{prefix}prog_test"
        graph_storage.store_concept(ConceptNode(name=concept))
        
        # Initial state
        state = user_tracker.get_user_state(user_id)
        assert concept.lower() not in state.in_progress_concepts
        assert concept.lower() not in state.completed_concepts
        
        # Mark in progress
        user_tracker.mark_in_progress(user_id, concept)
        state = user_tracker.get_user_state(user_id)
        assert concept.lower() in state.in_progress_concepts
        assert concept.lower() not in state.completed_concepts
        
        # Mark completed
        user_tracker.mark_completed(user_id, concept)
        state = user_tracker.get_user_state(user_id)
        assert concept.lower() not in state.in_progress_concepts  # Should be removed from in-progress
        assert concept.lower() in state.completed_concepts

    @given(st.data())
    @settings(max_examples=50, deadline=None)
    def test_available_concepts_consistency(self, data):
        """
        **Feature: learnfast-core-engine, Property 9: Available concept state consistency**
        **Validates: Requirements 2.5, 4.5**
        
        Available concepts must always be consistent with user progress and prerequisites.
        """
        if not graph_storage.verify_constraints():
            pytest.skip("Database constraints not active")
            
        test_id = str(uuid.uuid4())[:8]
        prefix = f"test_{self.session_id}_{test_id}_"
        user_id = f"user_{self.session_id}_{test_id}"
        
        # Create A -> B structure
        concept_a = f"{prefix}A"
        concept_b = f"{prefix}B"
        
        nodes = [ConceptNode(name=concept_a), ConceptNode(name=concept_b)]
        graph_storage.store_concepts_batch(nodes)
        
        link = PrerequisiteLink(
            source_concept=concept_a,
            target_concept=concept_b,
            weight=1.0,
            reasoning="A strict prereq for B"
        )
        graph_storage.store_prerequisite_relationship(link)
        
        # Initial state: only A should be available (root)
        unlocked = nav_engine.get_unlocked_concepts(user_id)
        assert concept_a.lower() in unlocked
        assert concept_b.lower() not in unlocked
        
        # Complete A
        user_tracker.mark_completed(user_id, concept_a)
        
        # New state: B should be available now (completed logic may hide completed ones? 
        # get_unlocked_concepts implementation excludes completed ones)
        
        unlocked = nav_engine.get_unlocked_concepts(user_id)
        assert concept_a.lower() not in unlocked  # Already completed
        assert concept_b.lower() in unlocked      # Now unlocked
