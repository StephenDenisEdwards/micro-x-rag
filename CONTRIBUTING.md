# Contributing to micro-x-rag

## Prerequisites

- Python 3.11+
- Ollama running locally ([ollama.com](https://ollama.com))
- An Anthropic API key

## Setup

```bash
git clone https://github.com/StephenDenisEdwards/micro-x-rag.git
cd micro-x-rag
cp .env.example .env   # Add your API keys
pip install -r requirements.txt
```

Pull required Ollama models:

```bash
ollama pull nomic-embed-text   # embeddings
```

## Code Style

- **Type hints:** Required on all public functions
- **Naming:** snake_case for functions/variables, PascalCase for classes
- **Docstrings:** Required for public classes and non-trivial functions
- **Configuration:** All model references must use the configurable provider/model variables in the notebook's Setup & Configuration cell — no hardcoded model names

## Commit Messages

Use conventional prefix style:

| Prefix | Use For |
|--------|---------|
| `feat:` | New features or capabilities |
| `fix:` | Bug fixes |
| `docs:` | Documentation changes only |
| `refactor:` | Code restructuring without behaviour change |
| `chore:` | Build, tooling, dependency updates |
| `test:` | Adding or updating tests |

Examples:
```
feat: add deterministic compatibility service integration
fix: handle truncated JSON in entity extraction
docs: add comparison of mistral vs Claude community summaries
refactor: extract llm_chat dispatcher from hardcoded client calls
```

## Branching

- `main` is the primary branch
- Create feature branches for non-trivial changes
- Keep commits focused — one logical change per commit

## Project Structure

```
micro-x-rag/
├── notebooks/                    # Jupyter notebooks (main workflow)
│   ├── rag_catalog_search.ipynb  # Standard RAG
│   └── graph_rag_catalog_search.ipynb  # GraphRAG
├── catalogs/                     # Source PDF catalogs
├── scripts/                      # Standalone utility scripts
├── docs/                         # Project documentation
│   ├── architecture/             # ADRs and system architecture
│   ├── design/                   # Design docs
│   └── planning/                 # Feature plans and roadmaps
├── requirements.txt
├── CLAUDE.md                     # AI assistant context
├── CONTRIBUTING.md               # This file
├── CHANGELOG.md                  # Version history
└── README.md                     # Project overview
```

## Documentation

- Update relevant docs when changing behaviour
- Design docs and analysis live in `docs/`
- Architecture decisions live in `docs/architecture/decisions/`
- Planning and roadmaps live in `docs/planning/`
- Keep `CLAUDE.md` up to date when adding key files or changing conventions
- Keep `README.md` up to date when adding notebooks or changing config

## Architecture Decisions

Significant design choices are recorded as ADRs in `docs/architecture/decisions/`. Before proposing a change that affects architecture, check existing ADRs and create a new one if needed.
