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

## Concrete Integration: window-project Constraint Engine

The [window-project](../../) repository (`C:\Users\steph\source\repos\window-project`) contains a production constraint engine that is a direct implementation of the deterministic compatibility service described above. This section maps the abstract design to the concrete system.

### What the Constraint Engine Does

Given customer requirements (cabinet type, door dimensions, overlay, brand preference), the engine deterministically evaluates **all valid product combinations** and returns ranked configurations with full explainability traces. Every recommendation is provably correct — no recommendation reaches the user without passing all constraint rules, and every recommendation includes the full rule trace showing *why* it's valid.

There are two engine versions:
- **V1** (`engine_v1/`): Production hinge engine — specialised for concealed hinge + mounting plate pairs (N=2). 53 hinges × 55 plates = 2,915 combinations, 14 constraint rules, 70+ tests.
- **V2** (`engine_v2/`): Generic N-candidate solver — handles any product family shape (N=1, N=2, N=3+). Three families prototyped: concealed hinges, drawer slides, LED lighting.

### How the Engine Maps to GraphRAG Integration

| Abstract Concept (this doc) | Concrete Implementation (window-project) |
|---|---|
| Compatibility service | `HingeConstraintEngine.solve()` or `NCandidateSolver.solve()` |
| Structured compatibility pairs | `Configuration` objects — each contains hinge, plate, rule results |
| `source` / `target` fields | `Configuration.hinge` and `Configuration.plate` |
| `relationship: compatible_with` | `Configuration.valid == True` (all rules passed) |
| `conditions` | `RuleResult.values_compared` — door thickness, overlay, boring pattern, etc. |
| `confidence: 1.0` | Always 1.0 — these are deterministic evaluations, not inferences |
| Entity name mapping | `ManufacturerProduct.manufacturer_part` (canonical ID) maps to graph entity names |

### What the Engine Provides That LLM Extraction Cannot

**14 constraint rules evaluated per combination:**

| Rule | What It Checks | Why LLM Extraction Misses It |
|------|---------------|------------------------------|
| R001 Brand Lock | Hinge and plate must be same brand | LLM may pair cross-brand products |
| R002 Series Compatibility | Hinge series must be in plate's compatible list | Buried in spec tables across pages |
| R003 Cabinet Type Match | Hinge, plate, and requirements must agree | Often implicit in catalog context |
| R004 Overlay in Range | Desired overlay within plate's achievable range | Requires overlay lookup table computation |
| R005 Inset Support | Plate must support inset application | Small footnote in catalog |
| R006 Door Thickness | Door thickness within hinge's rated range | LLM may extract range incorrectly |
| R007 Door Weight | Door weight ≤ capacity × number of hinges | Requires derived hinge count |
| R008 Hinges Per Door | Height-based formula (≤889mm→2, ≤1400mm→3, etc.) | Not in any single chunk |
| R009 Boring Pattern | Cabinet boring must match hinge boring | Simple but often missed |
| R011 Face Frame Overlay | Overlay ≤ frame width - 3mm | Conditional rule, rarely stated |
| R012 Adjacent Door Clearance | Combined overlay ≤ partition thickness | Multi-door spatial constraint |
| R013 Corner Cabinet Angle | Opening angle ≥ 155° for corners | Context-dependent |
| R014 Mounting Method | Hinge mounting compatible with plate mounting | Compatibility matrix lookup |
| R015 Cup Depth | Door thickness ≥ cup depth + 2mm | Derived from two different specs |

The LLM might extract that "Tiomos is a hinge" and "Tiomos has soft-close" — but it cannot compute that a specific Tiomos model paired with a specific mounting plate achieves exactly 16mm overlay on a 3/4" frameless cabinet door with 45mm boring at a combined price of $12.50 per door. The constraint engine can.

### Integration Architecture

```
┌─────────────────────────────────┐
│  window-project                 │
│  Constraint Engine              │
│                                 │
│  solve(requirements)            │
│    → list[Configuration]        │
│      ├─ hinge (product details) │
│      ├─ plate (product details) │
│      ├─ valid (bool)            │
│      └─ rule_results (traces)   │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│  micro-x-rag                    │
│  Knowledge Graph                │
│                                 │
│  For each valid Configuration:  │
│    add_edge(                    │
│      hinge → verified_          │
│      compatible_with → plate,   │
│      conditions={overlay,       │
│        cabinet_type, ...},      │
│      source="constraint_engine" │
│    )                            │
└─────────────────────────────────┘
```

### Practical Integration Steps

**Step 1: Import the engine**

The constraint engine is a pure Python package with no database dependencies (JSON-based). It can be imported directly:

```python
from engine_v1.solver import HingeConstraintEngine
from engine_v1.loader import load_hinges, load_plates
```

Or via the V2 generic solver:

```python
from engine_v2.core.solver_n import NCandidateSolver
from engine_v2.core.registry import FamilyRegistry
```

**Step 2: Generate all valid combinations for common scenarios**

Rather than querying per-user-request, pre-compute valid combinations for common cabinet configurations and inject them into the graph at build time:

```python
common_scenarios = [
    {"cabinet_type": "frameless", "door_thickness_mm": 19, "boring_pattern_mm": 45, ...},
    {"cabinet_type": "face_frame", "door_thickness_mm": 19, "boring_pattern_mm": 45, ...},
    # etc.
]

engine = HingeConstraintEngine(hinges, plates)
for scenario in common_scenarios:
    configs = engine.solve(CustomerRequirements(**scenario))
    for config in configs:
        # Add verified edge to the knowledge graph
        G.add_edge(
            normalize_name(config.hinge.description),
            normalize_name(config.plate.description),
            relations={"verified_compatible_with"},
            source="constraint_engine",
            weight=10,  # Higher weight than LLM-extracted edges
            conditions=scenario,
        )
```

**Step 3: Entity name mapping**

The engine uses `manufacturer_part` as canonical identity (e.g., "71B3550") and `description` for display names (e.g., "Blum CLIP top BLUMOTION 110° full_overlay"). The graph has LLM-extracted names like "Clip Top Blumotion". Mapping options:

1. **Include manufacturer part numbers in the extraction prompt** — modify the GraphRAG extraction to capture product codes, then match on codes
2. **Fuzzy match on descriptions** — use the existing `SequenceMatcher` or embedding similarity to match engine descriptions to graph entity names
3. **Add engine products as graph nodes directly** — create nodes from engine product data with both the canonical name and manufacturer part, then merge with existing graph nodes

**Step 4: Post-generation verification via the API**

The window-project includes a FastAPI demo at `demo/app.py`:

```
POST /api/solve/concealed_hinge
```

For post-generation verification, extract compatibility claims from the LLM answer, construct `CustomerRequirements` from the claim context, and call `solve()`. If the claimed combination appears in the results, it's verified. If not, it's contradicted.

### What This Unlocks for GraphRAG

With the constraint engine integrated:

- **"What mounting plates work with soft-close hinges for a 3/4" frameless door?"** — the engine has pre-computed every valid hinge+plate pair for this scenario. The graph traversal follows `verified_compatible_with` edges to return exact products with prices.

- **"Compare Blum vs Grass options for my cabinet"** — the engine evaluates both brands against the same requirements. The graph contains verified configurations from each, and the LLM can compare them with confidence.

- **"Why doesn't this hinge work with this plate?"** — the engine's `RuleResult` traces explain exactly which constraint failed and why. This can be included in the graph context or used in post-generation verification to provide precise failure explanations.

### Brand Lock: Mechanical Compatibility vs Business Rules

The constraint engine's `brand_lock` flag surfaces an important distinction: **"these products can work together"** vs **"these products should be sold together."**

A Blum CLIP top hinge might physically fit a Grass Tiomos mounting plate — the boring pattern matches, the mounting method is compatible, and the overlay range works. But no manufacturer would recommend it, no distributor would sell it as a set, and no warranty would cover it. The constraint engine treats brand lock as a customer preference (`brand_lock: bool = True` on `CustomerRequirements`), not a product property. When enabled, hinge and plate must be the same brand. When disabled, cross-brand combinations are allowed if all other rules pass.

**The problem for GraphRAG:** The user asking "What plates work with this hinge?" could mean either question. If you only pre-compute with brand lock on, you give the safe answer but miss technically valid options. If you only pre-compute with it off, you might suggest combinations that a professional would reject.

**Solution: Pre-compute both and tag the edges.**

Run the engine twice for each scenario — once with `brand_lock=True`, once with `brand_lock=False`:

```python
for scenario in common_scenarios:
    # Same-brand combinations (recommended)
    locked_req = CustomerRequirements(**scenario, brand_lock=True)
    for config in engine.solve(locked_req):
        G.add_edge(
            normalize_name(config.hinge.description),
            normalize_name(config.plate.description),
            relations={"verified_compatible_with"},
            brand_locked=True,
            weight=10,
        )

    # Cross-brand combinations (technically valid)
    unlocked_req = CustomerRequirements(**scenario, brand_lock=False)
    for config in engine.solve(unlocked_req):
        if config.hinge.brand != config.plate.brand:
            G.add_edge(
                normalize_name(config.hinge.description),
                normalize_name(config.plate.description),
                relations={"verified_compatible_with"},
                brand_locked=False,
                weight=5,  # Lower weight than same-brand edges
            )
```

This gives the graph both types of edges:

```
Blum CLIP top --[verified_compatible_with, brand_locked=true,  weight=10]--> Blum CLIP cruciform
Blum CLIP top --[verified_compatible_with, brand_locked=false, weight=5 ]--> Grass Tiomos plate
```

At retrieval time, same-brand edges are weighted higher and traversed first. But the cross-brand edges exist, so when a user explicitly asks "can I use a Blum hinge with a Grass plate?", the graph has that information.

The LLM prompt can then distinguish between the two:

> "The **Blum CLIP cruciform plate** is the recommended match (same brand, full warranty coverage, manufacturer-tested combination). The **Grass Tiomos plate** is technically compatible based on mechanical specifications, but this is a cross-brand pairing — check with your distributor regarding warranty and support."

This is a significant advantage over both pure LLM extraction (which has no concept of brand lock) and a naive deterministic integration (which would either show all combinations or only same-brand ones, with no way to explain the distinction).

### Data Available Today

| Product Family | Products | Status |
|---|---|---|
| Concealed hinges | 53 hinges + 55 mounting plates | Real catalog data, production rules |
| Drawer slides | 4 slides | Synthetic prototype |
| LED lighting | 5 bars + 4 drivers + 4 dimmers | Synthetic prototype |
| 10 more families | Not yet modelled | Planned in production roadmap |

The concealed hinge data covers the same Blum and Grass products that are in the micro-x-rag PDF catalogs, making it immediately usable for integration.

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
