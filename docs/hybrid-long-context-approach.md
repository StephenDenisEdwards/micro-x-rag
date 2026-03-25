# Hybrid Approach: Long Context with Structured Data Layers

## The Idea

Instead of choosing between GraphRAG (retrieval-based) and long context (send everything), combine them. Give the LLM the full catalog text **plus** pre-computed structured data — knowledge graph relationships and deterministic compatibility matrices — in a single long-context prompt.

The structured data acts as an index layered on top of the raw text. The LLM doesn't have to infer relationships from 274 pages of prose — the graph and compatibility matrices tell it directly, and the catalog text provides the detail and nuance to back up the answers.

## Three Layers of Context

### Layer 1: Raw Catalog Text

The original PDF content — product descriptions, specification tables, marketing language, installation instructions. This is where the detail lives: exact dimensions, torque values, ordering codes, compatibility notes buried in footnotes.

**Strengths**: Complete information, nuance, human-readable detail.
**Weaknesses**: Relationships between products are implicit and scattered across pages. An LLM processing 200K+ tokens may overlook a compatibility fact on page 137.

### Layer 2: Knowledge Graph Data

Pre-extracted entities and relationships in structured form:

```
ENTITIES:
- Nexis 110° Snap-on Hinge (product, 12 mentions, sources: grass-nexis-catalog.pdf)
- Grass (manufacturer, 24 mentions)
- Soft-Close (feature, 18 mentions)
- Nexis Cam Base Plate H0 (product, 6 mentions)

RELATIONSHIPS:
- Nexis 110° Snap-on Hinge --[manufactured_by]--> Grass
- Nexis 110° Snap-on Hinge --[has_feature]--> Soft-Close
- Nexis 110° Snap-on Hinge --[compatible_with]--> Nexis Cam Base Plate H0
```

**Strengths**: Makes implicit relationships explicit. The LLM doesn't need to figure out that Hinge X and Base Plate Y are compatible by reading two separate pages — the relationship is stated directly.
**Weaknesses**: Only as complete as the extraction. LLM-extracted relationships can be wrong or missing.

### Layer 3: Deterministic Compatibility Matrices

Ground truth compatibility data from a verified source, presented as compact tables:

```
COMPATIBILITY MATRIX — Hinges to Doors:
| Hinge                        | Door Type              | Overlay | Boring | Base Plate Required     |
|------------------------------|------------------------|---------|--------|-------------------------|
| Nexis 110° Snap-on           | 3/4" Frameless         | Full    | 45mm   | Nexis Cam Base Plate H0 |
| Nexis 110° Snap-on           | 3/4" Frameless         | Half    | 45mm   | Nexis Cam Base Plate H2 |
| Nexis 110° Snap-on           | 3/4" Face Frame        | Full    | 45mm   | Nexis FFA Base Plate    |
| Tiomos M9 110°               | 3/4" Frameless         | Full    | 45mm   | Tiomos Linear Plate     |
| Tiomos M9 110°               | 5/8" Frameless         | Full    | 45mm   | Tiomos Linear Plate     |
...
```

**Strengths**: Verified facts. Compact — hundreds of compatibility pairs fit in a few thousand tokens. No ambiguity.
**Weaknesses**: Only covers products in the compatibility database. Doesn't include descriptions, features, or installation instructions.

## Why the Combination Works

Each layer compensates for the others' weaknesses:

| Question Type | Which Layer Answers It |
|--------------|----------------------|
| "What base plate do I need for a Nexis 110° on a 3/4 inch frameless door?" | **Layer 3** (compatibility matrix) — exact answer, verified |
| "What are the main product categories and how do they relate?" | **Layer 2** (graph) — pre-computed entity clusters and relationships |
| "How do I adjust the soft-close damping force on a Tiomos M9?" | **Layer 1** (catalog text) — detailed installation instructions |
| "Compare all hinge options for face frame cabinets" | **All three** — matrix for compatibility, graph for relationships, text for detailed specs |

The graph data and compatibility matrices are particularly effective because they're **compact**. A compatibility matrix covering 500 product pairings might be 10K tokens. The equivalent information scattered across catalog pages could be 50K+ tokens of prose. Structured data gives the LLM the same facts at a fraction of the token cost, leaving more room for the raw text that provides detail and nuance.

## How the Prompt Would Be Structured

```
You are a hardware product specialist. Answer the user's question using ALL
three sources below. When compatibility information comes from the VERIFIED
COMPATIBILITY MATRIX, state that it is verified. When citing product details,
reference the catalog source and page number.

=== VERIFIED COMPATIBILITY MATRIX ===
[Deterministic compatibility tables — compact, high-trust]

=== KNOWLEDGE GRAPH (entity relationships) ===
[Pre-extracted entities and relationships — structured, medium-trust]

=== CATALOG TEXT ===
[Full or relevant catalog pages — detailed, provides nuance and citations]

USER QUESTION: {query}
```

The ordering matters. Compatibility matrices go first because they're the most reliable and compact. Graph data goes next as structured context. Catalog text goes last as the detailed reference. This structure helps the LLM prioritize verified facts while having full detail available for elaboration.

## Comparison of Approaches

| Aspect | Standard RAG | GraphRAG (retrieval) | Long Context Only | Hybrid (this approach) |
|--------|-------------|---------------------|-------------------|----------------------|
| **Context seen by LLM** | 5 chunks (~4K tokens) | 5 chunks + graph + summaries (~6K tokens) | All catalogs (~200K tokens) | All catalogs + graph + matrices (~220K tokens) |
| **Cost per query** | Low | Low | High | Highest |
| **Latency** | Fast | Fast | Slow | Slowest |
| **Relationship awareness** | None — must infer from chunks | Pre-computed graph edges | Must infer from full text | Pre-computed graph + verified matrices |
| **"Lost in the middle" risk** | N/A (small context) | N/A (small context) | High — LLM may miss facts on page 137 | Mitigated — structured data surfaces key facts upfront |
| **Compatibility accuracy** | Low — may miss or hallucinate | Medium — LLM-extracted edges | Medium — must infer from text | High — verified matrices + graph + text |
| **Scalability** | Good — fixed retrieval size | Good — fixed retrieval size | Limited by context window | Limited by context window |
| **Best for** | Simple fact lookups | Broad/thematic questions | One-off deep analysis | High-stakes decisions requiring verified answers |

## When to Use Each Approach

**Standard RAG**: High-volume, low-stakes queries where cost and speed matter. "What's the opening angle of the Tiomos M9?"

**GraphRAG (retrieval-based)**: The general-purpose production path. Good balance of cost, speed, and answer quality. Handles broad and multi-hop questions well. Best when query volume is high.

**Long Context Only**: One-off analysis or evaluation. "Read all four catalogs and tell me which products overlap." Useful for validating whether retrieval-based approaches are missing information.

**Hybrid (long context + structured data)**: High-stakes queries where accuracy matters and cost is acceptable. Professional specifiers choosing hardware for a project. Quality assurance verification. Situations where "the Nexis 110° appears to be compatible" isn't good enough and you need "the Nexis 110° is verified compatible."

## Implementation Notes

### Token Budget

With current model context windows (200K+ tokens for Claude):

| Content | Estimated Tokens |
|---------|-----------------|
| 4 PDF catalogs (~274 pages) | ~150K–180K |
| Knowledge graph (600 entities, 460 relationships) | ~5K–8K |
| Compatibility matrices (500 pairings) | ~8K–12K |
| System prompt + query | ~1K |
| **Total** | ~170K–200K |

This fits within Claude's context window, but leaves limited room for the response. For larger catalog sets, you may need to:
- Send only the most relevant catalog sections (using retrieval to select pages)
- Summarize less relevant catalogs while sending key catalogs in full
- Use community summaries in place of full graph data for less relevant clusters

### Selective Hybrid

A practical middle ground: use **retrieval** to select the most relevant catalog pages (say, 20–30 pages instead of 274), then combine those with the **full** graph data and **full** compatibility matrices. This gives you:
- Relevant catalog detail (not everything, but the right pages)
- Complete structured relationships (the full graph is small enough to always include)
- Complete compatibility data (matrices are compact)
- Reasonable token cost (30K–50K instead of 200K)

This selective approach gets most of the hybrid benefit at a fraction of the cost.

### Caching

The graph data and compatibility matrices are the same for every query (they only change when products change). They can be pre-formatted and cached as a prompt prefix, with only the query and retrieved catalog pages changing per request.
