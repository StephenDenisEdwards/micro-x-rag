# GraphRAG Knowledge Graph Analysis

## Overview

This document analyzes the quality of the knowledge graph built by the GraphRAG notebook (`notebooks/graph_rag_catalog_search.ipynb`) and tracks improvements made to the extraction and post-processing pipeline.

---

## Baseline (Before Improvements)

Extracted from 92 chunks (10 pages per PDF, 4 PDFs).

| Metric | Value |
|--------|-------|
| Nodes (entities) | 665 |
| Edges (relationships) | 498 |
| Connected components | 243 |
| Communities | 249 |
| Average degree | 1.5 |
| Density | 0.0023 |
| Chunks indexed | 288 |
| Community summaries | 10 |
| Extraction time | ~8171s (~2.3 hours) |
| Pages processed | ~40 of ~276 total (10 per PDF) |
| Entity types | 57 |
| Relationship types | 50+ |
| Unknown-type entities | 158 (25%) |

### Models

- Extraction: `claude-sonnet-4-20250514` via Anthropic API
- Community summaries: `mistral:7b` via Ollama (34% CPU / 66% GPU on RTX 3050 Ti, 3.8 GiB VRAM)
- Embeddings: `nomic-embed-text` via Ollama
- Final answers: Claude Sonnet + Ollama

### Source PDFs

| Catalog | Pages |
|---------|-------|
| grass-nexis-catalog.pdf | 51 |
| grass-tiomos-catalog.pdf | 63 |
| wurth-baer-section-b-concealed-hinges.pdf | 104 |
| Wurth_Baer_Section_C.pdf | 56 |
| **Total** | **274** |

---

## Baseline Quality Issues

### 1. Extreme Fragmentation

243 connected components for 665 nodes means most entities are isolated islands. The graph traversal step in GraphRAG adds limited value since most entities can't be reached from each other. A well-connected graph would have 1-10 components.

### 2. Low Connectivity

Average degree of 1.5 and density of 0.0023 means entities have almost no connections. Most nodes have 0 or 1 edge. For graph-based retrieval to add value over vector search alone, entities need meaningful interconnections.

### 3. Entity Type Explosion

57 different entity types when there should be ~7-10. 158 entities (25%) classified as "unknown".

Duplicate concepts that all mean the same thing:
- `product`, `product_variant`, `product_code`, `product_id`, `product_series`, `product_line`, `product_model`
- `specification`, `product_specification`
- `feature`, `product_feature`

| Type | Count |
|------|-------|
| product | 238 |
| unknown | 158 |
| specification | 37 |
| feature | 33 |
| product_variant | 17 |
| dimension | 16 |
| property | 11 |
| weight | 10 |
| product_code | 10 |
| (47 more types) | <8 each |

### 4. Relationship Type Explosion

50+ relationship types when the extraction prompt only allowed 6. The model ignored the schema constraints entirely.

| Relationship | Count | In Schema? |
|-------------|-------|------------|
| has_feature | 152 | Yes |
| has_specification | 86 | Yes |
| part_of | 48 | Yes |
| compatible_with | 40 | Yes |
| manufactured_by | 35 | Yes |
| includes | 12 | No |
| has_dimension | 10 | No |
| pages | 10 | No |
| (44 more types) | <10 each | No |

### 5. Extraction Quality (mistral:7b limitations)

- **JSON truncation**: Model runs out of tokens before completing JSON objects, causing parse errors on ~3% of chunks
- **Inconsistent entity naming**: Same product appears under different names (e.g., "Tiomos" vs "TIOMOS" vs "Grass Tiomos")
- **Schema non-compliance**: Model frequently invents entity types and relationship types outside the allowed set
- **Slow inference**: 34% CPU / 66% GPU split due to model exceeding VRAM

### 6. Low Page Coverage

Only 10 pages per PDF were processed. With 4 PDFs totaling ~274 pages, only ~14% of content was extracted. This directly causes:
- Missing products and specifications
- Fewer cross-document connections
- Both RAG approaches failing on questions about content in unprocessed pages

---

## GraphRAG vs Standard RAG Comparison

Based on test queries run against both approaches:

| Query Type | Standard RAG | GraphRAG | Winner |
|-----------|-------------|----------|--------|
| Broad thematic ("product categories") | Partial, limited to retrieved chunks | Better, community summaries add breadth | GraphRAG |
| Cross-catalog comparison ("Grass vs Wurth Baer") | Failed (couldn't find Wurth Baer info) | Failed (same limitation) | Tie |
| Specific factual ("mounting plates for soft-close") | Partial answer | Slightly more context from graph traversal | Slight GraphRAG |
| Specific factual ("Tiomos max opening angle") | Failed | Failed | Tie |

**Key finding**: Community summaries are the most valuable GraphRAG addition. Graph traversal adds limited value due to fragmentation. For specific factual queries, neither approach significantly outperforms the other when page coverage is low.

---

## Improvements Applied

### Post-Processing Pipeline (Section 4a in notebook)

1. **Entity type normalization**: Maps 57 raw types to 7 canonical types using a lookup dictionary:
   - `product`, `manufacturer`, `feature`, `specification`, `material`, `certification`, `category`
   - Unmapped types default to `feature`
   - 15 unmapped types found in baseline data: `compatible_with`, `contact_info`, `contact_information`, `has_feature`, `label`, `mounting_method`, `number_of_items`, `occupation`, `packaging`, `relationship`, `safety_feature`, `sub_category`, `use_case`, `user`, `website`

2. **Relationship type normalization**: Maps 50+ raw types to 6 canonical types:
   - `has_feature`, `has_specification`, `part_of`, `compatible_with`, `manufactured_by`, `variant_of`
   - Unmapped types default to `has_feature`

3. **Entity deduplication**: Fuzzy matching (SequenceMatcher, threshold 0.92) to merge near-duplicate entity names. Keeps the variant with the most mentions as canonical. 36 entity variants merged in baseline data, examples:
   - `'Lift Mechanism Sets'` -> `'Lift Mechanisms'`
   - `'Arm Assembly Mounting Plate'` -> `'Arm Assembly Mounting Plates'`
   - `'All Metal Hinge, Nickel-Plated'` -> `'All Metal Hinge, Nickel Plated'`

4. **Noise filtering**: Removes entities that are pure numbers, <3 characters, or generic stop words (N/A, Unknown, Page, etc.). Removed 137 entities and 91 relationships from baseline data.

### Extraction Improvements

5. **Stricter prompt**: Closed enum for entity/relationship types with explicit "use ONLY these" instruction. Few-shot example included. Shorter, more constrained.

6. **JSON repair**: Attempts to fix truncated JSON by balancing brackets/braces and removing incomplete trailing objects.

7. **max_tokens=1024**: Explicit token limit to reduce truncation.

8. **Checkpointing**: Saves progress every 50 chunks during extraction so interrupted runs can resume.

### Graph Building Improvements

9. **Type majority voting**: When the same entity appears with different types across chunks, the most frequent type wins.

10. **MAX_PAGES_PER_PDF = None**: Process all pages for complete catalog coverage (274 pages, 676 chunks).

11. **Better default type**: Nodes created implicitly from relationship endpoints default to `product` instead of `unknown`.

---

## After Improvements (with cached 92-chunk extractions)

Post-processing applied to the same 92-chunk extraction data:

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Nodes | 665 | 604 | -9% |
| Edges | 498 | 466 | -6% |
| Connected components | 243 | 206 | -15% |
| Communities | 249 | 213 | -14% |
| Entity types | 57 | 8 | -86% |
| Relationship types | 50+ | 6 | -88% |
| Unknown-type entities | 158 (25%) | 0 | -100% |
| Chunks indexed | 288 | 676 | +135% |
| Density | 0.0023 | 0.0026 | +13% |

### Entity Type Distribution (After)

| Type | Count |
|------|-------|
| product | 278 |
| feature | 80 |
| specification | 73 |
| category | 21 |
| manufacturer | 7 |
| material | 2 |
| certification | 1 |

### Relationship Type Distribution (After)

| Type | Count |
|------|-------|
| has_feature | 222 |
| has_specification | 107 |
| compatible_with | 53 |
| part_of | 53 |
| manufactured_by | 25 |
| variant_of | 6 |

---

## Pending: Full Re-Extraction

The improvements above were applied to the cached 92-chunk extraction (10 pages per PDF). The full improvement requires re-running extraction on all 676 chunks (all pages):

1. Set `FORCE_RE_EXTRACT = True` in the notebook config cell
2. Run all cells — extraction will take ~20-30 minutes
3. The stricter prompt + JSON repair + full page coverage should produce significantly better results

### Expected Impact of Full Re-Extraction

| Metric | Current (92 chunks) | Expected (676 chunks) |
|--------|---------------------|----------------------|
| Connected components | 206 | 30-60 |
| Average degree | 1.5 | 3-5 |
| Pages processed | ~40 (14%) | 274 (100%) |
| Cross-catalog connections | Minimal | Significantly more |
| GraphRAG vs Standard RAG gap | Small | Larger |

---

## Further Improvements to Consider

1. **Use qwen2.5:7b for extraction** — better JSON compliance and instruction following than mistral:7b, similar VRAM requirements
2. **Use qwen2.5:3b for extraction** — fits fully in VRAM (100% GPU), faster inference, trades some quality for speed
3. **Entity resolution with embeddings** — use nomic-embed-text to compute similarity between entity names for smarter deduplication
4. **Graph pruning** — remove singleton nodes (degree 0) and very low-confidence edges
5. **Hierarchical community summaries** — summarize at multiple levels for different query granularities
6. **Weighted retrieval** — use edge weights and node mention counts to rank graph context
