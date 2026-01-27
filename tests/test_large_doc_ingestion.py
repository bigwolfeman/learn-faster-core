import pytest
import os
from unittest.mock import MagicMock, patch
from src.ingestion.ingestion_engine import IngestionEngine
from src.models.schemas import GraphSchema, PrerequisiteLink

class TestLargeDocIngestion:
    
    @pytest.fixture
    def engine(self):
        with patch('src.ingestion.ingestion_engine.ollama.Client') as mock_client:
            engine = IngestionEngine(model="test-model")
            engine._client = mock_client.return_value
            return engine

    def test_init_with_env_var(self):
        """Test that window size is read from environment variable."""
        with patch.dict(os.environ, {"OLLAMA_CONTEXT_WINDOW_CHARS": "12345"}):
            with patch('src.ingestion.ingestion_engine.ollama.Client'):
                engine = IngestionEngine()
                assert engine.MAX_EXTRACTION_CHARS == 12345

    def test_create_extraction_windows_small_doc(self, engine):
        """Test that small docs return a single window."""
        content = "Small document content."
        engine.MAX_EXTRACTION_CHARS = 100
        windows = engine._create_extraction_windows(content)
        assert len(windows) == 1
        assert windows[0] == content

    def test_create_extraction_windows_large_doc(self, engine):
        """Test splitting logic for large docs."""
        # Create paragraphs
        para1 = "a" * 60
        para2 = "b" * 60
        para3 = "c" * 60
        content = f"{para1}\n\n{para2}\n\n{para3}"
        
        # Set max chars to force split after para1
        engine.MAX_EXTRACTION_CHARS = 100
        
        windows = engine._create_extraction_windows(content)
        
        # Window 1: para1 + para2 (60+60=120? No wait, logic checks BEFORE appending)
        # 0 + 60 <= 100 (append para1)
        # 60 + 60 > 100 (full) -> save para1. new window [para1, para2]
        
        # Let's trace the logic:
        # P1 (60): curr=60, win=[P1]
        # P2 (60): curr+60=120 > 100.
        #   Save win: "P1"
        #   New win: [P1, P2]. curr=120.
        # P3 (60): curr+60=180 > 100.
        #   Save win: "P1\n\nP2"
        #   New win: [P2, P3]. curr=120.
        # End loop. Save: "P2\n\nP3"
        
        # Wait, the logic is:
        # if current_size + para_len > MAX:
        #    save window
        #    overlap = last para
        #    new window = [overlap, current_para]
        
        # This overlap logic seems aggressive if paragraphs are huge, but fine for test.
        # Result should be multiple windows with overlap.
        
        assert len(windows) >= 2
        # Check overlap
        assert para2 in windows[0] or para2 in windows[1]

    def test_merge_schemas_deduplication(self, engine):
        """Test merging schemas with overlapping concepts."""
        schema1 = GraphSchema(
            concepts=["a", "b"],
            prerequisites=[
                PrerequisiteLink(source_concept="a", target_concept="b", weight=0.5, reasoning="r1")
            ]
        )
        schema2 = GraphSchema(
            concepts=["b", "c"],
            prerequisites=[
                PrerequisiteLink(source_concept="b", target_concept="c", weight=0.8, reasoning="r2")
            ]
        )
        
        merged = engine._merge_schemas([schema1, schema2])
        
        assert len(merged.concepts) == 3
        assert set(merged.concepts) == {"a", "b", "c"}
        assert len(merged.prerequisites) == 2

    def test_merge_schemas_conflict_resolution(self, engine):
        """Test prioritizing higher weight for duplicate prerequisites."""
        schema1 = GraphSchema(
            concepts=["a", "b"],
            prerequisites=[
                PrerequisiteLink(source_concept="a", target_concept="b", weight=0.5, reasoning="low")
            ]
        )
        schema2 = GraphSchema(
            concepts=["a", "b"],
            prerequisites=[
                PrerequisiteLink(source_concept="a", target_concept="b", weight=0.9, reasoning="high")
            ]
        )
        
        merged = engine._merge_schemas([schema1, schema2])
        
        assert len(merged.prerequisites) == 1
        assert merged.prerequisites[0].weight == 0.9
        assert merged.prerequisites[0].reasoning == "high"
