# GraphRAG vs Standard RAG: Why Graph-Enhanced Retrieval Produces Better Results

## How Standard RAG Works

Standard RAG (Retrieval-Augmented Generation) follows a straightforward pipeline:

1. **Chunk** documents into fixed-size text segments (e.g., 800 characters)
2. **Embed** each chunk into a vector using an embedding model (e.g., `nomic-embed-text`)
3. **Store** vectors in a database (ChromaDB)
4. **Query** by embedding the user's question, finding the top-k most similar chunks
5. **Generate** an answer using an LLM with the retrieved chunks as context

The LLM only sees the handful of chunks that happened to be closest in vector space to the query. It has no awareness of how information connects across chunks or documents.

## How GraphRAG Works

GraphRAG adds a knowledge graph layer on top of standard vector retrieval:

1. **Extract entities and relationships** from each chunk using an LLM (e.g., products, manufacturers, features, and the connections between them)
2. **Build a knowledge graph** where entities are nodes and relationships are edges
3. **Detect communities** in the graph using the Leiden algorithm — groups of densely connected entities
4. **Summarize communities** using an LLM to create thematic overviews
5. **Retrieve via three sources** at query time:
   - **Vector search** (same as standard RAG) — finds relevant text chunks
   - **Graph traversal** — follows entity relationships to find connected context
   - **Community summaries** — provides broad thematic context
6. **Generate** an answer using an LLM with all three context sources

## Why GraphRAG Produces Better Results

### 1. Community Summaries Unlock "Forest-Level" Understanding

This is the single biggest advantage. Standard RAG can only answer questions using information that exists within individual chunks. When a user asks a broad question like *"What are the main product categories across all catalogs?"*, standard RAG returns whichever 5 chunks happen to be closest in vector space — typically fragments from one or two pages.

GraphRAG's community summaries are pre-computed overviews of entity clusters. A community might group all concealed hinge products with their manufacturers, compatible mounting plates, and shared features. This summary exists as a single retrievable unit that captures cross-document themes no individual chunk contains.

**In our testing**, the "product categories" query produced:
- **Standard RAG**: A fragmented list of items from individual pages, with no coherent organization
- **GraphRAG**: A structured taxonomy with 5 clear categories and explanations of how they interrelate (functional integration, brand specialization, specification compatibility)

### 2. Graph Traversal Connects Information Across Documents

Standard RAG treats each chunk as an independent unit. If information about a product's compatibility is split across two different catalog pages (or two different catalogs), standard RAG may retrieve one page but miss the other.

GraphRAG's entity relationships create explicit bridges between chunks. When the system finds an entity like "Nexis Snap-on hinges" in one chunk, graph traversal follows the relationship edges to find connected entities like "Nexis base plates", "cam base plates", and "soft-close adapters" — even if those appear in completely different documents.

**In our testing**, the mounting plate compatibility query produced:
- **Standard RAG**: Found a few relevant chunks but reported it "cannot find specific information" about mounting plate compatibility
- **GraphRAG**: Traversed relationships to list cam, linear, wing, FFA/FFAL base plates and surfaced the compatibility check requirement — information spread across multiple catalog sections

### 3. Entity Relationships Provide Structured Context

When GraphRAG retrieves graph context, it provides the LLM with structured facts like:

```
Tiomos M9 110° Hinge --[manufactured_by]--> Grass
Tiomos M9 110° Hinge --[has_feature]--> Soft-Close
Tiomos M9 110° Hinge --[compatible_with]--> System 9000 Base Plate
```

This structured context helps the LLM organize its answer logically rather than synthesizing from unstructured text fragments. The result is answers with clearer categorization and more explicit relationships between concepts.

### 4. Where Standard RAG Still Matches

For **specific fact lookups** where the answer lives within a single chunk (e.g., "What is the opening angle of the Tiomos M9?"), standard RAG performs equally well. The vector search finds the relevant chunk directly and the LLM extracts the answer. The graph layer adds no significant value here because no cross-referencing is needed.

Both approaches also show equal **hallucination resistance** — when information isn't in the indexed data, both refuse to guess rather than fabricating answers.

## Test Results Summary

| Query Type | Standard RAG | GraphRAG | Why |
|-----------|-------------|----------|-----|
| Broad thematic ("product categories") | Fragmented, chunk-limited | Structured, cross-catalog | Community summaries provide thematic overview |
| Cross-document ("mounting plate compatibility") | Partial, misses connections | More complete, links related entities | Graph traversal bridges information across sections |
| Cross-brand comparison ("Grass vs Wurth Baer") | Failed — only found one brand | Failed — same limitation | Both limited by incomplete page coverage |
| Specific fact ("Tiomos max opening angle") | Failed | Partial (found 110° but couldn't confirm max) | Both limited by page coverage; graph found slightly more |

## Current Setup

| Component | Model / Tool | Role |
|-----------|-------------|------|
| Entity extraction | `claude-sonnet-4-20250514` via Anthropic API | Extracts entities and relationships from chunks |
| Community summaries | `mistral:7b` via Ollama | Generates thematic summaries of entity clusters |
| Embeddings | `nomic-embed-text` via Ollama | Vector embeddings for chunks and queries |
| Final answer generation | `claude-sonnet-4-20250514` via Anthropic API | Generates answers from retrieved context |
| Vector store | ChromaDB | Stores and retrieves chunk embeddings |
| Graph analysis | NetworkX + Leiden algorithm | Builds graph, detects communities |

---

## Options to Improve GraphRAG Results

### A. Improve the Community Summary Model

Entity extraction already uses `claude-sonnet-4-20250514` via the Anthropic API, which provides strong JSON compliance, schema adherence, and consistent entity naming. However, **community summaries** currently use `mistral:7b` via Ollama, which is the weakest link in the pipeline. Since community summaries are the single biggest advantage GraphRAG has over standard RAG, improving this model has outsized impact.

Known `mistral:7b` limitations for summarization:

| Issue | Impact |
|-------|--------|
| Shallow summaries that list entities without synthesizing themes | Community summaries add less value to broad queries |
| Inconsistent detail level across communities | Some summaries are useful, others are near-empty |
| Misses cross-entity relationships within the community | Summaries don't capture the connections that make GraphRAG valuable |
| Slow inference (34% CPU / 66% GPU split on RTX 3050 Ti) | Long summarization times |

**Option 1: `qwen2.5:7b`** (drop-in replacement)
- Better instruction following and more coherent summaries
- Similar VRAM requirements to `mistral:7b`
- No code changes needed — just change `OLLAMA_CHAT_MODEL`

**Option 2: `qwen2.5:3b`** (speed-focused)
- Fits fully in VRAM (100% GPU offload on RTX 3050 Ti)
- Faster inference, trades some summary quality for speed
- Good for rapid iteration

**Option 3: Claude via API for summaries** (quality-focused)
- Use `claude-sonnet-4-20250514` for community summaries (same as extraction)
- Best summary quality — will produce thematic, well-structured overviews
- Trade-off: API cost (modest — typically only 10-30 communities to summarize)
- Highest expected impact since community summaries are GraphRAG's key differentiator

**Option 4: Larger local model** (if hardware allows)
- `mistral:13b`, `qwen2.5:14b`, or `llama3:8b` would all produce better summaries
- Requires more VRAM or slower CPU offload
- Good middle ground between local speed and API quality

### B. Improve Data Quality

**1. Process all pages** (`MAX_PAGES_PER_PDF = None`)

Currently only ~40 of 274 pages are processed (14% coverage). This is the single highest-impact improvement available. Both RAG approaches fail on queries about content in unprocessed pages, and low coverage directly causes:
- Missing products and specifications
- Fewer cross-document connections (the main GraphRAG advantage)
- Community summaries that reflect only a fraction of the catalog

**2. Better PDF extraction**

The quality of text extracted from PDFs directly affects everything downstream. Options:
- Use a PDF extraction tool that preserves table structure (e.g., `pdfplumber` or `camelot` for tabular catalog data)
- Pre-process PDFs to separate body text from headers/footers/page numbers
- Extract images and diagrams separately using vision models

**3. Smarter chunking**

The current approach uses fixed-size chunks (800 chars with 100-char overlap). For catalog data with natural structure (product sections, specification tables), consider:
- Section-aware chunking that respects product boundaries
- Table-aware chunking that keeps specification tables intact
- Overlapping entity windows — chunk with enough overlap that entity relationships spanning chunk boundaries are captured in at least one chunk

### C. Improve Graph Quality

**1. Entity resolution with embeddings**

Current deduplication uses string similarity (SequenceMatcher, threshold 0.92). This misses semantic duplicates like "soft-close mechanism" and "soft close feature". Using `nomic-embed-text` to compute embedding similarity between entity names would catch these.

**2. Graph pruning**

Remove noise:
- Singleton nodes (degree 0) that add nothing to graph traversal
- Very low-confidence edges (entities connected by weak or generic relationships)
- Entities below a minimum mention count threshold

**3. Hierarchical community summaries**

Currently communities are summarized at one level. Summarizing at multiple granularities (e.g., product line level, category level, full catalog level) would let the system match the right summary to the query scope.

**4. Weighted retrieval**

Use edge weights (relationship frequency) and node mention counts to rank graph context by importance, so the most relevant entities and relationships are prioritized in the LLM prompt.

### D. Improve the Embedding Model

The current `nomic-embed-text` model is good for general text but not specifically tuned for technical catalog content. Options:
- Fine-tune an embedding model on catalog-specific vocabulary
- Use a larger embedding model like `mxbai-embed-large` for better semantic representation
- Create separate embeddings for different content types (product descriptions vs specifications vs compatibility info)

---

## Recommended Improvement Priority

| Priority | Improvement | Impact | Effort |
|----------|------------|--------|--------|
| 1 | Process all pages (`MAX_PAGES_PER_PDF = None`) | High — 7x more content | Low — config change |
| 2 | Upgrade community summary model (Claude API or `qwen2.5:7b`) | High — summaries are GraphRAG's key advantage | Low — config change or small code change |
| 3 | Entity resolution with embeddings | Medium — fewer duplicate nodes | Medium — new code |
| 4 | Section-aware chunking | Medium — better entity extraction | Medium — new chunking logic |
| 5 | Graph pruning (remove singletons) | Medium — less noise in retrieval | Low — few lines of code |
| 6 | Hierarchical community summaries | Medium — better broad query answers | Medium — new summarization pass |
| 7 | Better PDF table extraction | Medium — captures structured data | Medium — new extraction pipeline |
