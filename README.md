# LearnFast Core Engine

**A Hybrid Graph-RAG Learning Platform**

LearnFast Core Engine combines the structural reasoning of Knowledge Graphs with the semantic flexibility of Vector Search (RAG) to deliver intelligent, personalized, and time-constrained learning paths.

## 🚀 Key Features

- **Structured Knowledge Graph**: Uses Neo4j to model concepts and prerequisite relationships.
- **RAG Content Retrieval**: Uses PostgreSQL + pgvector to store and retrieve content chunks with semantic search.
- **Adaptive Navigation**: Unlocks concepts as you progress through the graph.
- **Time-Constrained Optimization**: Generates the most effective learning path that fits your available time budget.
- **Automated Ingestion**: Converts documents (PDF, DOCX, HTML) into structured graph nodes and content embeddings.

## 🏗 Architecture

The system uses a **Hybrid Graph-RAG** architecture:

1.  **Ingestion Layer**: 
    - LLMs extract concepts and relationships from documents.
    - Content is chunked and embedded for vector search.
2.  **Storage Layer**:
    - **Neo4j**: Stores the "Map" (Concepts, Relationships, User Progress).
    - **PostgreSQL**: Stores the "Library" (Content Chunks, Embeddings).
3.  **Logic Layer**:
    - **Navigation Engine**: Determines what is valid to learn next.
    - **Path Resolver**: Finds optimal paths and estimates learning time.
    - **Content Retriever**: Assembles lessons from distributed chunks.

## 🛠️ Prerequisites

- **Python 3.12+**
- **Docker & Docker Compose**
- **uv** (Python package manager)
- **Ollama** (running locally with `gpt-oss:20b-cloud` and `embeddinggemma:latest` models pulled)

## 🏁 Quick Start

### 1. Setup Environment

Clone the repository and install dependencies:

```bash
uv sync
cp .env.example .env
```

### 2. Start Services

Launch Neo4j, PostgreSQL, and ensure Ollama is ready:

```bash
./scripts/start_services.sh
```

*Services available at:*
- **Neo4j Browser**: [http://localhost:7475](http://localhost:7475) (user: `neo4j`, pass: `password`)
- **PostgreSQL**: `localhost:5433` (user: `learnfast`, pass: `password`)
- **API**: [http://localhost:8000](http://localhost:8000)

### 3. Run the Application

Start the FastAPI server:

```bash
uv run uvicorn main:app --reload
```

## 📖 Usage Guide

You can interact with the system via the REST API.

### 1. Ingest Content
Upload a document to build the knowledge graph.

```bash
curl -X POST "http://localhost:8000/ingest" \
  -F "file=@/path/to/textbook.pdf"
```

### 2. Check Available Concepts
See what you can learn (Root concepts are available initially).

```bash
curl "http://localhost:8000/concepts/roots"
```

### 3. Generate a Learning Path
Request a path to a specific target with a time limit (e.g., 30 minutes).

```bash
curl -X POST "http://localhost:8000/learning/path" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "target_concept": "advanced_calculus",
    "time_budget_minutes": 30
  }'
```

### 4. Get a Lesson
Retrieve the actual content for your path.

```bash
curl "http://localhost:8000/learning/lesson/user_123/advanced_calculus?time_budget=30"
```

### 5. Track Progress
Mark concepts as you complete them to unlock new paths.

```bash
# Start a concept
curl -X POST "http://localhost:8000/progress/start" \
  -d '{"user_id": "user_123", "concept_name": "limits"}'

# Complete a concept
curl -X POST "http://localhost:8000/progress/complete" \
  -d '{"user_id": "user_123", "concept_name": "limits"}'
```

## 🧪 Testing

The codebase is verified using **property-based testing** with `hypothesis`.

```bash
# Run all tests
uv run pytest

# Run specific integration tests
uv run pytest tests/test_api.py
```

## 📂 Project Structure

```
src/
├── ingestion/          # LLM extraction & vector embedding logic
├── navigation/         # Graph traversal & user state management
├── path_resolution/    # Shortest path & time budget optimization
├── database/           # Neo4j & PostgreSQL connection handlers
└── models/             # Shared Pydantic schemas
```

---
**LearnFast Core Engine** — *Optimizing the path to knowledge.*