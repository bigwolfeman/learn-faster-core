"""
Property-based tests for Path Resolution verification.
"""

import pytest
import uuid
from hypothesis import given, strategies as st, settings
from unittest.mock import MagicMock

from src.database.graph_storage import graph_storage
from src.database.connections import postgres_conn
from src.path_resolution.path_resolver import PathResolver, MINUTES_PER_CHUNK
from src.models.schemas import ConceptNode, PrerequisiteLink

# Initialize resolver
resolver = PathResolver()

class TestPathResolution:
    """Property-based tests for path resolution."""
    
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

    @given(st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=5))
    @settings(max_examples=50, deadline=None)
    def test_time_estimation_mocked(self, chunk_counts):
        """
        **Feature: learnfast-core-engine, Property 11: Time estimation accuracy**
        **Validates: Requirements 3.2**
        
        Time estimation should strictly follow the formula: sum(chunks) * MINUTES_PER_CHUNK.
        This test MOCKS the postgres connection to isolate logic.
        """
        concepts = [f"c_{i}" for i in range(len(chunk_counts))]
        
        # Mock postgres execution
        # We need to compute total expected chunks to set up the mock return
        total_chunks = sum(chunk_counts)
        
        # Create a mock for this specific test run
        mock_pg = MagicMock()
        mock_pg.execute_query.return_value = [{'chunk_count': total_chunks}]
        
        # Inject mock
        original_pg = resolver.pg_connection
        resolver.pg_connection = mock_pg
        
        try:
            estimate = resolver.estimate_learning_time(concepts)
            expected = total_chunks * MINUTES_PER_CHUNK
            
            assert estimate == expected, f"Expected {expected} minutes, got {estimate}"
            
        finally:
            resolver.pg_connection = original_pg

    @given(st.data())
    @settings(max_examples=50, deadline=None)
    def test_path_pruning_constraints(self, data):
        """
        **Feature: learnfast-core-engine, Property 12: Time constraint satisfaction**
        **Validates: Requirements 3.3**
        
        Pruned paths must always have estimated time <= time_limit.
        And must be a prefix of the original path.
        """
        # Generate a path of concepts
        path_len = data.draw(st.integers(min_value=1, max_value=10))
        path = [f"concept_{i}" for i in range(path_len)]
        
        # Generate random 'times' for these concepts (mocked)
        times = [data.draw(st.integers(min_value=2, max_value=20)) for _ in range(path_len)]
        
        # Total time
        total_time = sum(times)
        
        # Pick a limit 
        limit = data.draw(st.integers(min_value=1, max_value=total_time + 10))
        
        # Mock resolver time estimation to return values from our 'times' list
        # This is tricky because estimate_learning_time takes a LIST.
        # But prune_path_by_time calls it one by one.
        
        def mock_estimate(concepts):
            t = 0
            for c in concepts:
                idx = int(c.split('_')[1])
                t += times[idx]
            return t
            
        # Monkey patch estimate method for this test instance?
        # Or better, mock the internal call.
        original_estimate = resolver.estimate_learning_time
        resolver.estimate_learning_time = mock_estimate
        
        try:
            pruned_path, prune_time = resolver.prune_path_by_time(path, limit)
            
            # Property 1: Time constraint satisfied
            assert prune_time <= limit, f"Pruned time {prune_time} exceeds limit {limit}"
            
            # Property 2: Path is prefix
            assert path[:len(pruned_path)] == pruned_path, "Pruned path is not a prefix of original"
            
            # Property 3: Optimality (cannot add next one)
            if len(pruned_path) < len(path):
                next_concept = path[len(pruned_path)]
                next_time = times[int(next_concept.split('_')[1])]
                assert prune_time + next_time > limit, "Pruning was too aggressive, could have fit more"
                
        finally:
            resolver.estimate_learning_time = original_estimate

    @given(st.lists(st.integers(min_value=1, max_value=5), min_size=2, max_size=5))
    @settings(max_examples=20, deadline=None)
    def test_shortest_path_resolution(self, chain_lengths):
        """
        **Feature: learnfast-core-engine, Property 10: Shortest path optimization**
        **Validates: Requirements 3.1**
        
        The resolved path should follow the prerequisite chain structure.
        """
        if not graph_storage.verify_constraints():
            pytest.skip("Database constraints not active")
            
        test_id = str(uuid.uuid4())[:8]
        prefix = f"test_{self.session_id}_{test_id}_"
        user_id = f"user_{self.session_id}_{test_id}"
        
        # Create a chain A -> B -> C ...
        chain_len = chain_lengths[0] # Just use first length
        concepts = [f"{prefix}c_{i}" for i in range(chain_len)]
        
        nodes = [ConceptNode(name=c) for c in concepts]
        graph_storage.store_concepts_batch(nodes)
        
        for i in range(chain_len - 1):
            link = PrerequisiteLink(
                source_concept=concepts[i],
                target_concept=concepts[i+1],
                weight=1.0, 
                reasoning="chain"
            )
            graph_storage.store_prerequisite_relationship(link)
            
        target = concepts[-1]
        
        # We need to mock chunk counts so estimation doesn't fail/return 0
        # Mocking PG calls again
        mock_pg = MagicMock()
        mock_pg.execute_query.return_value = [{'chunk_count': 5}] # 10 mins per concept
        
        original_pg = resolver.pg_connection
        resolver.pg_connection = mock_pg
        
        try:
            # Resolve path with huge budget
            path_obj = resolver.resolve_path(user_id, target, 1000)
            
            assert path_obj is not None
            assert not path_obj.pruned
            
            # Path should match the chain (normalized)
            expected = [c.lower() for c in concepts]
            assert path_obj.concepts == expected
            assert path_obj.target_concept == target.lower()
            
        finally:
            resolver.pg_connection = original_pg
