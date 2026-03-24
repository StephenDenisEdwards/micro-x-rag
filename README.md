# micro-x-rag

A RAG (Retrieval-Augmented Generation) system that indexes hardware product catalogs into a ChromaDB vector database and answers natural language queries using both local Ollama models and Anthropic Claude.

## Overview

This project demonstrates a complete RAG pipeline:

1. **Extract** — Pull text from PDF catalogs (Wurth Baer, Grass hinges & drawer slides) using PyMuPDF
2. **Chunk** — Split pages into overlapping segments with sentence-boundary awareness
3. **Embed** — Generate vector embeddings locally with Ollama `nomic-embed-text`
4. **Store** — Persist embeddings and metadata in a ChromaDB vector database
5. **Retrieve** — Semantic search to find the most relevant catalog sections for a query
6. **Generate** — Synthesize answers with source citations using Ollama or Claude

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

The notebook loads environment variables (including `ANTHROPIC_API_KEY`) from the sibling project `micro-x-agent-loop-python/.env`. Update the path in the notebook's first cell if your layout differs.

## Project Structure

```
micro-x-rag/
├── catalogs/                  # PDF product catalogs (source documents)
├── chroma_db/                 # ChromaDB persistent storage (created on first run)
├── notebooks/
│   └── rag_catalog_search.ipynb   # Main RAG notebook
├── requirements.txt
└── README.md
```

## Usage

Open the notebook and run cells in order:

```bash
jupyter notebook notebooks/rag_catalog_search.ipynb
```

**First run** — all cells execute end-to-end: PDF extraction, chunking, embedding, ingestion, and querying. This takes a few minutes depending on hardware.

**Subsequent runs** — skip to the query cells. The ChromaDB store persists to disk. Section 10 of the notebook has a reload snippet to reconnect to the existing collection without re-ingesting.

## Catalogs Included

| File | Description |
|------|-------------|
| `Wurth_Baer_Section_C.pdf` | Wurth Baer Section C |
| `wurth-baer-section-b-concealed-hinges.pdf` | Wurth Baer concealed hinges |
| `grass-tiomos-catalog.pdf` | Grass Tiomos hinge system |
| `grass-nexis-catalog.pdf` | Grass Nexis drawer system |

## Configuration

Key settings in the notebook's first cell:

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model |
| `OLLAMA_CHAT_MODEL` | `mistral:7b` | Local generation model |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Claude model for generation |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
