# Open WebUI

Open WebUI is a self-hosted, extensible AI platform designed to operate entirely offline. It provides a polished web interface for interacting with LLMs via Ollama and OpenAI-compatible APIs, with a built-in inference engine for RAG.

- **Website**: https://openwebui.com
- **Docs**: https://docs.openwebui.com
- **GitHub**: https://github.com/open-webui/open-webui
- **Discord**: https://discord.gg/5rJgQTnV4s

## Installation

### Docker (recommended)

**Basic setup with local Ollama:**

```bash
docker run -d -p 3000:8080 --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data --name open-webui --restart always \
  ghcr.io/open-webui/open-webui:main
```

Access at `http://localhost:3000`. First sign-up becomes the super admin.

**With GPU support (NVIDIA):**

```bash
docker run -d -p 3000:8080 --gpus all --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data --name open-webui --restart always \
  ghcr.io/open-webui/open-webui:cuda
```

**Bundled with Ollama (all-in-one):**

```bash
docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama \
  -v open-webui:/app/backend/data --name open-webui --restart always \
  ghcr.io/open-webui/open-webui:ollama
```

**Remote Ollama server:**

```bash
docker run -d -p 3000:8080 -e OLLAMA_BASE_URL=https://example.com \
  -v open-webui:/app/backend/data --name open-webui --restart always \
  ghcr.io/open-webui/open-webui:main
```

**OpenAI API only (no Ollama):**

```bash
docker run -d -p 3000:8080 -e OPENAI_API_KEY=your_secret_key \
  -v open-webui:/app/backend/data --name open-webui --restart always \
  ghcr.io/open-webui/open-webui:main
```

**Network troubleshooting (host network mode):**

```bash
docker run -d --network=host -v open-webui:/app/backend/data \
  -e OLLAMA_BASE_URL=http://127.0.0.1:11434 --name open-webui \
  --restart always ghcr.io/open-webui/open-webui:main
```

### Python pip

```bash
pip install open-webui
open-webui serve
```

Requires Python 3.11. Access at `http://localhost:8080`.

### Important

- Always include `-v open-webui:/app/backend/data` in Docker commands to persist data
- CUDA support requires the NVIDIA container runtime toolkit on Linux/WSL
- Set `HF_HUB_OFFLINE=1` for fully offline operation

## Ollama Connection

If Ollama is running on the host machine (not inside the container), Open WebUI reaches it via `host.docker.internal:11434` (handled by the `--add-host` flag). If auto-detection fails, configure it manually in **Settings > Connections** and set the Ollama URL to `http://host.docker.internal:11434`.

---

## Feature Overview

### LLM Integration

- **Ollama support** — connect to local or remote Ollama instances with model management (pull, delete, update all)
- **OpenAI-compatible APIs** — works with OpenAI, LM Studio, GroqCloud, Mistral, OpenRouter, and any compatible endpoint
- **Multiple Ollama instance load balancing** — distribute requests across instances, enhanced with optional Redis support
- **Concurrent model utilization** — engage multiple models simultaneously in a single conversation
- **@ model switching** — switch to any model mid-conversation using the `@` command
- **Model Builder** — create and edit custom Ollama models from the web UI, including GGUF file uploads
- **Model Playground (Beta)** — sandbox environment for testing model capabilities
- **Model presets** — create and manage parameter presets for Ollama and OpenAI APIs
- **Fine-tuned control** — adjust seed, temperature, frequency penalty, context length, and more per session

### Chat & Conversations

- **True asynchronous chat** — multitask while waiting; responses are ready when you return
- **Message queue** — compose follow-up messages while the AI is still generating
- **Chat folders & projects** — organize into folders with drag-and-drop; transform folders into project workspaces with custom system prompts and attached knowledge bases
- **Chat cloning** — snapshot any conversation for reference or branching
- **Pinned and archived chats** — keep important conversations accessible or store completed ones
- **Conversation tagging** — categorize and search with `tag:` queries, plus auto-tagging
- **Regeneration history** — explore the full history of regenerated responses
- **Temporary chat** — chat without saving history, with browser-side document processing
- **Import/export** — drag-and-drop JSON import; export as JSON, PDF, or TXT
- **Markdown and LaTeX** — full rendering support for rich text interactions
- **Shared chat management** — generate shareable links with centralized audit interface

### Retrieval-Augmented Generation (RAG)

- **Built-in RAG pipeline** — hybrid search with BM25 and CrossEncoder re-ranking
- **9 vector database backends** — ChromaDB, PostgreSQL/PGVector, Qdrant, Milvus, Elasticsearch, OpenSearch, Pinecone, S3Vector, Oracle 23ai
- **Document extraction** — PDFs, Word, Excel, PowerPoint via Apache Tika, Docling, Azure Document Intelligence, Mistral OCR
- **Web search integration** — 15+ providers including SearXNG, Google PSE, Brave Search, Kagi, Tavily, Perplexity
- **Agentic search** — sequential multi-step searches with `fetch_url` for deep research
- **Web browsing** — fetch and process URLs via `#` command or `fetch_url` tool
- **YouTube RAG** — summarize videos by pasting a URL (uses transcription)
- **Citations** — inline source references with relevance percentages
- **Configurable embedding models** — change embedding models directly from the Admin Panel
- **Full document vs snippet retrieval** — toggle between returning complete documents or chunked snippets

### Voice & Video

- **Voice input** — Local Whisper, OpenAI, Deepgram, Azure Speech Services
- **Text-to-speech** — OpenAI-compatible, Azure Speech, ElevenLabs, local Transformers, WebAPI
- **Hands-free voice calls** — initiate without manual activation
- **Video calls** — use vision models (LLaVA, GPT-4o) with camera feed
- **Tap/voice interrupt** — stop AI speech on mobile with a tap or by speaking
- **Customizable playback speed** — adjust TTS speed in call mode
- **Emoji call** — LLMs express emotions with emojis during voice calls

### Image Generation

- **Built-in image generation** — DALL-E, Gemini, ComfyUI, AUTOMATIC1111 support
- **Image editing** — native tool-calling integration
- **Multi-modal support** — engage models like LLaVA that accept image inputs

### Code Execution & Artifacts

- **Python code execution** — run Python directly in the browser via Pyodide
- **Live code editing** — edit code blocks in responses with live reloads
- **Interactive artifacts** — render HTML, SVGs, and web content directly in the interface
- **Mermaid diagrams** — create flowcharts and diagrams from code
- **Persistent artifact storage** — key-value storage API for journals, trackers, leaderboards across sessions

### Extensibility & Pipelines

- **Pipelines framework** — modular plugin system for custom logic with Python library integration
- **Native Python function calling** — write Python tools directly in the built-in code editor
- **Agentic mode** — system tools that enable multi-step research, knowledge base exploration, and autonomous memory management
- **Langfuse monitoring** — real-time analytics pipeline
- **Toxic message filtering** — Detoxify pipeline for content moderation
- **LLM-Guard** — prompt injection scanning and detection
- **User rate limiting** — control request flow to prevent rate limit breaches
- **LibreTranslate** — real-time cross-lingual translation pipeline

### Security & Access Control

- **Role-based access control (RBAC)** — granular permissions across the workspace
- **SCIM 2.0 provisioning** — enterprise user/group automation via Okta, Azure AD, Google Workspace
- **LDAP authentication** — Active Directory integration
- **OAuth management** — group-level control with multi-device session support
- **Encrypted database** — SQLCipher encryption for SQLite
- **Model whitelisting** — restrict users to authorized models only
- **API key management** — secure credential handling with endpoint restrictions
- **Backend reverse proxy** — enhanced security for Ollama communication

### Administration

- **Admin panel** — user management with pagination and bulk CSV import
- **Analytics dashboard** — usage insights: message volume, token consumption, user activity, model performance
- **Active users indicator** — monitor who's online and which models are in use
- **Configurable banners** — custom notification banners (info/warning/error/success) with Markdown
- **Webhook integration** — sign-up event notifications for Discord, Google Chat, Slack, Microsoft Teams
- **Horizontal scalability** — Redis-backed session management with WebSocket support for production
- **OpenTelemetry observability** — export traces, metrics, and logs via OTLP

### File & Storage

- **Centralized file management** — unified dashboard for document search, viewing, and management
- **Cloud storage** — Amazon S3, Google Cloud Storage, Microsoft Azure Blob Storage
- **Enterprise cloud integration** — Google Drive and OneDrive/SharePoint file picker import
- **Portable configuration** — import/export settings to replicate across instances

### User Experience

- **ChatGPT-inspired interface** — intuitive, responsive design
- **Progressive Web App** — native PWA for mobile with offline localhost access
- **Theme customization** — Light, Dark, OLED modes with custom chat backgrounds
- **Prompt presets** — access via `/` command with template variables (`{{CURRENT_DATE}}`, `{{USER_NAME}}`, etc.)
- **Text select quick actions** — floating buttons on highlighted text for "Ask a Question" or "Explain"
- **Multilingual** — internationalization (i18n) with community translations
- **Keyboard navigation** — arrow key model selection, shift+key shortcuts in workspace

### Collaboration

- **Channels (Beta)** — Discord/Slack-style real-time group conversations with bot support and typing indicators
- **Model evaluation arena** — blind A/B testing for side-by-side model comparison with ELO ratings
- **RLHF annotation** — rate responses with thumbs up/down, 1-10 scale, and textual feedback; export as JSON
- **Community sharing** — share sessions with the Open WebUI community
- **Memory (Experimental)** — LLM-remembered user information with `add_memory`, `search_memories`, `replace_memory_content` tools
