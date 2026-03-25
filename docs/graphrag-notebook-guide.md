# GraphRAG Notebook: Step-by-Step Guide

This document walks through every step of the `notebooks/graph_rag_catalog_search.ipynb` notebook in detail. It is written for someone who may be new to RAG (Retrieval-Augmented Generation), knowledge graphs, or LLMs.

---

## What This Notebook Does

The notebook builds a **GraphRAG** system — a way to search product catalogs using AI that goes beyond simple text matching. It reads PDF catalogs, understands the products and relationships described in them, builds a knowledge graph, and then uses all of that to answer questions.

The key idea: instead of just finding text chunks that look similar to your question (standard RAG), GraphRAG also understands *how things connect* — which products are made by which manufacturers, which features are compatible with which hinges, and so on.

---

## Step 0: Install Dependencies (Cell 1)

```
%pip install -q pymupdf chromadb anthropic openai python-dotenv httpx networkx pyvis
```

This installs the Python libraries the notebook needs:

| Library | What It Does |
|---------|-------------|
| **pymupdf** (`fitz`) | Reads PDF files and extracts text from each page |
| **chromadb** | A vector database — stores text as mathematical vectors so we can find similar text quickly |
| **anthropic** | The official Python client for Claude (Anthropic's AI model) |
| **openai** | Used here to talk to Ollama (a local AI server) which speaks the same protocol as OpenAI |
| **python-dotenv** | Loads secret API keys from a `.env` file so they don't end up in code |
| **httpx** | Makes HTTP requests (used to call Ollama's embedding API) |
| **networkx** | Builds and analyzes graphs (networks of connected things) |
| **pyvis** | Creates interactive graph visualizations you can open in a browser |

---

## Step 1: Setup & Configuration (Cells 2–3)

The notebook loads configuration and sets up key parameters:

```python
CATALOG_DIR = Path("../catalogs")          # Where the PDF catalogs live
OLLAMA_EMBED_MODEL = "nomic-embed-text"    # Model that converts text to vectors
OLLAMA_CHAT_MODEL = "mistral:7b"           # Local model for community summaries
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"  # Claude model for extraction and answers
CHUNK_SIZE = 800                           # How many characters per text chunk
CHUNK_OVERLAP = 100                        # How much chunks overlap with each other
MAX_PAGES_PER_PDF = None                   # Process all pages (set a number to limit)
FORCE_RE_EXTRACT = False                   # Whether to redo extraction from scratch
```

### What are these models?

The notebook uses **three different AI models**, each for a different job:

1. **Claude Sonnet** (`claude-sonnet-4-20250514`) — A powerful cloud-based model from Anthropic. Used for the two hardest tasks: extracting entities from text (Step 3) and generating final answers (Step 11). It costs money per API call but produces high-quality, well-structured output.

2. **Mistral 7B** (`mistral:7b`) — A smaller model that runs locally on your computer via Ollama. Used for generating community summaries (Step 8). It's free to run but produces lower quality output than Claude.

3. **Nomic Embed Text** (`nomic-embed-text`) — A specialized model that converts text into vectors (lists of numbers that capture meaning). Used in Step 9 to make text searchable. It doesn't generate text — it only produces numbers.

### Why use different models?

Cost and quality trade-offs. Claude is the best but costs money per call. Entity extraction (Step 3) requires high precision — getting entities and relationships wrong corrupts the entire graph — so we use Claude there. Community summaries (Step 8) are less critical and there are fewer of them, so we use the free local model. Embeddings require a specialized model designed for that purpose.

---

## Step 2: Extract and Chunk PDFs (Cells 4–5)

### What happens

1. Each PDF catalog is opened using PyMuPDF
2. Text is extracted from every page
3. Each page's text is split into **chunks** — smaller pieces of text

### Why chunk?

AI models have limited input sizes, and smaller pieces of text are easier to work with. If you send an entire 50-page catalog to an AI model and ask "what entities are in here?", it will miss things. Smaller chunks (800 characters, roughly a paragraph) let the model focus on one section at a time.

### How chunking works

The `chunk_text()` function:

1. Takes a page of text (could be thousands of characters)
2. Tries to split it into ~800 character pieces
3. Looks for natural break points (sentences ending with `.` or paragraph breaks `\n`) near the end of each chunk, so it doesn't cut words or sentences in half
4. Each chunk **overlaps** with the next by 100 characters — this ensures that if an important sentence spans the boundary between two chunks, it appears fully in at least one of them

### Example

Imagine a page with 2,000 characters of text:
- Chunk 1: characters 0–810 (found a sentence break at 810)
- Chunk 2: characters 710–1520 (starts 100 chars before chunk 1 ended, for overlap)
- Chunk 3: characters 1420–2000 (the remainder)

Each chunk is stored with metadata tracking which PDF file and page number it came from. This metadata is used later to cite sources in answers.

### Output

A list of chunks, each with an ID, the text content, and metadata (source file, page number, chunk index). For the full catalog set of ~274 pages, this produces around 676 chunks.

---

## Step 3: Entity & Relationship Extraction (Cells 6–7)

This is the core of what makes GraphRAG different from standard RAG. Instead of just storing text chunks, we ask an AI model to **read each chunk and identify the important things in it and how they connect**.

### What are entities?

An **entity** is a named thing that matters. In hardware catalogs, entities include:

| Entity Type | Examples |
|------------|---------|
| **product** | Tiomos M9 110° Hinge, Nexis Snap-on Hinge, SOSS Invisible Hinge |
| **manufacturer** | Grass, Blum, Salice, SOSS |
| **feature** | Soft-Close, Tool-Free Installation, Snap-on Technology |
| **specification** | 110° opening angle, 45mm boring pattern, 3.8 kg weight |
| **material** | Nickel-Plated Steel, Zinc Die Cast |
| **certification** | BHMA certified |
| **category** | Concealed Hinges, Institutional Hinges, Lid Supports |

### What are relationships?

A **relationship** connects two entities. Each relationship has a type:

| Relationship Type | Meaning | Example |
|------------------|---------|---------|
| **manufactured_by** | Who makes it | Tiomos → manufactured_by → Grass |
| **has_feature** | What it can do | Tiomos → has_feature → Soft-Close |
| **has_specification** | A measurable property | Tiomos M9 → has_specification → 110° opening angle |
| **compatible_with** | Works together with | Nexis Hinge → compatible_with → Nexis Base Plate |
| **part_of** | Belongs to a larger group | Tiomos M9 → part_of → Tiomos System |
| **variant_of** | A version of something | Tiomos Impresso → variant_of → Tiomos |

### How extraction works

For each chunk, the notebook sends it to Claude with this instruction (simplified):

> "Here is some text from a hardware catalog. Find every product, manufacturer, feature, specification, material, certification, and category mentioned. Also find every relationship between them. Return the results as JSON."

Claude reads the chunk and returns structured data like:

```json
{
  "entities": [
    {"name": "Tiomos M9", "type": "product"},
    {"name": "Grass", "type": "manufacturer"},
    {"name": "110°", "type": "specification"}
  ],
  "relationships": [
    {"source": "Tiomos M9", "relation": "manufactured_by", "target": "Grass"},
    {"source": "Tiomos M9", "relation": "has_specification", "target": "110°"}
  ]
}
```

### Why Claude for extraction?

This is the most important step in the pipeline. If the extraction is poor — wrong entity names, missing relationships, invented types — then the entire knowledge graph will be unreliable. Claude is used here because:

- It follows the JSON format reliably (smaller models often produce malformed JSON)
- It respects the schema (only uses the 7 entity types and 6 relationship types we specified)
- It names entities consistently (smaller models might call the same product "Tiomos", "TIOMOS", and "Grass Tiomos" in different chunks)

### Error handling

The extraction function includes:
- **Retries** (up to 2 attempts per chunk) in case of network errors
- **JSON repair** — strips markdown code blocks that Claude sometimes wraps around JSON
- **Regex fallback** — if the response isn't clean JSON, it searches for a JSON object within the response text
- **Graceful failure** — if extraction fails completely for a chunk, it returns empty results rather than crashing

---

## Step 4: Run Extraction on All Chunks (Cells 8–9)

This cell orchestrates the extraction across all chunks:

1. **Checks for cached results** — extraction is slow and costs money (API calls to Claude), so results are saved to `extractions.json`. If that file exists and `FORCE_RE_EXTRACT` is `False`, it loads the saved results instead of re-running.

2. **Iterates through every chunk**, calling the extraction function from Step 3 on each one.

3. **Tracks progress** — prints a running count of entities and relationships found, and estimates time remaining.

4. **Checkpoints every 50 chunks** — saves progress to disk so that if something goes wrong (network failure, API rate limit), you don't lose all your work. You can restart the notebook and it will load the saved results.

5. **Detects failures** — if the first 20 chunks all fail (no entities extracted), it stops early and warns you to check your API key or internet connection.

### Output

A list of extraction results, one per chunk, each containing:
- The entities and relationships found
- The chunk ID, source file, and page number (so we can trace everything back to the original catalog)

---

## Step 4a: Post-Process Extractions (Cells 10–13)

Even with Claude's high-quality extraction, the raw results need cleaning. This step has three parts:

### Part 1: Normalize entity and relationship types (Cell 11)

The extraction prompt says "use ONLY these 7 entity types" but in practice, the model sometimes uses variants like `product_model` instead of `product`, or `includes` instead of `has_feature`. The normalization step maps all variants to canonical types using a lookup dictionary.

**Before**: 57 different entity types, 50+ relationship types
**After**: 7 entity types, 6 relationship types

Any type that isn't in the lookup dictionary gets a sensible default (`feature` for entities, `has_feature` for relationships).

### Part 2: Deduplicate entities (Cell 12)

The same product might appear with slightly different names across chunks:
- "Lift Mechanism Sets" vs "Lift Mechanisms"
- "Arm Assembly Mounting Plate" vs "Arm Assembly Mounting Plates"
- "All Metal Hinge, Nickel-Plated" vs "All Metal Hinge, Nickel Plated"

The deduplication step uses **fuzzy string matching** (the `SequenceMatcher` algorithm) to find names that are more than 92% similar. When it finds a match, it keeps the version that appears most frequently as the **canonical** name and rewrites all occurrences of the other version.

This is important because if "Tiomos" and "TIOMOS" aren't merged, they become two separate nodes in the graph with no connection between them, losing relationships that should exist.

### Part 3: Filter noise (Cell 13)

Removes low-value entities that add noise to the graph:
- **Pure numbers** (e.g., "42", "3.5") — these are specification values, not meaningful entities
- **Very short strings** (less than 3 characters) — usually extraction artifacts
- **Stop words** (e.g., "N/A", "Unknown", "Page", "Table", "Figure") — generic terms that don't represent real products or features

Also removes relationships where either endpoint is missing or too short to be meaningful.

---

## Step 5: Build the Knowledge Graph (Cells 14–15)

This step takes all the cleaned entities and relationships and assembles them into a **graph** — a data structure where things (nodes) are connected by relationships (edges).

### What is a graph?

Think of it like a map of connections:
- Each **node** is an entity (a product, manufacturer, feature, etc.)
- Each **edge** (line between nodes) is a relationship (manufactured_by, compatible_with, etc.)

For example:
```
[Grass] --manufactured_by-- [Tiomos] --has_feature-- [Soft-Close]
                                |
                         --compatible_with--
                                |
                          [System Base Plate]
```

### How the graph is built

For each extraction result (one per chunk):

1. **Add entity nodes** — if the entity already exists in the graph, increment its mention count and add the new source file to its source list. If it's new, create it. When an entity appears with different types in different chunks (e.g., sometimes "product", sometimes "feature"), **majority voting** decides — whichever type appears most often wins.

2. **Add relationship edges** — if two entities are already connected, increment the edge weight and add the new relationship type. If they're not connected yet, create a new edge. If a relationship references an entity that wasn't explicitly extracted (it only appeared as a relationship endpoint), a new node is created for it with a default type of "product".

### Name normalization

All entity names are converted to Title Case (`normalize_name()` function) so that "soft close", "SOFT CLOSE", and "Soft Close" all become the same node: "Soft Close".

### Graph statistics

The notebook prints key metrics about the resulting graph:

| Metric | What It Means |
|--------|--------------|
| **Nodes** | Total number of unique entities |
| **Edges** | Total number of unique connections |
| **Connected components** | How many separate "islands" exist (ideally 1 — everything connected) |
| **Average degree** | Average number of connections per entity (higher = more connected) |
| **Density** | How close the graph is to having every possible connection (0 = no edges, 1 = fully connected) |

A good knowledge graph has few connected components (most things are reachable from most other things), a high average degree (entities have many connections), and reasonable density.

---

## Step 6: Community Detection (Cells 16–17)

### What is a community?

A **community** is a group of entities that are more connected to each other than to entities outside the group. Think of it as a "cluster" or "topic area" within the graph.

For example, one community might contain:
- Nexis Snap-on Hinge, Nexis Base Plate, Nexis Impresso, Cam Base Plate, Soft-Close Adapter
- These are all Nexis-related products that reference each other frequently

Another community might contain:
- Aventos HF, Aventos HL, Blum, Lift System, Cabinet Height Range
- These are all Blum lift system products

### How the Louvain algorithm works

The notebook uses the **Louvain algorithm** (`nx.community.louvain_communities`), one of the most popular community detection methods. Here's the intuition:

1. Start with every entity in its own community (one per node)
2. For each entity, check: would moving it to a neighbor's community increase the overall **modularity** (a measure of how well communities are separated)?
3. If yes, move it
4. Repeat until no more moves improve modularity
5. Then treat each community as a single "super-node" and repeat the process at a higher level

The result is a partition of the graph into communities where entities within a community are densely connected and entities between communities are sparsely connected.

### Why detect communities?

Communities enable answering **broad, thematic questions**. If someone asks "What are the main product categories?", no single chunk in any catalog contains that answer. But a community summary that says "This cluster contains the Nexis hinge system including snap-on, impresso, and standard variants with soft-close adapters and various base plates" captures thematic information that spans many chunks and even multiple catalogs.

### Output

Each node in the graph gets a `community` attribute (an integer ID). The communities are sorted by size (number of members) for use in the next steps.

---

## Step 7: Visualize the Knowledge Graph (Cells 18–19)

Creates an **interactive HTML visualization** you can open in a browser.

### How it works

1. **Filters to notable entities** — only shows entities with 3+ mentions (to keep the visualization readable; the full graph would be overwhelming)
2. **Colors nodes by community** — all entities in the same community get the same color, so you can visually see the clusters
3. **Sizes nodes by mentions** — frequently mentioned entities appear larger
4. **Labels edges** — hovering over a connection shows the relationship type(s)
5. **Uses physics simulation** — nodes push each other apart (Barnes-Hut gravity) while edges pull connected nodes together, naturally arranging related entities near each other

The result is saved as `knowledge_graph.html` in the project root.

---

## Step 8: Community Summaries (Cells 20–21)

This is where the communities detected in Step 6 become useful for answering questions. Each community gets a **natural language summary** — a short paragraph describing what the group is about.

### How it works

For each of the top 10 largest communities (skipping those with fewer than 3 members):

1. **Collect entity information** — the top 20 entities in the community (by mention count), formatted as:
   ```
   - Nexis Snap-On Hinge (type: product, mentions: 12)
   - Grass (type: manufacturer, mentions: 8)
   - Soft-Close (type: feature, mentions: 6)
   ```

2. **Collect internal relationships** — up to 30 edges where both endpoints are in the community:
   ```
   - Nexis Snap-On Hinge --[manufactured_by]--> Grass
   - Nexis Snap-On Hinge --[has_feature]--> Soft-Close
   - Nexis Snap-On Hinge --[compatible_with]--> Nexis Base Plate
   ```

3. **Send to the LLM** with the prompt: *"You are summarizing a cluster of related entities from hardware product catalogs. Write a concise summary (2-4 sentences) describing what this group represents, the key products/features, and how they relate."*

4. **Store the summary** along with the community size and top 5 entities.

### Why this step matters

Community summaries are **the single biggest advantage** GraphRAG has over standard RAG. They are pre-computed overviews of product clusters that capture cross-document themes. When someone asks a broad question like "What are the main product categories?", no single chunk in any catalog contains that answer — but a community summary might.

### Current limitation

This step currently uses `mistral:7b` (a local model) rather than Claude. This means the summaries are lower quality than they could be — sometimes shallow lists of entities rather than insightful thematic descriptions. Upgrading this to Claude or a better local model would directly improve GraphRAG's performance on broad questions.

---

## Step 9: Build the ChromaDB Vector Store (Cells 22–23)

### What is a vector store?

A **vector store** (or vector database) is a specialized database that stores text as **vectors** — lists of numbers that capture the meaning of the text. Two pieces of text with similar meanings will have similar vectors, even if they use different words.

For example, "soft-close hinge mechanism" and "gentle closing door hardware" would have similar vectors because they describe similar concepts, even though they share few words.

### What is an embedding?

An **embedding** is the process of converting text to a vector. The `nomic-embed-text` model reads a piece of text and outputs a list of numbers (typically 768 numbers) that represent its meaning. This is not a generative model — it doesn't produce text. It only produces numbers.

### How the OllamaEmbeddingFunction works

The notebook defines a custom embedding function that:
1. Takes a list of text documents
2. Sends them to Ollama's embedding API in batches of 32
3. Returns the resulting vectors

ChromaDB uses this function automatically whenever text is added to or queried from a collection.

### Two collections are created

**1. `graph_rag_chunks`** — contains all the original text chunks from Step 2. This is the same data standard RAG would use.

**2. `graph_rag_communities`** — contains the community summaries from Step 8. This is unique to GraphRAG.

Both use cosine similarity for matching (a standard way to measure how similar two vectors are — 0 means identical, 2 means completely different).

### Why two collections?

At query time, the system searches both collections independently:
- The chunks collection finds relevant raw text (same as standard RAG)
- The community collection finds relevant thematic summaries (the GraphRAG advantage)

---

## Step 10: GraphRAG Retrieval (Cells 24–25)

This is where everything comes together. When a user asks a question, the retrieval function combines **three sources** of information:

### Source 1: Vector search on chunks

The user's question is embedded (converted to a vector) and compared against all chunk vectors in ChromaDB. The 5 most similar chunks are returned. This is identical to what standard RAG does.

**Example**: For the query "What soft-close hinge options are available?", this might return chunks from the Grass Tiomos catalog page about soft-close mechanisms and from the Wurth Baer section about soft-close adapters.

### Source 2: Graph traversal

This is what standard RAG cannot do. The process:

1. **Find entities in retrieved chunks** — look at which entities (graph nodes) were originally extracted from the chunks found in Source 1. For example, if a retrieved chunk came from `chunk_42`, check which graph nodes list `chunk_42` in their `chunk_ids`.

2. **Follow connections** — for each entity found, traverse the graph to find its neighbors (entities connected by relationships). The `hop_depth` parameter controls how far to travel (default: 1 hop, meaning direct connections only).

3. **Build structured context** — format the discovered entities and their relationships as text:
   ```
   Nexis Snap-On Hinge (product, 12 mentions):
     Nexis Snap-On Hinge --[manufactured_by]--> Grass
     Nexis Snap-On Hinge --[compatible_with]--> Nexis Base Plate
     Nexis Snap-On Hinge --[has_feature]--> Soft-Close
   ```

**Why this matters**: The vector search might find a chunk about Nexis hinges but not the chunk about compatible base plates (because the base plate chunk uses different vocabulary). Graph traversal follows the `compatible_with` edge to find the base plate information regardless of text similarity.

### Source 3: Community summaries

The user's question is also searched against the community summary collection. The 2 most relevant summaries are returned. These provide high-level thematic context.

**Why this matters**: If the question is broad ("What are the main product categories?"), community summaries may be more relevant than any individual chunk.

### Output

A dictionary containing:
- `chunks` — the top 5 text chunks (with source metadata)
- `graph_context` — formatted entity relationships from graph traversal
- `graph_entities_found` — how many entities were discovered
- `communities` — the top 2 relevant community summaries

---

## Step 11: GraphRAG Answer Generation (Cells 26–27)

### Building the prompt

The `build_graph_rag_prompt()` function assembles all three context sources into a single prompt for the LLM:

```
You are a knowledgeable hardware product specialist. Answer the user's question
using ALL the provided context. You have three sources of information:

1. CATALOG TEXT — direct excerpts from product catalogs
2. KNOWLEDGE GRAPH — extracted entity relationships showing how products, features, and specs connect
3. THEMATIC SUMMARIES — high-level summaries of product clusters

=== CATALOG TEXT ===
[Source 1: grass-nexis-catalog.pdf, Page 37]
The Nexis soft-close adapter is compatible with 95°, 100°, 110°...
...

=== KNOWLEDGE GRAPH (entity relationships) ===
Nexis Snap-On Hinge (product, 12 mentions):
  Nexis Snap-On Hinge --[compatible_with]--> Nexis Base Plate
  Nexis Snap-On Hinge --[has_feature]--> Soft-Close
...

=== THEMATIC SUMMARIES ===
- This cluster represents the Grass Nexis hinge system including snap-on and impresso variants...
...

USER QUESTION: What soft-close hinge options are available?
```

The LLM (Claude) receives all three context sources and synthesizes them into a coherent answer. The instructions tell it to cite source catalogs and page numbers, and to clearly state when the context doesn't contain enough information.

### Two generation paths

The notebook provides two functions:
- `graph_rag_query_claude()` — uses Claude for the final answer (higher quality, costs money)
- `graph_rag_query_ollama()` — uses `mistral:7b` locally (free, lower quality)

---

## Step 12: Compare Standard RAG vs GraphRAG (Cells 28–29)

### Standard RAG implementation

For comparison, the notebook includes a `standard_rag_query_claude()` function that does traditional RAG:
1. Embed the question
2. Find the 5 most similar chunks
3. Send them to Claude with the question
4. Return the answer

This uses the **same chunks** and **same LLM** (Claude) as GraphRAG — the only difference is that standard RAG doesn't include graph context or community summaries.

### Comparison queries

Four queries are designed to test different strengths:

1. **"What are the main product categories across all catalogs and how do they relate?"** — A broad, thematic question. Tests whether the system can synthesize information across many documents. GraphRAG's community summaries give it an advantage here.

2. **"Compare the hinge systems from Grass and Wurth Baer."** — A cross-document comparison. Tests whether the system can find and combine information from different catalogs.

3. **"What mounting plates are compatible with soft-close hinges?"** — A multi-hop question. The answer requires connecting hinges → compatibility → mounting plates, information likely spread across multiple chunks. Graph traversal helps here.

4. **"What is the maximum opening angle for Tiomos hinges?"** — A specific fact lookup. Standard RAG should handle this fine if the right chunk is retrieved — no graph needed.

---

## Step 13: Interactive Query (Cells 30–31)

A convenience cell where you can type any question and choose whether to use Claude or Ollama for the answer. It shows the full retrieval results (which chunks were found, how many graph entities, which community summaries matched) before the answer.

---

## Step 14: Explore the Knowledge Graph (Cells 32–35)

Utility functions for directly querying the graph:

### `explore_entity(name)`

Shows everything the graph knows about a specific entity:
- Its type, mention count, source files, and community
- All its connections (neighbors and relationship types)
- Includes fuzzy matching — if you type "tiomos" it finds "Tiomos"

### `find_path(entity_a, entity_b)`

Finds the shortest path between two entities in the graph. For example, `find_path("Tiomos", "Soft Close")` might show:
```
Tiomos --[has_feature]--> Soft-Close
```
Or if they're not directly connected, it shows the chain of entities and relationships that link them.

### Graph statistics (Cell 35)

Prints a full summary of the graph: node count, edge count, connected components, community count, average degree, density, and the full distribution of entity types and relationship types.

---

## How Everything Connects: The Full Pipeline

```
PDF Catalogs
    │
    ▼
[Step 2] Extract text, split into chunks
    │
    ├──────────────────────────────┐
    ▼                              ▼
[Step 3-4] Extract entities    [Step 9] Embed chunks
& relationships (Claude)       in ChromaDB (nomic-embed-text)
    │                              │
    ▼                              │
[Step 4a] Clean & normalize        │
    │                              │
    ▼                              │
[Step 5] Build knowledge graph     │
    │                              │
    ▼                              │
[Step 6] Detect communities        │
    │                              │
    ▼                              │
[Step 8] Summarize communities     │
(mistral:7b)                       │
    │                              │
    ▼                              │
[Step 9] Embed summaries           │
in ChromaDB                        │
    │                              │
    └──────────────┬───────────────┘
                   │
                   ▼
           [Step 10] At query time:
           1. Vector search → chunks
           2. Graph traversal → entity relationships
           3. Vector search → community summaries
                   │
                   ▼
           [Step 11] Combine all three
           context sources → Claude → Answer
```

**Standard RAG** only has the right side of this diagram: chunks go into ChromaDB, queries find similar chunks, and the LLM answers from those chunks alone.

**GraphRAG** adds the entire left side: entity extraction, knowledge graph construction, community detection, and community summaries — providing the LLM with structured relationships and thematic overviews that no individual chunk contains.
