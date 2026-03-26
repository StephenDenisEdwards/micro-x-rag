# micro-x-rag

A RAG (Retrieval-Augmented Generation) system that indexes hardware product catalogs into a ChromaDB vector database and answers natural language queries. Includes both standard RAG and GraphRAG (knowledge graph-enhanced retrieval) approaches, with configurable model providers for each pipeline operation.

## What You Can Do

- Ask natural language questions about hardware product catalogs
- Find compatible products across multiple catalogs
- Get thematic overviews of product categories and their relationships
- Compare hinge systems, mounting plates, and accessories across manufacturers
- Explore a knowledge graph of extracted entities and relationships

## Key Features

- **Standard RAG** — vector search over chunked catalog text
- **GraphRAG** — knowledge graph-enhanced retrieval with community summaries
- **Configurable providers** — each operation (extraction, summaries, answers, embeddings) has its own provider and model setting
- **Multi-provider support** — Anthropic Claude (cloud) and Ollama (local) for chat; Ollama and Voyage AI for embeddings
- **Extraction caching** — entity extraction results saved to disk, avoiding repeated API calls
- **Interactive visualization** — knowledge graph rendered as an interactive HTML page

## Notebooks

### 1. Standard RAG — `rag_catalog_search.ipynb`

Classic vector-search RAG pipeline:

1. **Extract** text from PDF catalogs using PyMuPDF
2. **Chunk** pages into overlapping segments with sentence-boundary awareness
3. **Embed** chunks locally with Ollama `nomic-embed-text`
4. **Store** embeddings and metadata in ChromaDB
5. **Retrieve** the most relevant catalog sections via semantic search
6. **Generate** answers with source citations using Claude or Ollama

### 2. GraphRAG — `graph_rag_catalog_search.ipynb`

Knowledge graph-enhanced RAG that goes beyond simple vector search:

1. **Extract entities & relationships** from chunks using an LLM
2. **Build a knowledge graph** with NetworkX (products, specs, features, and their connections)
3. **Detect communities** using the Louvain algorithm for thematic clustering
4. **Generate community summaries** for high-level understanding
5. **Retrieve via graph traversal + vector search + community summaries** for richer context
6. **Compare** Standard RAG vs GraphRAG on different query types

| Query Type | Standard RAG | GraphRAG |
|-----------|-------------|----------|
| Specific fact lookup | Good | Good |
| Multi-hop reasoning | Weak | Strong |
| Global/thematic questions | Weak | Strong |
| Cross-document synthesis | Weak | Strong |

## Prerequisites

- **Python 3.11+**
- **Ollama** running locally ([ollama.com](https://ollama.com))
- **Anthropic API key** (set in `.env`)

### Ollama Models

```bash
ollama pull nomic-embed-text   # embeddings (required)
```

## Setup

```bash
git clone https://github.com/StephenDenisEdwards/micro-x-rag.git
cd micro-x-rag
cp .env.example .env   # Add your API keys
pip install -r requirements.txt
```

## Configuration

All model configuration is in the GraphRAG notebook's **first code cell** (Setup & Configuration). Each operation has its own provider (`"anthropic"` or `"ollama"`) and model:

| Operation | Provider | Model | Purpose |
|-----------|----------|-------|---------|
| Extraction | `anthropic` | `claude-sonnet-4-20250514` | Entity & relationship extraction |
| Summaries | `anthropic` | `claude-sonnet-4-20250514` | Community summary generation |
| Answers | `anthropic` | `claude-sonnet-4-20250514` | Final answer generation |
| Embeddings | `ollama` | `nomic-embed-text` | Vector embeddings |

To use a different model for any operation, change its provider and model in the config cell. For example, to use a local model for summaries:

```python
SUMMARY_PROVIDER = "ollama"
SUMMARY_MODEL    = "mistral:7b"
```

Pipeline settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_PAGES_PER_PDF` | `None` (all) | Limit pages per PDF for faster runs |
| `FORCE_RE_EXTRACT` | `False` | Set `True` to re-run extraction (ignores cache) |
| `CHUNK_SIZE` | `800` | Characters per text chunk |
| `CHUNK_OVERLAP` | `100` | Overlap between chunks |

## Usage

```bash
jupyter notebook notebooks/rag_catalog_search.ipynb
jupyter notebook notebooks/graph_rag_catalog_search.ipynb
```

**Standard RAG** — run cells in order. First run takes a few minutes for PDF ingestion.

**GraphRAG** — run cells in order. Entity extraction is cached to `extractions.json`. To re-run community summaries with a different model without re-extracting, just change `SUMMARY_PROVIDER` / `SUMMARY_MODEL` and re-run from the top with `FORCE_RE_EXTRACT = False`.

## Project Structure

```
micro-x-rag/
├── notebooks/                              # Jupyter notebooks (main workflow)
│   ├── rag_catalog_search.ipynb            # Standard RAG
│   ├── graph_rag_catalog_search.ipynb      # GraphRAG (main notebook)
│   ├── graph_rag_catalog_search_executed.ipynb   # Executed with mistral:7b summaries
│   └── graph_rag_catalog_search_executed_2.ipynb # Executed with Claude summaries
├── catalogs/                               # Source PDF product catalogs
├── scripts/                                # Standalone utility scripts
├── docs/                                   # Project documentation
│   ├── architecture/decisions/             # Architecture Decision Records
│   ├── design/                             # Design docs, analysis, comparisons
│   └── planning/                           # Roadmaps and improvement plans
├── requirements.txt                        # Python dependencies
├── .env.example                            # Environment variable template
├── CLAUDE.md                               # AI assistant project context
├── CONTRIBUTING.md                         # Contribution guidelines
├── CHANGELOG.md                            # Version history
└── README.md                               # This file
```

Generated artifacts (gitignored):
- `chroma_db/` / `chroma_db_graph/` — persisted vector stores
- `extractions.json` — cached LLM entity extractions
- `knowledge_graph.html` — interactive graph visualization

## Catalogs Included

| File | Description |
|------|-------------|
| `Wurth_Baer_Section_C.pdf` | Wurth Baer Section C — specialty hinges, lid supports |
| `wurth-baer-section-b-concealed-hinges.pdf` | Wurth Baer Section B — concealed hinges |
| `grass-tiomos-catalog.pdf` | Grass Tiomos hinge system |
| `grass-nexis-catalog.pdf` | Grass Nexis hinge system |

## Documentation

| Document | Description |
|----------|-------------|
| [GraphRAG Notebook Guide](docs/design/graphrag-notebook-guide.md) | Step-by-step explanation of every notebook cell |
| [GraphRAG vs Standard RAG](docs/design/graphrag-vs-standard-rag.md) | Comparison with test results and model upgrade analysis |
| [Graph Analysis](docs/design/graph-rag-analysis.md) | Knowledge graph quality metrics and improvement tracking |
| [Improvement Roadmap](docs/planning/graphrag-improvement-roadmap.md) | Prioritized improvement plan |
| [Deterministic Compatibility](docs/design/deterministic-compatibility-integration.md) | Design for integrating a compatibility service |
| [Hybrid Long-Context](docs/design/hybrid-long-context-approach.md) | Combining long context with structured data layers |
| [ADR-001: Configurable Providers](docs/architecture/decisions/ADR-001-configurable-providers.md) | Provider/model per operation architecture decision |
