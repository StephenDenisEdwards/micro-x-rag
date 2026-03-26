# GraphRAG Improvement Roadmap

This document outlines practical improvements to the GraphRAG pipeline, organized by priority. Each item explains what it is, why it matters, what to change, and the expected impact.

For a detailed explanation of how each step in the notebook works, see [graphrag-notebook-guide.md](../design/graphrag-notebook-guide.md).
For a comparison of GraphRAG vs Standard RAG results, see [graphrag-vs-standard-rag.md](../design/graphrag-vs-standard-rag.md).

---

## Current State

| Component | Current Choice | Role |
|-----------|---------------|------|
| Entity extraction | `claude-sonnet-4-20250514` (Anthropic API) | Extracts entities and relationships from each text chunk |
| Community summaries | `mistral:7b` (Ollama, local) | Generates thematic summaries of entity clusters |
| Embeddings | `nomic-embed-text` (Ollama, local) | Converts text to vectors for similarity search |
| Final answers | `claude-sonnet-4-20250514` (Anthropic API) | Generates answers from retrieved context |
| Vector store | ChromaDB | Stores and searches text vectors |
| Graph library | NetworkX | Builds graph, runs community detection |
| PDF extraction | PyMuPDF (`fitz`) | Extracts raw text from catalog PDFs |
| Chunking | Fixed-size (800 chars, 100 overlap) | Splits page text into processable pieces |

### Known Weaknesses

- Community summaries use the weakest model in the pipeline (`mistral:7b`)
- Only ~40 of 274 catalog pages were processed in the baseline run (14% coverage)
- Chunking doesn't respect document structure (tables, product sections)
- Entity deduplication uses string similarity only — misses semantic duplicates
- Graph contains singleton nodes (degree 0) that add noise but no value
- Communities are summarized at a single level of granularity

---

## Priority 1: Process All Pages

**What**: Set `MAX_PAGES_PER_PDF = None` in the notebook configuration and re-run extraction.

**Why**: This is the single highest-impact change. The baseline only processed ~40 of 274 pages (14%). Both Standard RAG and GraphRAG fail on questions about content in unprocessed pages. Low coverage also means:
- Missing products, specifications, and manufacturers
- Fewer cross-document connections (the main GraphRAG advantage)
- Community summaries that reflect only a fraction of the catalog

**How**: Change one line in Cell 3:
```python
MAX_PAGES_PER_PDF = None  # Already set — just ensure FORCE_RE_EXTRACT = True
FORCE_RE_EXTRACT = True
```

Then re-run all cells. Extraction will take longer (676 chunks instead of 92) and cost more in Claude API calls.

**Expected impact**:
| Metric | Before | Expected |
|--------|--------|----------|
| Pages processed | ~40 (14%) | 274 (100%) |
| Chunks | 92 | ~676 |
| Connected components | 206 | 30–60 |
| Average degree | 1.5 | 3–5 |
| Cross-catalog connections | Minimal | Significantly more |

**Effort**: Low — configuration change only.

---

## Priority 2: Upgrade the Community Summary Model

**What**: Replace `mistral:7b` with a better model for generating community summaries.

**Why**: Community summaries are the single biggest advantage GraphRAG has over Standard RAG. They enable answering broad, thematic questions like "What are the main product categories?" that no individual text chunk can answer. But the quality of those summaries depends entirely on the model generating them.

`mistral:7b` has these limitations for summarization:

| Issue | Impact |
|-------|--------|
| Shallow summaries that list entities without synthesizing themes | Summaries add less value to broad queries |
| Inconsistent detail level across communities | Some summaries are useful, others are near-empty |
| Misses cross-entity relationships within the community | Summaries don't capture the connections that make GraphRAG valuable |
| Slow inference (34% CPU / 66% GPU split on RTX 3050 Ti) | Long summarization times |

**Options**:

### Option A: Use Claude for summaries (recommended)

Use the same `claude-sonnet-4-20250514` already used for extraction and final answers. This gives the highest summary quality and there are typically only 10–30 communities to summarize, so the API cost is modest.

**How**: In Cell 21, change the `summarize_community()` function to use Claude instead of Ollama:
```python
# Replace:
response = ollama_client.chat.completions.create(
    model=OLLAMA_CHAT_MODEL, ...
)

# With:
response = extraction_client.messages.create(
    model=ANTHROPIC_MODEL,
    max_tokens=512,
    messages=[{"role": "user", "content": prompt}],
)
return response.content[0].text.strip()
```

### Option B: Switch to `qwen2.5:7b` (free, local)

Better instruction following and more coherent summaries than `mistral:7b`. Same VRAM requirements.

**How**: Change one line in Cell 3:
```python
OLLAMA_CHAT_MODEL = "qwen2.5:7b"
```
Then pull the model: `ollama pull qwen2.5:7b`

### Option C: Switch to `qwen2.5:3b` (fastest local option)

Fits fully in VRAM (100% GPU offload on RTX 3050 Ti). Faster inference but lower quality than 7B models.

### Option D: Larger local model

`qwen2.5:14b`, `llama3:8b`, or `mistral:13b` would all produce better summaries if VRAM allows. These may require partial CPU offload which slows inference.

**Effort**: Low — a few lines of code or a config change.

---

## Priority 3: Entity Resolution with Embeddings

**What**: Use the embedding model (`nomic-embed-text`) to find and merge semantically similar entity names, not just string-similar ones.

**Why**: The current deduplication (Cell 12) uses `SequenceMatcher` with a 0.92 threshold. This catches typos and pluralization differences:
- "Lift Mechanism Sets" → "Lift Mechanisms" ✓
- "All Metal Hinge, Nickel-Plated" → "All Metal Hinge, Nickel Plated" ✓

But it misses **semantic duplicates** — entities that mean the same thing but use different words:
- "Soft-Close Mechanism" vs "Gentle Closing Feature" ✗
- "Boring Pattern" vs "Drilling Pattern" ✗
- "Overlay" vs "Door Overlay" ✗

These duplicates create separate nodes in the graph that should be one node, splitting relationships and reducing connectivity.

**How**: After the current fuzzy matching step, add an embedding-based pass:
1. Embed all entity names using `nomic-embed-text`
2. Compute pairwise cosine similarity
3. Merge entities above a similarity threshold (e.g., 0.85)
4. Keep the name with the most mentions as canonical

**Expected impact**: Fewer disconnected components, higher average degree, more relationships discovered during graph traversal.

**Effort**: Medium — new code in the post-processing section (Cell 12).

---

## Priority 4: Section-Aware Chunking

**What**: Replace fixed-size chunking with chunking that respects the structure of catalog documents.

**Why**: The current approach splits text every ~800 characters, looking for sentence or paragraph breaks. But catalogs have natural structure — product sections, specification tables, feature lists. Fixed-size chunking can:
- Split a specification table across two chunks (losing context)
- Combine the end of one product section with the start of another (confusing extraction)
- Cut a product name from its specifications

**How**: Implement a chunking strategy that:
1. Detects section headers (product names, section titles) using font size or formatting cues from PyMuPDF
2. Keeps each product section as one chunk (or splits large sections at paragraph boundaries)
3. Keeps specification tables intact within a single chunk
4. Falls back to fixed-size chunking for unstructured text

**Expected impact**: Better entity extraction (fewer split entities), more complete relationships per chunk, cleaner community summaries.

**Effort**: Medium — requires new chunking logic and testing with the actual PDFs.

---

## Priority 5: Graph Pruning

**What**: Remove low-value nodes and edges from the knowledge graph before community detection and retrieval.

**Why**: The graph contains noise:
- **Singleton nodes** (degree 0) — entities with no connections. They add nothing to graph traversal and inflate community count.
- **Low-mention entities** (mentioned only once in a single chunk) — often extraction artifacts rather than meaningful entities.
- **Generic relationships** — edges with only a `has_feature` relationship to a vague entity add noise to graph traversal context.

**How**: Add a pruning step after graph building (Cell 15) and before community detection (Cell 17):
```python
# Remove singletons
singletons = [n for n, d in G.degree() if d == 0]
G.remove_nodes_from(singletons)

# Remove low-mention entities (optional, tune threshold)
low_mention = [n for n, data in G.nodes(data=True) if data.get("mentions", 0) < 2]
G.remove_nodes_from(low_mention)
```

**Expected impact**: Fewer, more meaningful communities. Less noise in graph traversal context. Faster community detection.

**Effort**: Low — a few lines of code.

---

## Priority 6: Hierarchical Community Summaries

**What**: Generate summaries at multiple levels of granularity instead of just one.

**Why**: Currently, all communities are summarized at the same level. But different questions need different levels of detail:
- "What are the main product categories?" → needs a **high-level** summary (catalog-wide)
- "What Nexis hinge options exist?" → needs a **mid-level** summary (product line)
- "What base plates work with Nexis 110°?" → needs a **detailed** summary (specific compatibility)

A single level of summarization can't serve all these query types well.

**How**:
1. Run community detection at multiple resolutions (the Louvain algorithm's `resolution` parameter controls granularity)
2. Generate summaries at each level:
   - **Level 1**: Fine-grained (many small communities — specific product groups)
   - **Level 2**: Medium (fewer, larger communities — product lines)
   - **Level 3**: Coarse (a few broad communities — major categories)
3. Store all levels in ChromaDB
4. At query time, retrieve summaries from the level that best matches the query scope

**Expected impact**: Better answers across all query types — broad questions get high-level summaries, specific questions get detailed ones.

**Effort**: Medium — requires multiple community detection runs, additional summarization, and modified retrieval logic.

---

## Priority 7: Better PDF Table Extraction

**What**: Use a table-aware PDF extraction tool instead of or alongside PyMuPDF's plain text extraction.

**Why**: Hardware catalogs contain **specification tables** — rows of product codes, dimensions, weights, and compatibility data. PyMuPDF's `get_text()` extracts these as raw text, which often loses the table structure:

```
# What the PDF shows:
| Model    | Angle | Boring | Close Type |
|----------|-------|--------|------------|
| TM9-110  | 110°  | 45mm   | Soft-Close |
| TM9-120  | 120°  | 45mm   | Self-Close |

# What PyMuPDF might extract:
Model Angle Boring Close Type TM9-110 110° 45mm Soft-Close TM9-120 120° 45mm Self-Close
```

Without structure, the LLM may not correctly associate "110°" with "TM9-110" during entity extraction.

**Options**:
- **`pdfplumber`** — good at extracting tables with row/column structure from PDFs
- **`camelot`** — specialized for table extraction, outputs DataFrames
- **Vision models** — use a multimodal LLM to read PDF pages as images, extracting table data with full visual context

**How**: Add a table detection step in the PDF extraction (Cell 5):
1. For each page, check if it contains tables (using `pdfplumber`)
2. If yes, extract the table as structured data (CSV or markdown format)
3. Include the structured table in the chunk so the extraction LLM sees clean tabular data

**Expected impact**: More accurate specifications extracted, better relationships between products and their specs, fewer extraction errors on tabular pages.

**Effort**: Medium — requires a new extraction pipeline and testing.

---

## Future Considerations

These are longer-term improvements worth exploring once the above priorities are addressed:

### Weighted Retrieval
Use edge weights (relationship frequency) and node mention counts to rank graph context by importance during retrieval. Currently all graph context is treated equally — a relationship seen 20 times has the same weight as one seen once.

### Better Embedding Model
The current `nomic-embed-text` is good for general text but not tuned for technical catalog vocabulary. Options:
- Use a larger model like `mxbai-embed-large` for better semantic representation
- Fine-tune an embedding model on catalog-specific vocabulary
- Create separate embeddings for different content types (product descriptions vs specifications vs compatibility data)

### Multi-Hop Retrieval
Currently graph traversal uses `hop_depth=1` (direct connections only). Increasing to 2 hops would find more distant relationships but risks including irrelevant context. An adaptive approach could use more hops for broad questions and fewer for specific ones.

### Incremental Updates
Currently, adding a new catalog means re-running the entire pipeline. An incremental approach would:
1. Extract entities from only the new catalog's chunks
2. Merge new entities into the existing graph (handling deduplication)
3. Re-run community detection on the updated graph
4. Re-generate only affected community summaries
5. Add new chunks and updated summaries to ChromaDB

---

## Summary

| Priority | Improvement | Impact | Effort | Changes To |
|----------|------------|--------|--------|-----------|
| 1 | Process all pages | High — 7x more content | Low | Config (Cell 3) |
| 2 | Upgrade community summary model | High — better broad query answers | Low | Cell 21 |
| 3 | Entity resolution with embeddings | Medium — fewer duplicates, more connections | Medium | Cell 12 |
| 4 | Section-aware chunking | Medium — cleaner extraction | Medium | Cell 5 |
| 5 | Graph pruning | Medium — less noise | Low | New cell between 15 and 17 |
| 6 | Hierarchical community summaries | Medium — better multi-scale answers | Medium | Cells 17, 21, 23, 25 |
| 7 | Better PDF table extraction | Medium — captures structured data | Medium | Cell 5 |
