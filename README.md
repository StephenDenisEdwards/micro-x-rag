# micro-x-rag

A RAG (Retrieval-Augmented Generation) system that indexes hardware product catalogs into a ChromaDB vector database and answers natural language queries using both local Ollama models and Anthropic Claude. Includes both standard RAG and GraphRAG approaches.

## Notebooks

### 1. Standard RAG — `rag_catalog_search.ipynb`

Classic vector-search RAG pipeline:

1. **Extract** — Pull text from PDF catalogs using PyMuPDF
2. **Chunk** — Split pages into overlapping segments with sentence-boundary awareness
3. **Embed** — Generate vector embeddings locally with Ollama `nomic-embed-text`
4. **Store** — Persist embeddings and metadata in ChromaDB
5. **Retrieve** — Semantic search for the most relevant catalog sections
6. **Generate** — Synthesize answers with source citations using Ollama or Claude

### 2. GraphRAG — `graph_rag_catalog_search.ipynb`

Knowledge graph-enhanced RAG that goes beyond simple vector search:

1. **Extract entities & relationships** from chunks using an LLM (Ollama, free/local)
2. **Build a knowledge graph** with NetworkX (products, specs, features, and their connections)
3. **Detect communities** using Louvain algorithm for thematic clustering
4. **Generate community summaries** for high-level understanding
5. **Retrieve via graph traversal + vector search + community summaries** for richer context
6. **Visualize** the knowledge graph interactively with pyvis
7. **Compare** Standard RAG vs GraphRAG on different query types

| Query Type | Standard RAG | GraphRAG |
|-----------|-------------|----------|
| Specific fact lookup | Great | Good |
| Multi-hop reasoning | Weak | Strong |
| Global/thematic questions | Weak | Strong |
| Cross-document synthesis | Weak | Strong |

## Prerequisites

- **Python 3.11+**
- **Ollama** running locally ([ollama.com](https://ollama.com))
- **Anthropic API key** (for Claude generation; set in `.env`)

### Ollama Models

```bash
ollama pull nomic-embed-text   # embeddings
ollama pull mistral:7b         # local chat (or any model you prefer)
```

## Setup

```bash
pip install -r requirements.txt
```

Copy your `.env` file to the project root with at minimum `ANTHROPIC_API_KEY` set. The `.env` file is gitignored.

## Project Structure

```
micro-x-rag/
├── catalogs/                          # PDF product catalogs (source documents)
├── chroma_db/                         # ChromaDB storage for standard RAG (created on first run)
├── chroma_db_graph/                   # ChromaDB storage for GraphRAG (created on first run)
├── notebooks/
│   ├── rag_catalog_search.ipynb       # Standard RAG notebook
│   └── graph_rag_catalog_search.ipynb # GraphRAG notebook
├── requirements.txt
└── README.md
```

Generated artifacts (gitignored):
- `chroma_db/` / `chroma_db_graph/` — persisted vector stores
- `extractions.json` — cached LLM entity extractions (avoids re-running)
- `knowledge_graph.html` — interactive graph visualization

## Usage

```bash
jupyter notebook notebooks/rag_catalog_search.ipynb
jupyter notebook notebooks/graph_rag_catalog_search.ipynb
```

**Standard RAG** — run cells in order. First run takes a few minutes for PDF ingestion. Subsequent runs can skip to query cells (section 10 has a reload snippet).

**GraphRAG** — run cells in order. The entity extraction step (section 4) is the slowest part as each chunk goes through the LLM. Results are cached to `extractions.json` so subsequent runs skip extraction. Set `MAX_PAGES_PER_PDF` to limit pages for a faster demo.

## Catalogs Included

| File | Description |
|------|-------------|
| `Wurth_Baer_Section_C.pdf` | Wurth Baer Section C |
| `wurth-baer-section-b-concealed-hinges.pdf` | Wurth Baer concealed hinges |
| `grass-tiomos-catalog.pdf` | Grass Tiomos hinge system |
| `grass-nexis-catalog.pdf` | Grass Nexis drawer system |

## Configuration

Key settings in each notebook's first cell:

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `OLLAMA_CHAT_MODEL` | `mistral:7b` | Local generation model |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude model for generation |
| `CHUNK_SIZE` | `1000` / `800` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` / `100` | Overlap between chunks |
| `MAX_PAGES_PER_PDF` | `30` (GraphRAG only) | Limit pages for faster demo |
