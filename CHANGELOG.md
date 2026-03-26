# Changelog

## 2026-03-26

### Added
- Configurable provider and model per operation (extraction, summaries, answers, embeddings)
- `llm_chat()` dispatcher function replacing hardcoded client calls
- Anthropic embedding support via Voyage AI SDK
- Documentation: GraphRAG notebook guide, comparison analysis, improvement roadmap
- Documentation: deterministic compatibility service integration design
- Documentation: hybrid long-context approach design
- Executed notebook with Claude-generated community summaries for comparison
- CLAUDE.md, CONTRIBUTING.md, CHANGELOG.md, .env.example

### Changed
- Community summaries upgraded from `mistral:7b` to `claude-sonnet-4-20250514`
- Notebook Setup & Configuration cell restructured — config only, no imports
- README.md updated to reflect configurable model architecture

### Fixed
- Corrected model attribution in docs (extraction uses Claude, not mistral:7b)

## 2026-03-25

### Added
- GraphRAG notebook with knowledge graph-enhanced retrieval
- Entity extraction using Claude API with strict schema enforcement
- Post-processing pipeline: type normalization, fuzzy deduplication, noise filtering
- Community detection via Louvain algorithm
- Interactive knowledge graph visualization with pyvis
- Standard RAG vs GraphRAG comparison queries
- Extraction safety guards and standalone extraction script
- Graph quality analysis documentation

### Fixed
- Notebook cell escaping issues and improved error messages
- Restored missing graph building cell in notebook

## 2026-03-24

### Added
- Initial standard RAG notebook (`rag_catalog_search.ipynb`)
- PDF extraction and chunking pipeline
- ChromaDB vector store with Ollama embeddings
- Query generation with both Ollama and Claude
- Four hardware catalog PDFs (Grass Nexis, Grass Tiomos, Wurth Baer Sections B & C)
