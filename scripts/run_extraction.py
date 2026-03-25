"""Run or resume entity extraction using Claude API.

Usage:
    python scripts/run_extraction.py              # Resume from checkpoint or start fresh
    python scripts/run_extraction.py --force      # Start fresh (deletes existing extractions)
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import anthropic
import fitz
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

CATALOG_DIR = Path(__file__).parent.parent / "catalogs"
EXTRACTIONS_PATH = Path(__file__).parent.parent / "extractions.json"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

extraction_client = anthropic.Anthropic()

EXTRACTION_PROMPT = """Extract entities and relationships from this hardware catalog text.

ENTITY TYPES (use ONLY these exact values):
  product, manufacturer, feature, specification, material, certification, category

RELATIONSHIP TYPES (use ONLY these exact values):
  has_feature, manufactured_by, has_specification, compatible_with, part_of, variant_of

Return ONLY a valid JSON object with no markdown formatting, no code blocks, no extra text.
Use "relation" as the key for relationship type (not "type").

Example:
{"entities": [{"name": "Tiomos", "type": "product"}], "relationships": [{"source": "Tiomos", "relation": "manufactured_by", "target": "Grass"}]}

TEXT:
$TEXT$

JSON:"""


def extract_pdf_pages(pdf_path, max_pages=None):
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        if max_pages and i >= max_pages:
            break
        pages.append({"page": i + 1, "text": page.get_text()})
    doc.close()
    return pages


def chunk_text(text, chunk_size=800, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def extract_entities_and_relations(chunk_text, retries=2):
    for attempt in range(retries + 1):
        try:
            response = extraction_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1024,
                temperature=0.0,
                messages=[{"role": "user", "content": EXTRACTION_PROMPT.replace("$TEXT$", chunk_text)}],
            )
            content = response.content[0].text.strip()
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                parsed = json.loads(json_match.group())
                entities = parsed.get("entities", [])
                relationships = parsed.get("relationships", [])
                for rel in relationships:
                    if "type" in rel and "relation" not in rel:
                        rel["relation"] = rel.pop("type")
                return {"entities": entities, "relationships": relationships}
        except json.JSONDecodeError as e:
            if attempt == retries:
                print(f"\nWarning: JSON parse error: {e}")
        except Exception as e:
            if attempt == retries:
                print(f"\nWarning: Extraction failed: {type(e).__name__}: {e}")
    return {"entities": [], "relationships": []}


def main():
    force = "--force" in sys.argv

    # Build chunks
    print("Building chunks from PDFs...")
    all_chunks = []
    for pdf_path in sorted(CATALOG_DIR.glob("*.pdf")):
        pages = extract_pdf_pages(pdf_path)
        print(f"  {pdf_path.name}: {len(pages)} pages")
        for page in pages:
            chunks = chunk_text(page["text"], CHUNK_SIZE, CHUNK_OVERLAP)
            for j, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:
                    continue
                all_chunks.append({
                    "id": f"{pdf_path.stem}_p{page['page']}_c{j}",
                    "text": chunk,
                    "metadata": {"source": pdf_path.name, "page": page["page"]},
                })
    print(f"Total chunks: {len(all_chunks)}")

    # Load or start
    if EXTRACTIONS_PATH.exists() and not force:
        with open(EXTRACTIONS_PATH) as f:
            all_extractions = json.load(f)
        # Check if data is valid (not empty)
        total_e = sum(len(e.get("entities", [])) for e in all_extractions)
        if total_e > 0:
            print(f"Loaded {len(all_extractions)} extractions ({total_e} entities)")
        else:
            print("Existing file has no entities — starting fresh")
            all_extractions = []
    else:
        all_extractions = []

    if len(all_extractions) >= len(all_chunks):
        print("Extraction already complete!")
        return

    start_idx = len(all_extractions)
    remaining = all_chunks[start_idx:]
    print(f"Extracting {len(remaining)} chunks (starting from {start_idx})...")

    start_time = time.time()
    consecutive_errors = 0

    for i, chunk in enumerate(remaining):
        result = extract_entities_and_relations(chunk["text"])
        result["chunk_id"] = chunk["id"]
        result["source"] = chunk["metadata"]["source"]
        result["page"] = chunk["metadata"]["page"]
        all_extractions.append(result)

        if not result["entities"] and not result["relationships"]:
            consecutive_errors += 1
            if consecutive_errors >= 10:
                print(f"\n\n10 consecutive failures — check API credits. Saving progress...")
                with open(EXTRACTIONS_PATH, "w") as f:
                    json.dump(all_extractions, f)
                print(f"Saved {len(all_extractions)} extractions to {EXTRACTIONS_PATH}")
                sys.exit(1)
        else:
            consecutive_errors = 0

        elapsed = time.time() - start_time
        rate = (i + 1) / elapsed if elapsed > 0 else 0
        remaining_time = (len(remaining) - i - 1) / rate if rate > 0 else 0
        total_e = sum(len(e.get("entities", [])) for e in all_extractions)
        total_r = sum(len(e.get("relationships", [])) for e in all_extractions)
        print(
            f"  [{start_idx + i + 1}/{len(all_chunks)}] "
            f"Entities: {total_e}, Relations: {total_r} "
            f"(~{remaining_time:.0f}s remaining)",
            end="\r",
        )

        if (i + 1) % 50 == 0:
            with open(EXTRACTIONS_PATH, "w") as f:
                json.dump(all_extractions, f)

    with open(EXTRACTIONS_PATH, "w") as f:
        json.dump(all_extractions, f)

    elapsed = time.time() - start_time
    total_e = sum(len(e.get("entities", [])) for e in all_extractions)
    total_r = sum(len(e.get("relationships", [])) for e in all_extractions)
    print(f"\n\nDone in {elapsed:.1f}s")
    print(f"Final: {len(all_extractions)} chunks, {total_e} entities, {total_r} relationships")


if __name__ == "__main__":
    main()
