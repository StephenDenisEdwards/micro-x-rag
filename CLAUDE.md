# CLAUDE.md — Project Context for AI Assistants

## Project

**micro-x-rag** — A RAG (Retrieval-Augmented Generation) system that indexes hardware product catalogs into ChromaDB and answers queries using both standard vector search and GraphRAG (knowledge graph-enhanced retrieval). Supports multiple LLM providers (Anthropic Claude, Ollama local models).

## Language & Layout

- **Python 3.11+**, notebook-first workflow
- Package manager: `pip` or `uv`
- Config: notebook Setup & Configuration cell (provider/model per operation)
- Secrets: `.env` file (never commit)

## Key Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run notebooks
jupyter notebook notebooks/rag_catalog_search.ipynb
jupyter notebook notebooks/graph_rag_catalog_search.ipynb

# Pull required Ollama models
ollama pull nomic-embed-text   # embeddings
ollama pull mistral:7b         # local chat (optional, if using ollama provider)
```

## Architecture Overview

```
PDF Catalogs
    │
    ├─────────────────────────────────────┐
    ▼                                     ▼
Extract text (PyMuPDF)              Embed chunks (nomic-embed-text)
    │                                     │
    ▼                                     ▼
Chunk text (800 chars, 100 overlap) Store in ChromaDB
    │                                     │
    ▼                                     │
Extract entities & relationships    ┌─────┘
(Claude API)                        │
    │                               │
    ▼                               │
Post-process (normalize,            │
deduplicate, filter)                │
    │                               │
    ▼                               │
Build knowledge graph (NetworkX)    │
    │                               │
    ▼                               │
Detect communities (Louvain)        │
    │                               │
    ▼                               │
Summarize communities (LLM)        │
    │                               │
    ▼                               │
Embed summaries in ChromaDB ────────┘
    │
    ▼
Query time: vector search + graph traversal + community summaries → LLM → Answer
```

## Key Files

| File | Purpose |
|------|---------|
| `notebooks/rag_catalog_search.ipynb` | Standard RAG pipeline |
| `notebooks/graph_rag_catalog_search.ipynb` | GraphRAG pipeline (main notebook) |
| `notebooks/graph_rag_catalog_search_executed.ipynb` | Executed GraphRAG with mistral:7b summaries |
| `notebooks/graph_rag_catalog_search_executed_2.ipynb` | Executed GraphRAG with Claude summaries |
| `catalogs/*.pdf` | Source PDF product catalogs |
| `extractions.json` | Cached entity extraction results (gitignored) |
| `knowledge_graph.html` | Interactive graph visualization (gitignored) |
| `scripts/extract_standalone.py` | Standalone extraction script |
| `.env` | API keys (gitignored) |

## Configuration

All model configuration is in the notebook's **first code cell** (Setup & Configuration). Each operation has its own provider and model:

```python
EXTRACTION_PROVIDER = "anthropic"          # "anthropic" or "ollama"
EXTRACTION_MODEL    = "claude-sonnet-4-20250514"

SUMMARY_PROVIDER    = "anthropic"
SUMMARY_MODEL       = "claude-sonnet-4-20250514"

ANSWER_PROVIDER     = "anthropic"
ANSWER_MODEL        = "claude-sonnet-4-20250514"

EMBED_PROVIDER      = "ollama"             # "ollama" or "anthropic"
EMBED_MODEL         = "nomic-embed-text"
```

Pipeline settings:

```python
MAX_PAGES_PER_PDF   = None      # None = all pages
FORCE_RE_EXTRACT    = False     # True = ignore cached extractions
CHUNK_SIZE          = 800
CHUNK_OVERLAP       = 100
```

## Conventions

### Commit Messages

Use conventional prefix style:

| Prefix | Use For |
|--------|---------|
| `feat:` | New features or capabilities |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes only |
| `refactor:` | Code restructuring without behaviour change |
| `chore:` | Build, tooling, dependency updates |
| `test:` | Adding or updating tests |

### Code Style

- Type hints on all public functions
- Docstrings on public classes and non-trivial functions
- No hardcoded model names — all config in the Setup & Configuration cell

### Documentation

- Design docs and analysis in `docs/`
- Keep README.md up to date when adding notebooks or changing config
- Keep CLAUDE.md up to date when adding key files or changing conventions
- Architecture decisions recorded in `docs/architecture/decisions/`

### Critical Rules

- Never commit `.env` or API keys
- Never commit ChromaDB directories or `extractions.json`
- All model references must use the configurable provider/model variables
- Extraction results are cached — set `FORCE_RE_EXTRACT = True` to re-run
