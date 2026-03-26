# ADR-001: Configurable Provider and Model Per Operation

## Status

Accepted

## Context

The GraphRAG pipeline has four distinct operations that use AI models:

1. **Entity extraction** — reads text chunks and outputs structured JSON entities/relationships
2. **Community summaries** — generates natural language summaries of entity clusters
3. **Answer generation** — produces final answers from retrieved context
4. **Embeddings** — converts text to vectors for similarity search

Each operation has different quality requirements, cost sensitivities, and model compatibility needs. Initially, extraction and answers used Claude (hardcoded), summaries used mistral:7b via Ollama (hardcoded), and embeddings used nomic-embed-text via Ollama (hardcoded).

This made it impossible to experiment with different model combinations without editing code throughout the notebook.

## Decision

Each operation gets its own `PROVIDER` and `MODEL` configuration in the notebook's first code cell (Setup & Configuration):

```python
EXTRACTION_PROVIDER = "anthropic"
EXTRACTION_MODEL    = "claude-sonnet-4-20250514"

SUMMARY_PROVIDER    = "anthropic"
SUMMARY_MODEL       = "claude-sonnet-4-20250514"

ANSWER_PROVIDER     = "anthropic"
ANSWER_MODEL        = "claude-sonnet-4-20250514"

EMBED_PROVIDER      = "ollama"
EMBED_MODEL         = "nomic-embed-text"
```

A unified `llm_chat(prompt, provider, model)` function dispatches to the correct client. Embedding uses a separate class hierarchy (`OllamaEmbeddingFunction`, `AnthropicEmbeddingFunction`) because embedding APIs differ from chat APIs.

Supported providers: `"anthropic"` (Anthropic API) and `"ollama"` (local via OpenAI-compatible API).

## Rationale

- **Experimentation**: Can test different models for each operation without code changes
- **Cost control**: Use expensive cloud models only where quality matters (extraction), cheap local models for less critical operations
- **Simplicity**: All config in one cell, visible at the top of the notebook
- **Extensibility**: Adding a new provider (e.g., OpenAI, Gemini) means adding one branch to `llm_chat()` and one embedding class

## Consequences

- No global `ANTHROPIC_MODEL` or `OLLAMA_CHAT_MODEL` variables — each operation references its own pair
- `llm_chat()` must be defined before any operation cell that uses it
- Switching embedding providers requires re-indexing ChromaDB (different models produce different vector dimensions)
- The Anthropic embedding path requires the `voyageai` package and a `VOYAGE_API_KEY`
