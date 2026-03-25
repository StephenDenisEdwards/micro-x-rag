# Integrating a Deterministic Compatibility Service with GraphRAG

## The Problem

The current GraphRAG pipeline relies entirely on LLM extraction to discover relationships between products. When Claude reads a catalog chunk and encounters text like "the Nexis Snap-on hinge attaches to Nexis base plates", it extracts a `compatible_with` relationship. But this approach has limitations:

- **It only finds relationships stated in the text.** If a hinge is compatible with a bracket but that fact appears on a different page (or in a different catalog, or in a separate compatibility chart), the LLM may never see both entities in the same chunk.
- **It misses implicit compatibility.** A catalog might list product codes in a table without explicitly saying "X is compatible with Y" — the reader is expected to understand from context.
- **It's probabilistic.** The LLM might extract a relationship incorrectly, miss one entirely, or name entities inconsistently across chunks.
- **Graph fragmentation.** The knowledge graph currently has 206 connected components — many product entities exist as isolated islands with no connections, precisely because the text-based extraction missed the relationships that link them.

## The Opportunity

A deterministic compatibility service — a database, rules engine, or API that knows exactly which hinges, brackets, mounting plates, and accessories work with which cabinet doors — would provide **ground truth** relationships. These are facts, not inferences. They don't depend on whether the right chunk was processed or whether the LLM interpreted the text correctly.

## How It Would Integrate

### Architecture

```
                    ┌─────────────────────────┐
                    │   PDF Catalogs           │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   LLM Extraction         │
                    │   (entities + inferred   │
                    │    relationships)         │
                    └────────────┬────────────┘
                                 │
                                 ▼
┌──────────────────┐   ┌─────────────────────────┐
│  Compatibility   │──▶│   Knowledge Graph        │
│  Service         │   │   (LLM edges + verified  │
│  (deterministic) │   │    compatibility edges)   │
└──────────────────┘   └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │   Community Detection    │
                       │   + Summaries            │
                       └────────────┬────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │   GraphRAG Retrieval     │
                       │   + Answer Generation    │
                       └─────────────────────────┘
```

The compatibility service feeds into the knowledge graph **after** LLM extraction and post-processing, but **before** community detection. This means communities form around real product compatibility clusters, not just textual co-occurrence.

### What the Service Needs to Provide

At minimum, structured compatibility pairs:

```json
{
  "source": "Nexis 110° Snap-on Hinge",
  "target": "3/4 inch Frameless Cabinet Door",
  "relationship": "compatible_with",
  "conditions": {
    "door_thickness_mm": [16, 19],
    "overlay": "full",
    "boring_pattern_mm": 45
  },
  "bracket": "Nexis Cam Base Plate H0",
  "confidence": 1.0
}
```

The key fields are `source`, `target`, and `relationship`. The `conditions` and `bracket` fields are optional but valuable — they provide context that makes the graph richer and answers more precise.

### Where It Fits in the Notebook Pipeline

The integration point is between the current Step 4a (post-processing) and Step 5 (build knowledge graph). A new step would:

1. **Query the compatibility service** for all known compatibility relationships
2. **Map service entity names to graph entity names** — the service may use product codes ("71B3580") while the graph uses names extracted from catalog text ("Nexis 110° Snap-on Hinge"). This mapping could be a lookup table, fuzzy matching, or part of the service's API.
3. **Add verified edges to the graph** with a distinct relationship type (`verified_compatible_with`) and a flag indicating the source is deterministic
4. **Create new nodes** for any entities in the service data that don't yet exist in the graph

### Edge Types: LLM-Extracted vs Deterministic

| Property | LLM-Extracted Edge | Deterministic Edge |
|----------|-------------------|-------------------|
| **Source** | Inferred from catalog text | Compatibility service / database |
| **Relationship type** | `compatible_with` | `verified_compatible_with` |
| **Confidence** | Variable — depends on text clarity and LLM accuracy | 1.0 — ground truth |
| **Coverage** | Limited to processed chunks | Complete for all products in the service |
| **Conditions** | Rarely captured (LLM may miss "only for 3/4 inch doors") | Can include door thickness, overlay type, boring pattern, etc. |

Both edge types coexist in the graph. At retrieval time, deterministic edges can be weighted higher to prioritize verified facts.

## What It Would Improve

### 1. Graph Connectivity (the biggest current weakness)

The graph currently has 206 connected components — most entities are isolated islands. Deterministic compatibility edges would bridge products that the LLM couldn't connect from text alone. A hinge, its compatible base plates, the doors they fit, and the required brackets would all become connected, even if those relationships were never stated in a single chunk.

**Expected impact**: Connected components could drop from 200+ to under 50, and average degree (connections per entity) would increase significantly.

### 2. Community Quality

Communities are detected by finding groups of densely connected entities. Right now, communities form based on which entities happened to be mentioned together in the same chunks. With deterministic compatibility data, communities would form around **real product systems** — all the hinges, plates, brackets, and doors that actually work together.

This means community summaries would describe genuine compatibility ecosystems rather than textual patterns, directly improving answers to questions like "What do I need for a frameless cabinet door?"

### 3. Multi-Hop Query Answers

Multi-hop queries are where GraphRAG is supposed to shine but currently underperforms. A question like "What mounting plates are compatible with soft-close hinges for 3/4 inch doors?" requires traversing:

```
soft-close hinges → compatible_with → mounting plates → compatible_with → 3/4 inch doors
```

If any of those edges are missing (because the LLM didn't extract them), the traversal fails. Deterministic edges fill those gaps with certainty.

### 4. Answer Trust and Precision

When the final answer includes compatibility information sourced from a deterministic service, the system can say:

> "The Nexis 110° Snap-on Hinge is **verified compatible** with 3/4 inch frameless cabinet doors using the Nexis Cam Base Plate H0 (source: compatibility database)"

Rather than:

> "Based on the catalog text, the Nexis hinge appears to be compatible with frameless applications"

This distinction matters for professional users making purchasing or specification decisions.

### 5. Handling Products Not in Catalogs

The current pipeline only knows about products mentioned in the indexed PDFs. A compatibility service could include products from other sources — newer products, discontinued products, third-party accessories — expanding the graph beyond what's in the catalogs.

## Implementation Considerations

### Entity Name Mapping

The hardest part of integration is matching entity names between the compatibility service and the knowledge graph. The service might use:
- Product codes: `71B3580`
- Internal SKUs: `GNXS-110-SC-45`
- Formal names: `Grass Nexis 110° Snap-on Soft-Close Hinge, 45mm`

While the graph has names extracted by the LLM:
- `Nexis 110° Hinge`
- `Nexis Snap-On Hinge`
- `Grass Nexis`

Options for resolving this:
1. **Lookup table** — manually map service IDs to graph entity names (reliable but requires maintenance)
2. **Include product codes in extraction** — modify the extraction prompt to capture product codes alongside names, then match on codes
3. **Fuzzy + embedding matching** — use string similarity and vector embeddings to automatically find the best match in the graph for each service entity
4. **Service provides both** — the compatibility service returns both its internal ID and the catalog display name

### Confidence and Conflict Resolution

When the LLM extracts `compatible_with` between two entities and the deterministic service says they are **not** compatible, the service should win. A conflict resolution strategy:

1. If the service says compatible → add `verified_compatible_with` edge
2. If the service says not compatible → remove any LLM-extracted `compatible_with` edge between those entities
3. If the service has no data → keep the LLM-extracted edge as-is

### Retrieval Weighting

During graph traversal (Step 10), deterministic edges should be prioritized. Options:
- Give `verified_compatible_with` edges a higher weight (e.g., 10x) so they're traversed first
- Include the edge source in the graph context sent to the LLM so it can distinguish verified facts from inferred relationships
- Filter graph context to show only verified edges for compatibility-specific queries

### Keeping Data Fresh

If the compatibility service is updated (new products, changed compatibility), the graph needs to be updated too. Options:
- **Full rebuild**: re-run the graph building step with fresh service data (simple, works for infrequent updates)
- **Incremental update**: add/remove only the changed edges (faster, more complex)
- **Timestamped edges**: track when each edge was added and flag stale data

## Post-Generation Verification

Beyond enriching the graph, the compatibility service can also be used **after** the LLM generates an answer to verify its claims before they reach the user. This is a second layer of protection — the graph provides better context going in, and verification catches errors coming out.

### How It Would Work

1. The LLM generates an answer as normal (using chunk context, graph context, and community summaries)
2. A post-processing step **extracts compatibility claims** from the answer — e.g., "the Nexis 110° hinge is compatible with frameless cabinet doors using the Cam Base Plate H0"
3. Each claim is **checked against the compatibility service**
4. The answer is returned to the user with verification status:
   - **Verified**: the service confirms the claim
   - **Contradicted**: the service says this is incorrect — the claim is flagged or corrected
   - **Unverified**: the service has no data on this pairing — the claim stands but is marked as unverified

### Example Output

Without verification:
> The Nexis 110° Snap-on Hinge works with 3/4 inch frameless cabinet doors using the Nexis Cam Base Plate H0.

With verification:
> The Nexis 110° Snap-on Hinge works with 3/4 inch frameless cabinet doors using the Nexis Cam Base Plate H0. **[Verified]**
>
> The Tiomos M9 is also compatible with this door type. **[Unverified — not in compatibility database]**

### Extracting Claims from the Answer

The simplest approach is a second LLM call that reads the generated answer and extracts structured compatibility claims:

```
Given this answer about cabinet hardware, extract every compatibility claim as JSON:
[{"product": "...", "compatible_with": "...", "via": "..."}]
```

Each extracted claim is then looked up in the service. This adds latency (one extra LLM call + service lookups) but provides a significant trust improvement for professional users.

### Where This Fits vs Graph Enrichment

| Approach | When It Acts | What It Does | Cost |
|----------|-------------|-------------|------|
| **Graph enrichment** (Section above) | Before retrieval | Adds verified edges so the LLM gets better context | One-time at graph build |
| **Post-generation verification** | After answer generation | Checks claims in the final answer against the service | Per-query (extra LLM call + lookups) |

Both approaches are complementary. Graph enrichment prevents most errors by giving the LLM accurate context. Post-generation verification catches the remaining cases where the LLM makes claims that go beyond the provided context or misinterprets relationships.

For maximum reliability, use both. For minimal cost, start with graph enrichment alone — it handles the majority of cases without per-query overhead.

---

## Summary

| Aspect | Current (LLM only) | With Compatibility Service |
|--------|-------------------|---------------------------|
| Compatibility data source | Inferred from catalog text | Ground truth from service + inferred from text |
| Graph connectivity | 206 components, fragmented | Significantly fewer components, well-connected |
| Community clusters | Based on textual co-occurrence | Based on real product systems |
| Multi-hop queries | Often fail due to missing edges | Reliable traversal through verified edges |
| Answer confidence | "appears to be compatible" | "verified compatible" |
| Product coverage | Limited to indexed catalog pages | Extends beyond catalogs |
