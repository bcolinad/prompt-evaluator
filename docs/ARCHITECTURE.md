# Architecture Documentation

> **⚠️ KEEP THIS FILE UPDATED**: Any time a component, module, database table, node, or feature is added, modified, or removed — this file MUST be updated. See [Documentation Update Rules](#documentation-update-rules).

---

## Diagrams

All diagrams are stored in `docs/diagrams/` and designed for direct paste into their respective platforms:

| Diagram | File | Platform | What It Shows |
|---------|------|----------|---------------|
| System Architecture | `architecture.eraser` | [eraser.io](https://app.eraser.io) | Full system overview — UI, agent, LLMs, DB, observability |
| LangGraph Workflow | `langgraph-workflow.eraser` | [eraser.io](https://app.eraser.io) | Agent graph topology — nodes, edges, conditional routing |
| Data Flow | `data-flow.eraser` | [eraser.io](https://app.eraser.io) | How data moves through the evaluation pipeline |
| Component Diagram | `component-diagram.eraser` | [eraser.io](https://app.eraser.io) | Module dependencies and internal wiring |
| Database Schema | `database.dbml` | [dbdiagram.io](https://dbdiagram.io) | Tables, columns, indexes, JSON schemas |

### How to View

1. **Eraser.io diagrams**: Go to [app.eraser.io](https://app.eraser.io), create a new diagram, paste the contents of any `.eraser` file
2. **Database diagram**: Go to [dbdiagram.io/d](https://dbdiagram.io/d), paste the contents of `database.dbml`

---

## System Overview

```
┌──────────────────────────────────────────────────────────┐
│                   Chainlit Chat UI                        │
│             (src/app.py — port 8000)                      │
└──────────────────┬───────────────────────────────────────┘
                   │ User messages + session
                   ▼
┌──────────────────────────────────────────────────────────┐
│               LangGraph StateGraph                        │
│                 (src/agent/graph.py)                       │
│                                                            │
│  ┌─────────┐   ┌───────────┐   ┌──────────────────┐      │
│  │ Route   │──▶│ Analyze   │──▶│ Score            │      │
│  │ Input   │   │ (CoT)     │   │ (weighted calc)  │      │
│  └─────────┘   └───────────┘   └────────┬─────────┘      │
│       │                                  │                │
│       │         (Full mode)              ▼                │
│       │        ┌─────────────────────┐                    │
│       │        │ Run Prompt Nx       │──▶ LangSmith trace │
│       │        │ (concurrent)        │                    │
│       │        └──────────┬──────────┘                    │
│       │                   ▼                               │
│       │        ┌─────────────────────┐                    │
│       │        │ Evaluate Output     │──▶ LangSmith score │
│       │        │ (LLM-as-Judge)      │                    │
│       │        └──────────┬──────────┘                    │
│       │                   ▼                               │
│       │        ┌───────────────────────────────────┐      │
│       │        │ Generate Improvements (ToT)       │      │
│       │        │ → multi-branch exploration        │      │
│       │        │ → select/synthesize best           │      │
│       │        └──────────┬────────────────────────┘      │
│       │                   ▼                               │
│       │        ┌─────────────────────┐                    │
│       │        │ Run Optimized Nx    │                    │
│       │        │ (concurrent)        │                    │
│       │        └──────────┬──────────┘                    │
│       │                   ▼                               │
│       │        ┌─────────────────────┐                    │
│       │        │ Evaluate Optimized  │                    │
│       │        │ (quality comparison)│                    │
│       │        └──────────┬──────────┘                    │
│       │                   ▼                               │
│       │        ┌─────────────────────┐                    │
│       │        │ Meta-Evaluate       │ (always)           │
│       │        │ (self-assessment)   │                    │
│       │        └──────────┬──────────┘                    │
│       │                   ▼                               │
│       │        ┌─────────────────────┐                    │
│       │        │ Build Report        │                    │
│       │        │ (merge all results) │                    │
│       │        └──────────┬──────────┘                    │
│       │                   ▼                               │
│       │        ┌───────────────────────────────────┐      │
│       └────────│ Conversation Loop (follow-ups)    │      │
│                └───────────────────────────────────┘      │
└──────────┬────────────────┬────────────────┬─────────────┘
           │                │                │
    ┌──────▼──────┐  ┌──────────────────────────┐
    │ PostgreSQL  │  │  LangSmith               │
    │ (history)   │  │  (traces + feedback)     │
    └─────────────┘  └──────────────────────────┘
```

---

## Module Reference

### `src/app.py` — Chainlit Entry Point (Orchestrator)
- Slim orchestrator (~450 lines) — delegates logic to `src/ui/` modules
- `get_data_layer()` — `@cl.data_layer` decorator configures `CustomDataLayer` with `LocalStorageClient`
- `auth_callback` — `@cl.password_auth_callback` for password-based authentication
- `chat_profiles()` — `@cl.set_chat_profiles` defines 6 evaluator profiles + 1 chat profile
- `_init_session_common()` — Shared setup: user ID, LLM label strings, label-to-key mapping
- `_send_settings_widget()` — Sends `ChatSettings` Select widget, swallowing errors
- `_init_chat_mode(profile_name)` — Sets up chat session (provider, history, welcome message)
- `_init_evaluator_mode(profile_name)` — Sets up evaluator session (task type, welcome message with `_WELCOME_MESSAGES` dict lookup)
- `on_chat_start` — Delegates to `_init_chat_mode()` or `_init_evaluator_mode()` + thread naming
- `on_chat_resume` — Restores session state for resumed threads
- `on_settings_update` — Routes LLM provider selection by `profile_mode`
- `on_audio_start/chunk/end` — Audio recording handlers, delegates transcription to `transcribe_audio()`
- `on_message` — Routes to `_handle_chat_message()` or `_run_evaluation()` by `profile_mode`
- `_process_document_attachments()` — Processes uploaded document files through the document pipeline (load → extract → chunk → vectorize → store)
- `_get_document_context_for_chat()` — Retrieves relevant document context via RAG for use in chat and evaluation
- Session stores `document_ids` for tracking uploaded documents per session
- **Depends on**: `ui.*`, `agent.graph`, `evaluator`, `evaluator.example_prompts`, `utils.example_formatter`, `config`, `documents`

### `src/ui/` — UI Helper Modules (extracted from app.py)

| File | Purpose |
|------|---------|
| `profiles.py` | `_PROFILE_TO_TASK_TYPE` mapping, `_CHAT_PROFILE_NAME`, `_WELCOME_MESSAGES` dict (TaskType → welcome text), `_DEFAULT_WELCOME`, file extension constants (`_TEXT_FILE_EXTENSIONS`, `_IMAGE_EXTENSIONS`, `_DOCUMENT_EXTENSIONS`, `_MAX_TEXT_FILE_SIZE`, `_MAX_DOCUMENT_SIZE`) |
| `thread_utils.py` | `increment_chat_counter()` for unique thread numbering, `_set_thread_name()` for conversation history sidebar |
| `chat_handler.py` | `_handle_chat_message()` with live streaming, `_get_chat_llm()` provider factory, `_extract_thinking_and_text()`, `_extract_chunk_deltas()`, `_process_attachments()` returns 3-tuple (text, images, documents) for text files + images + document files |
| `evaluation_runner.py` | `_run_evaluation()` streams LangGraph with progress bar, `NODE_STEP_MAP` weights, `_extract_step_summary()` via `_STEP_EXTRACTORS` dispatch dict, `_progress_bar()` |
| `results_display.py` | `_send_results()` generates audit report HTML + sends as `cl.File`, `_send_recommendations()` shows similar past evaluations |
| `audio_handler.py` | `transcribe_audio()` converts audio to text via Google Gemini (PCM16→WAV conversion) |

### `src/agent/graph.py` — LangGraph Workflow
- Defines the `StateGraph` with all nodes and edges
- Conditional routing: `_route_by_phase()` → STRUCTURE/FULL → analyzer, OUTPUT → output runner
- Conditional routing: `_after_improvements()` → `run_optimized_prompt` (when `rewritten_prompt` exists) or `meta_evaluate` (when no rewritten prompt)
- Conditional routing: `_after_optimized_runner()` → `evaluate_optimized_output`
- Conditional routing: `_after_optimized_eval()` → `meta_evaluate`
- Conditional routing: `_after_meta_evaluate()` → `build_report` or END on fatal error
- Conditional continuation: `_should_continue()` → follow-up or end
- Exports `evaluator_graph` (compiled graph)
- **Depends on**: `agent.nodes.*`, `agent.state`

### `src/agent/state.py` — State Schema
- `AgentState(TypedDict)` — all fields passed between nodes
- Uses `add_messages` reducer for conversation history
- **Key fields**: `input_text`, `mode`, `eval_phase`, `prompt_type`, `task_type`, `dimension_scores`, `overall_score`, `evaluation_result`, `llm_output`, `output_evaluation`, `full_report`, `should_continue`, `followup_action`, `chunk_count`, `user_id`, `thread_id`, `similar_evaluations`, `llm_provider`, `strategy`, `meta_assessment`, `meta_findings`, `execution_count`, `original_outputs`, `original_output_summary`, `optimized_outputs`, `optimized_output_summary`, `optimized_output_evaluation`, `cot_reasoning_trace`, `tot_branches_data`
- `task_type: TaskType` — Set by Chainlit UI action buttons; defaults to `GENERAL`. Determines which criteria set, prompts, and eval config to use throughout the pipeline
- `execution_count: int` — Number of times to execute each prompt (default 2, range 2-5)
- `cot_reasoning_trace: str | None` — Captured Chain-of-Thought reasoning from analysis
- `tot_branches_data: ToTBranchesAuditData | None` — Tree-of-Thought exploration audit trail
- `document_context: str | None` — RAG context retrieved from uploaded documents (injected before graph invocation)
- `document_ids: list[str] | None` — IDs of documents uploaded in the current session
- `document_summary: str | None` — Summary of uploaded document content for context

### `src/agent/nodes/` — Graph Nodes

| Node | File | Purpose | LLM Call? |
|------|------|---------|-----------|
| `route_input` | `router.py` | Detect eval mode from input text; classify prompt as `initial` or `continuation` via heuristic signals | No |
| `analyze_prompt` | `analyzer.py` | Evaluate prompt against T.C.R.E.I. criteria with always-on CoT reasoning. Reads `task_type` from state to select task-specific analysis prompt and criteria. Retrieves similar past evaluations via embeddings. Returns `cot_reasoning_trace` | Yes |
| `analyze_system_prompt` | `analyzer.py` | Evaluate system prompt + expected outcome with always-on CoT reasoning | Yes |
| `score_prompt` | `scorer.py` | Compute weighted overall score and grade. Passes `task_type` to `load_eval_config()` to load correct dimension weights (e.g., `email_writing_eval_config.yaml` for email tasks) | No |
| `generate_improvements` | `improver.py` | Always uses Tree-of-Thought: generates multiple improvement branches, selects/synthesizes the best, builds `EvaluationResult`. Returns `tot_branches_data` audit trail. Falls back to standard single-shot if ToT fails. Context-aware: preserves continuation markers for continuation prompts. Appends task-specific improvement guidance per `task_type` | Yes |
| `run_prompt_for_output` | `output_runner.py` | Execute the prompt N times concurrently via `asyncio.gather()`. Returns `original_outputs` list and `original_output_summary`. Handles partial failures gracefully | Yes |
| `evaluate_output` | `output_evaluator.py` | Score LLM output using LLM-as-Judge with LangSmith feedback; uses `invoke_structured()` with per-dimension recommendations. Selects task-specific output evaluation prompt based on `task_type` | Yes |
| `run_optimized_prompt` | `optimized_runner.py` | Execute the rewritten prompt N times concurrently. Returns `optimized_outputs` and `optimized_output_summary`. Skips gracefully if no `rewritten_prompt` exists | Yes |
| `evaluate_optimized_output` | `output_evaluator.py` | Score the optimized prompt output using `_evaluate_output_common()` shared helper. Returns `optimized_output_evaluation`. Skips if no optimized output | Yes |
| `build_report` | `report_builder.py` | Merge structure + output + optimized output evaluations, CoT trace, ToT branches, and meta-assessment into a `FullEvaluationReport` | No (but stores embeddings) |
| `meta_evaluate` | `meta_evaluator.py` | Self-assessment of evaluation quality — scores accuracy, completeness, actionability, faithfulness, and overall confidence. Always runs (no conditional) | Yes |
| `handle_followup` | `conversational.py` | Process follow-up questions (explain, adjust, re-evaluate, mode switch) | Yes |

### `src/evaluator/` — Core Models & Criteria

| File | Contents |
|------|----------|
| `__init__.py` | Pydantic domain models: `EvaluationResult`, `DimensionScore`, `Improvement`, `TCREIFlags`, `EvaluationInput`, `EvalPhase`, `OutputDimensionScore` (with `recommendation` field), `OutputEvaluationResult`, `FullEvaluationReport` (with `optimized_output_result`, `execution_count`, `original_outputs`, `optimized_outputs`, `cot_reasoning_trace`, `tot_branches_data`), `ToTBranchAuditEntry`, `ToTBranchesAuditData`, `TaskType` enum (`GENERAL`, `EMAIL_WRITING`, `SUMMARIZATION`, `CODING_TASK`, `EXAM_INTERVIEW`, `LINKEDIN_POST`) |
| `criteria/` | Package with per-task-type criterion definitions. `__init__.py` re-exports all constants and provides `_CRITERIA_REGISTRY` dict + `get_criteria_for_task_type()`. Sub-modules: `base.py` (Criterion dataclass), `general.py`, `email.py`, `summarization.py`, `coding.py`, `exam.py`, `linkedin.py` — each defines 4 dimension criteria dicts |
| `example_prompts.py` | Annotated example prompts with T.C.R.E.I. breakdowns per task type. Dataclasses: `ExamplePrompt` (title, full_prompt, overall_description, sections, estimated_score), `AnnotatedSection` (dimension, label, text, explanation). Registry: `EXAMPLE_PROMPTS` dict keyed by `TaskType`. Accessor: `get_example_for_task_type(task_type)`. Five examples: General (veterinarian blog), Email (professional follow-up), Summarization (research paper executive summary), Coding (REST API endpoint in Python), Exam (technical interview assessment for backend engineers) |
| `exceptions.py` | Custom exception hierarchy: `EvaluatorError` (base with optional `context` dict), `LLMError`, `AnalysisError`, `ScoringError`, `ImprovementError`, `OutputEvaluationError`, `ReportBuildError`, `ConfigurationError`, `OllamaConnectionError`, `OllamaModelNotFoundError`. Fatal error detection: `is_fatal_llm_error()`, `format_fatal_error()` with Ollama-specific patterns (model not found, connection refused) |
| `llm_schemas.py` | Pydantic LLM response schemas (separate from domain models): `AnalysisLLMResponse`, `ImprovementsLLMResponse`, `OutputEvaluationLLMResponse` (with `recommendation` field), `FollowupLLMResponse` — used with `with_structured_output()` |
| `strategies.py` | Evaluation strategy presets: `EvaluationStrategy` enum (STANDARD, ENHANCED, COT_ONLY, TOT_ONLY, META_ONLY), `StrategyConfig` Pydantic model (`use_cot`, `use_tot`, `use_meta` flags + `label`), `resolve_strategy()` factory function, `get_default_strategy()` returns always-enhanced config |
| `service.py` | High-level `PromptEvaluationService` orchestrator: `EvaluationReport` dataclass (full_report, overall_score, grade, strategy_used, meta_assessment, optimized_output_evaluation, error), `PromptEvaluationService` class with `async evaluate()` that always uses `get_default_strategy()`, accepts `execution_count`, constructs initial state, invokes `get_graph().astream()`, and returns a clean `EvaluationReport` |

### `src/prompts/` — LLM Prompt Templates (package)

Split into per-task-type sub-modules (`general.py`, `email.py`, `summarization.py`, `coding.py`, `exam.py`, `linkedin.py`). The `__init__.py` re-exports all constants.

| Template | Defined In | Purpose |
|----------|-----------|---------|
| `ANALYSIS_SYSTEM_PROMPT` | `general.py` | Evaluate prompt dimensions, return structured JSON |
| `SYSTEM_PROMPT_ANALYSIS_TEMPLATE` | `general.py` | Evaluate system prompts with outcome alignment |
| `IMPROVEMENT_SYSTEM_PROMPT` | `general.py` | Generate prioritized improvements + context-aware rewrite |
| `PROMPT_TYPE_INITIAL` / `PROMPT_TYPE_CONTINUATION` | `general.py` | Guidance for rewriting initial vs continuation prompts |
| `FOLLOWUP_SYSTEM_PROMPT` | `general.py` | Classify follow-up intent + generate contextual response |
| `OUTPUT_EVALUATION_SYSTEM_PROMPT` | `general.py` | LLM-as-Judge scoring of output quality across 5 dimensions |
| `EMAIL_*` | `email.py` | Email-specific analysis, output evaluation, improvement guidance |
| `SUMMARIZATION_*` | `summarization.py` | Summarization-specific analysis, output evaluation, improvement guidance |
| `CODING_*` | `coding.py` | Coding-specific analysis, output evaluation, improvement guidance |
| `EXAM_*` | `exam.py` | Exam/interview-specific analysis, output evaluation, improvement guidance |
| `LINKEDIN_*` | `linkedin.py` | LinkedIn-specific analysis, output evaluation, improvement guidance |
| `COT_*` | `strategies/cot.py` | Chain-of-Thought reasoning prompts for deeper analysis |
| `TOT_*` | `strategies/tot.py` | Tree-of-Thought branching prompts for improvement generation |
| `META_*` | `strategies/meta.py` | Meta-evaluation self-assessment prompts |

### `src/prompts/registry.py` — Task-Type Prompt Registry
- `TaskTypePrompts` frozen dataclass: `analysis`, `output_evaluation`, `improvement_guidance`, `fallback_dimensions`
- `_REGISTRY` dict mapping task type strings to `TaskTypePrompts` — eliminates elif chains in agent nodes
- `get_prompts_for_task_type(task_type)` — single lookup, falls back to `"general"`
- Used by `analyzer.py`, `improver.py`, `output_evaluator.py` for prompt and fallback dimension selection

### `src/config/` — Configuration

| File | Purpose |
|------|---------|
| `__init__.py` | `Settings` class (Pydantic Settings) — loads from `.env` with `lru_cache` singleton. `LLMProvider` enum: `GOOGLE`, `ANTHROPIC`, `OLLAMA`. Includes `app_env`, `log_level`, `llm_provider` (`GOOGLE` default), `google_model`, `google_project`, `google_location`, `anthropic_api_key`, `anthropic_model`, `ollama_chat_model` (`qwen3:4b`), `ollama_num_predict` (16384), `ollama_request_timeout` (120.0), `ollama_base_url`, `llm_temperature`, `llm_max_tokens`, `embedding_model`, `embedding_dimensions`, `similarity_threshold`, `max_similar_results`, `auth_enabled`, `auth_secret_key`, `auth_admin_email`, `auth_admin_password`, `default_execution_count` (2, range 2-5). Document processing settings: `doc_max_file_size`, `doc_chunk_size`, `doc_chunk_overlap`, `doc_max_chunks_per_query`, `doc_enable_extraction`, `doc_extraction_model`. PDF OCR settings: `pdf_ocr_enabled` (default true), `pdf_ocr_min_text_chars` (default 50) |
| `eval_config.py` | `EvalConfig` — loads YAML, computes scores, assigns grades |
| `defaults/eval_config.yaml` | Default dimension weights and grading scale |
| `defaults/email_writing_eval_config.yaml` | Email Creation Prompts dimension weights: task 0.30, context 0.30, references 0.15, constraints 0.25 |
| `defaults/summarization_eval_config.yaml` | Summarization Prompts dimension weights: task 0.25, context 0.25, references 0.30, constraints 0.20 |
| `defaults/coding_task_eval_config.yaml` | Coding Task Prompts dimension weights: task 0.30, context 0.25, references 0.20, constraints 0.25 |
| `defaults/exam_interview_eval_config.yaml` | Exam Interview Agent Prompts dimension weights: task 0.30, context 0.25, references 0.20, constraints 0.25 |
| `defaults/linkedin_post_eval_config.yaml` | LinkedIn Professional Post Prompts dimension weights: task 0.25, context 0.35, references 0.15, constraints 0.25 |
| `defaults/domains/healthcare.yaml` | Healthcare-specific terminology and constraints |

### `src/db/` — Database Layer

| File | Purpose |
|------|---------|
| `__init__.py` | Async SQLAlchemy engine + session factory with thread-safe double-checked locking. Exports `get_engine()`, `get_session_factory()`, `get_session()`, `dispose_engine()`. Auto-commits on success, rolls back on exception |
| `models.py` | ORM models: `Evaluation` (with `thread_id`), `EvalConfig`, `ConversationEmbedding` (with pgvector `Vector(768)` and `thread_id`), `Document` (uploaded document metadata + extracted text), `DocumentChunkRecord` (vectorized document chunks with pgvector HNSW index) |
| `repository.py` | `EvaluationRepository`, `ConfigRepository`, `DocumentRepository` — CRUD operations |

### `src/rag/` — RAG Pipeline

| File | Purpose |
|------|---------|
| `knowledge_store.py` | In-memory vector store built from knowledge docs, criteria, and domain configs. Uses `OllamaEmbeddings` (self-hosted via Ollama). Exposes `retrieve_context(query, top_k=3) -> str` for grounding LLM evaluations with T.C.R.E.I. reference material. Chunked with `RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)`. Singleton via `@lru_cache`. |

### `src/knowledge/` — Knowledge Base

| File | Purpose |
|------|---------|
| `tcrei_framework.md` | T.C.R.E.I. framework reference — what makes strong Task/Context/References/Constraints/Iterate, common weaknesses, scoring guidance per dimension |
| `scoring_guide.md` | Scoring rubrics with grading scale, dimension weights, detailed score range examples (0-20 through 81-100), and full example prompt evaluations at each grade level |

### `src/utils/` — Utility Modules

| File | Purpose |
|------|---------|
| `example_formatter.py` | Markdown formatter for example prompts with T.C.R.E.I. breakdowns. `format_example_markdown(example: ExamplePrompt) -> str` produces pure Markdown (no HTML) with title, code block, dimension prefixes ([T], [C], [R], [E/I]), blockquoted excerpts, italic explanations, and call-to-action footer. Compatible with Chainlit's `unsafe_allow_html = false` |
| `llm_factory.py` | Centralized LLM provider factory with three-provider cascade. Tries Google Gemini (`ChatGoogleGenerativeAI` via Vertex AI) first, falls back to Anthropic Claude (`ChatAnthropic`), then Ollama (`ChatOllama`). Raises `RuntimeError` with setup instructions if all three fail |
| `langsmith_utils.py` | LangSmith client initialization and run feedback scoring helpers |
| `structured_output.py` | `invoke_structured(llm, prompt, variables, schema)` helper — tries `with_structured_output()` first, falls back to raw invocation + JSON extraction + `model_validate()`, returns `None` on total failure. Includes `_is_ollama_model()` detector for future Ollama-specific routing |
| `chunking.py` | Adaptive chunking for long, multi-section prompts. `should_chunk()` gates on 2000+ token estimate. `detect_sections()` finds markdown headers and XML tags. `chunk_prompt()` splits at boundaries with paragraph fallback. `aggregate_dimension_scores()` uses token-weighted averaging and OR-merge for flags. |
| `report_generator.py` | Professional Audit HTML report generator — builds self-contained dashboard with CSS Grid accordion, client-side JSON rendering via placeholder injection, XSS-protected data serialization. Includes word-level prompt comparison diff via `generate_diff_html()` using `difflib.SequenceMatcher` (green additions, red strikethrough deletions). Also provides `generate_similarity_report()` for lightweight HTML reports of similar past evaluations (score badge, grade, original prompt, improvements, optimized prompt with copy button) |
| `local_storage.py` | Local filesystem storage client for Chainlit file uploads — implements `BaseStorageClient` using `aiofiles`, registered via `@cl.data_layer` to eliminate "No storage client configured" warning |
| `custom_data_layer.py` | `CustomDataLayer` — extends `ChainlitDataLayer` to clean up app-owned tables (`evaluations`, `conversation_embeddings`, `documents`, `document_chunks`) when a Chainlit thread is deleted from the sidebar. Overrides `delete_thread()` to DELETE matching rows by `thread_id` before calling parent. Graceful: logs warning and proceeds if app cleanup fails |
| `logging_config.py` | Centralized logging configuration via `setup_logging(level, environment)`. Dev mode uses human-readable format, staging/production uses structured JSON-like format. Silences noisy third-party loggers (httpx, httpcore, sqlalchemy, langchain, ollama, anthropic) to WARNING level |

### `src/embeddings/` — Embedding Service

| File | Purpose |
|------|---------|
| `__init__.py` | Module init |
| `service.py` | `generate_embedding()` via `OllamaEmbeddings` (self-hosted `nomic-embed-text`, 768 dimensions). `store_evaluation_embedding()` to persist vectorized evaluations with combined summary text and optional `thread_id` for cleanup. `find_similar_evaluations()` for pgvector cosine similarity search using SQLAlchemy ORM `cosine_distance()` method with configurable threshold and limit. `_build_summary_text()` combines prompt, score, quality, improvements, and rewrite into embeddable text. |

### `src/documents/` — Document Processing Pipeline

| File | Purpose |
|------|---------|
| `__init__.py` | Public API exports |
| `models.py` | Pydantic models: `DocumentMetadata` (file metadata), `DocumentChunk` (text chunk with embedding), `ExtractionEntity` (structured entity extracted by LLM), `ProcessingResult` (full pipeline output) |
| `loader.py` | File format loaders using LangChain: `PyPDFLoader` for PDF (with tiered OCR fallback: pypdf → pdfplumber → PyMuPDF OCR), `Docx2txtLoader` for DOCX, `openpyxl` for XLSX, `python-pptx` for PPTX. Returns raw text + metadata. PDF loader returns extra metadata (`pdf_extraction_method`, `pdf_ocr_applied`, `pdf_tiers_attempted`) |
| `extractor.py` | LLM-based entity extraction: takes raw document text and produces structured `ExtractionEntity` objects. Configurable via `DOC_ENABLE_EXTRACTION` and `DOC_EXTRACTION_MODEL` settings |
| `chunker.py` | Document-specific text chunking using `RecursiveCharacterTextSplitter`. Chunk size and overlap configurable via `DOC_CHUNK_SIZE` and `DOC_CHUNK_OVERLAP` settings |
| `vectorizer.py` | Generates Ollama embeddings for document chunks and stores them in PostgreSQL with pgvector (HNSW indexed) |
| `retriever.py` | Document RAG retriever: cosine similarity search on `document_chunks` table via pgvector. Returns top-K relevant chunks for a query. Configurable via `DOC_MAX_CHUNKS_PER_QUERY` |
| `processor.py` | Orchestrator: coordinates the full pipeline — load → extract → chunk → vectorize → store. Called from `src/app.py` when document attachments are detected |
| `exceptions.py` | Custom exceptions: `DocumentProcessingError` (base), `UnsupportedFormatError` (unsupported file type) |

---

## Database Schema

### `evaluations` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `session_id` | VARCHAR(255) | Groups evaluations per chat session |
| `thread_id` | VARCHAR(255) (nullable) | Chainlit thread ID — enables cleanup on thread deletion |
| `mode` | VARCHAR(50) | `"prompt"` or `"system_prompt"` |
| `input_text` | TEXT | The prompt being evaluated |
| `expected_outcome` | TEXT (nullable) | For system prompt mode |
| `overall_score` | INTEGER (0-100) | Weighted overall score |
| `grade` | VARCHAR(20) | Excellent / Good / Needs Work / Weak |
| `task_score` | INTEGER (0-100) | Task dimension score |
| `context_score` | INTEGER (0-100) | Context dimension score |
| `references_score` | INTEGER (0-100) | References dimension score |
| `constraints_score` | INTEGER (0-100) | Constraints dimension score |
| `analysis` | JSONB | Full dimension analysis with sub-criteria |
| `improvements` | JSONB | Prioritized improvement list |
| `rewritten_prompt` | TEXT (nullable) | AI-generated improved version |
| `config_snapshot` | JSONB (nullable) | Config used at eval time |
| `eval_phase` | VARCHAR(20) (nullable) | Evaluation phase: `"structure"`, `"output"`, or `"full"` |
| `llm_output` | TEXT (nullable) | Raw LLM output captured during output evaluation |
| `output_evaluation` | JSONB (nullable) | Full output evaluation result with dimension scores |
| `langsmith_run_id` | VARCHAR(255) (nullable) | LangSmith run ID for output evaluation feedback scoring |
| `created_at` | TIMESTAMPTZ | Auto-set |

**Indexes**: `session_id`, `thread_id`, `created_at DESC`, `grade`, `(session_id, created_at)`

### `eval_configs` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `name` | VARCHAR(255) UNIQUE | Config name (e.g., "default", "healthcare") |
| `description` | TEXT (nullable) | What this config is for |
| `config` | JSONB | Dimensions, weights, sub_criteria, grading_scale |
| `is_default` | BOOLEAN | Active default flag |
| `created_at` | TIMESTAMPTZ | Auto-set |
| `updated_at` | TIMESTAMPTZ | Auto-updated |

### `conversation_embeddings` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `user_id` | UUID (FK → User) | Owner of the evaluation |
| `thread_id` | VARCHAR(255) (nullable) | Chainlit thread ID — enables cleanup on thread deletion |
| `evaluation_id` | UUID (FK → evaluations) | Linked evaluation record |
| `input_text` | TEXT | The original prompt |
| `rewritten_prompt` | TEXT (nullable) | AI-generated improved version |
| `overall_score` | INTEGER (0-100) | Weighted overall score |
| `grade` | VARCHAR(20) | Excellent / Good / Needs Work / Weak |
| `output_score` | DOUBLE PRECISION (nullable) | Output quality score (0.0-1.0) |
| `improvements_summary` | TEXT (nullable) | Summary of suggested improvements |
| `embedding` | vector(768) | Ollama nomic-embed-text vector |
| `metadata` | JSONB | Additional metadata |
| `created_at` | TIMESTAMPTZ | Auto-set |

**Indexes**: `user_id`, `thread_id`, `evaluation_id`, IVFFlat on `embedding` (cosine ops, lists=100)

### `documents` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `thread_id` | VARCHAR(255) (nullable) | Chainlit thread ID — enables cleanup on thread deletion |
| `filename` | VARCHAR(255) | Original uploaded filename |
| `content_type` | VARCHAR(100) | MIME type of the uploaded file |
| `file_size` | INTEGER | File size in bytes |
| `extracted_text` | TEXT | Full text extracted from the document |
| `metadata` | JSONB | Additional document metadata (page count, author, etc.) |
| `created_at` | TIMESTAMPTZ | Auto-set |

**Indexes**: `thread_id`, `created_at DESC`

### `document_chunks` Table

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID (PK) | Auto-generated |
| `document_id` | UUID (FK → documents) | Parent document reference |
| `chunk_index` | INTEGER | Position of chunk within the document |
| `content` | TEXT | Chunk text content |
| `embedding` | vector(768) | Ollama nomic-embed-text vector |
| `metadata` | JSONB | Chunk-level metadata (page number, section, etc.) |
| `created_at` | TIMESTAMPTZ | Auto-set |

**Indexes**: `document_id`, HNSW on `embedding` (cosine ops)

> **Full DBML schema**: see `docs/diagrams/database.dbml`

---

## Evaluation Framework

### T.C.R.E.I. Dimensions

| Dimension | Weight | Sub-Criteria |
|-----------|--------|-------------|
| **Task** | 30% | `clear_action_verb` (25%), `specific_deliverable` (30%), `persona_defined` (25%), `output_format_specified` (20%) |
| **Context** | 25% | `background_provided` (25%), `audience_defined` (25%), `goals_stated` (25%), `domain_specificity` (25%) |
| **References** | 20% | `examples_included` (40%), `structured_references` (30%), `reference_labeling` (30%) |
| **Constraints** | 25% | `scope_boundaries` (25%), `format_constraints` (25%), `length_limits` (25%), `exclusions_defined` (25%) |

### Email Creation Prompts Criteria

When `task_type` is `EMAIL_WRITING`, email-specific sub-criteria replace the general ones. Loaded via `get_criteria_for_task_type(TaskType.EMAIL_WRITING)`.

| Dimension | Weight | Email-Specific Sub-Criteria |
|-----------|--------|-----------------------------|
| **Task** | 30% | `clear_email_purpose` — States the email's objective (inform, request, follow-up, etc.); `specific_desired_outcome` — Defines what the recipient should do/know; `sender_role_defined` — Identifies the sender's role/relationship; `email_format_specified` — Specifies tone, length, or structure expectations |
| **Context** | 30% | `recipient_defined` — Identifies the audience (individual, team, external client); `relationship_context` — Clarifies sender-recipient dynamic; `situation_background` — Provides the triggering event or reason; `communication_history` — References prior exchanges or shared context |
| **References** | 15% | `supporting_data_included` — Attaches relevant facts, figures, or documents; `example_emails_provided` — Includes sample emails or templates; `reference_labeling` — Labels and organizes attached materials |
| **Constraints** | 25% | `tone_constraints` — Specifies formality level (formal, casual, diplomatic); `length_limits` — Sets word/paragraph limits; `content_boundaries` — Defines what to include and exclude; `timing_requirements` — Urgency level or send-by deadline |

Config: `defaults/email_writing_eval_config.yaml` — task: 0.30, context: 0.30, references: 0.15, constraints: 0.25

### Summarization Prompts Criteria

When `task_type` is `SUMMARIZATION`, summarization-specific sub-criteria replace the general ones. Loaded via `get_criteria_for_task_type(TaskType.SUMMARIZATION)`.

| Dimension | Weight | Summarization-Specific Sub-Criteria |
|-----------|--------|-------------------------------------|
| **Task** | 25% | `content_scope_specified` — Specifies WHICH content to summarize (portion, sub-topic, or entire source); `format_and_tone_defined` — Desired format (bullet points, paragraph, table) AND tone/reading level; `output_length_specified` — Word count, sentence count, or reduction ratio; `persona_or_reading_level` — Persona or target reading level (e.g., "9th grade reading level") |
| **Context** | 25% | `source_document_described` — Document type, title, subject, length; `audience_for_summary` — Who reads the summary and their expertise; `summary_purpose` — What the summary is for, anchoring to something tangible; `domain_specificity` — Industry terms, specialized context |
| **References** | 30% | `source_material_provided` — Source text included or referenced; `example_summary_with_source` — Example summary paired with the document it summarizes; `key_sections_identified` — Which parts to focus on or prioritize |
| **Constraints** | 20% | `length_word_limits` — Hard length constraints; `inclusion_requirements` — Key findings that must be included; `hallucination_safeguards` — Instructions to prevent hallucinations/misinterpretations from large inputs; `exclusion_constraints` — Sections or details to omit |

Config: `defaults/summarization_eval_config.yaml` — task: 0.25, context: 0.25, references: 0.30, constraints: 0.20

### Coding Task Prompts Criteria

When `task_type` is `CODING_TASK`, coding-specific sub-criteria replace the general ones. Loaded via `get_criteria_for_task_type(TaskType.CODING_TASK)`.

| Dimension | Weight | Coding-Specific Sub-Criteria |
|-----------|--------|------------------------------|
| **Task** | 30% | `programming_language_specified` — Specifies the programming language, framework, and version; `requirements_clarity` — Defines functional requirements with input/output specifications; `architecture_guidance` — Provides design patterns, module structure, or component architecture; `code_quality_standards` — Specifies coding style, naming conventions, and documentation expectations |
| **Context** | 25% | `project_context_provided` — Describes the project type, purpose, and broader system; `technical_constraints_specified` — Identifies runtime environment, dependencies, and platform limitations; `target_developer_audience` — Specifies the experience level and skill set of the intended developer; `existing_codebase_context` — References existing code, APIs, or interfaces that must be integrated |
| **References** | 20% | `code_examples_provided` — Includes sample code, snippets, or pseudocode; `api_documentation_referenced` — References API docs, library documentation, or specifications; `test_expectations_defined` — Specifies testing requirements, test cases, or coverage expectations |
| **Constraints** | 25% | `error_handling_requirements` — Defines error handling, logging, and failure recovery expectations; `security_considerations` — Specifies security requirements (input validation, SQL injection, XSS prevention); `performance_requirements` — Defines performance targets (response time, memory, scalability); `scope_exclusions` — Explicitly excludes features, libraries, or approaches |

Config: `defaults/coding_task_eval_config.yaml` — task: 0.30, context: 0.25, references: 0.20, constraints: 0.25

### Coding Task Output Evaluation Dimensions

| Dimension | Score Range | What It Checks |
|-----------|-----------|----------------|
| `code_correctness` | 0.0 - 1.0 | Does the code have correct syntax, logic, and produce expected functionality? |
| `code_quality` | 0.0 - 1.0 | Does the code follow best practices — readability, naming, documentation, SOLID? |
| `requirements_coverage` | 0.0 - 1.0 | Does the code implement ALL specified requirements? |
| `error_handling_security` | 0.0 - 1.0 | Does the code include proper validation, error handling, and security? |
| `maintainability` | 0.0 - 1.0 | Is the code well-structured, testable, and easily extensible? |

### Exam Interview Agent Prompts Criteria

When `task_type` is `EXAM_INTERVIEW`, exam-specific sub-criteria replace the general ones. Loaded via `get_criteria_for_task_type(TaskType.EXAM_INTERVIEW)`.

| Dimension | Weight | Exam-Specific Sub-Criteria |
|-----------|--------|----------------------------|
| **Task** | 30% | `assessment_objective_defined` — States what knowledge, skills, or competencies are being assessed; `question_design_specified` — Defines question types, format, and answer expectations; `difficulty_calibration` — Specifies difficulty level or distribution (e.g., Bloom's taxonomy); `rubric_or_scoring_defined` — Includes scoring criteria, point allocation, or evaluation rubric |
| **Context** | 25% | `candidate_profile_defined` — Describes the target candidates (role, experience level, background); `assessment_context_provided` — Provides the setting (job interview, certification, course exam); `subject_domain_specified` — Identifies the technical or knowledge domain; `time_constraints_defined` — Specifies duration, pacing, or time-per-question guidelines |
| **References** | 20% | `sample_questions_provided` — Includes example questions or question templates; `source_material_referenced` — References textbooks, standards, or curricula; `assessment_standards_referenced` — References assessment frameworks or best practices |
| **Constraints** | 25% | `fairness_and_bias_safeguards` — Addresses bias prevention, accessibility, and cultural sensitivity; `anti_cheating_measures` — Specifies question randomization, proctoring, or integrity measures; `format_and_structure_constraints` — Defines exam structure (sections, question counts, ordering); `content_exclusions` — Explicitly excludes topics, question types, or approaches |

Config: `defaults/exam_interview_eval_config.yaml` — task: 0.30, context: 0.25, references: 0.20, constraints: 0.25

### Exam Interview Output Evaluation Dimensions

| Dimension | Score Range | What It Checks |
|-----------|-----------|----------------|
| `question_quality` | 0.0 - 1.0 | Are the questions clear, unambiguous, and well-structured? |
| `assessment_coverage` | 0.0 - 1.0 | Does the assessment proportionally cover all specified topics? |
| `difficulty_calibration` | 0.0 - 1.0 | Does the difficulty match the specified level and distribution? |
| `rubric_completeness` | 0.0 - 1.0 | Is the scoring guide thorough, fair, and actionable? |
| `fairness_objectivity` | 0.0 - 1.0 | Is the assessment free from bias and trick questions? |

### LinkedIn Professional Post Prompts Criteria

When `task_type` is `LINKEDIN_POST`, LinkedIn-specific sub-criteria replace the general ones. Loaded via `get_criteria_for_task_type(TaskType.LINKEDIN_POST)`.

| Dimension | Weight | LinkedIn-Specific Sub-Criteria |
|-----------|--------|--------------------------------|
| **Task** | 25% | `post_objective_defined` — States the post's goal (thought leadership, announcement, engagement, etc.); `writing_voice_specified` — Defines the author's writing voice and tone; `content_format_specified` — Specifies post format (story, listicle, hot take, carousel text, etc.); `call_to_action_defined` — Includes a clear call-to-action (comment, share, follow link, etc.) |
| **Context** | 35% | `target_audience_specified` — Identifies the professional audience (industry, role, seniority); `author_identity_defined` — Describes the author's professional identity and credibility; `industry_topic_context` — Provides industry context, trends, or timely relevance; `platform_awareness` — Demonstrates understanding of LinkedIn norms and algorithm preferences |
| **References** | 15% | `inspiration_posts_provided` — Includes example posts or style references; `data_statistics_referenced` — References data, statistics, or research to support claims; `expertise_basis_specified` — Identifies the knowledge or experience basis for the content |
| **Constraints** | 25% | `length_formatting_constraints` — Specifies post length, line breaks, or formatting rules; `tone_boundaries` — Defines tone guardrails (e.g., avoid salesy, stay authentic); `content_exclusions` — Explicitly excludes topics, competitors, or sensitive subjects; `hashtag_mention_requirements` — Specifies hashtag strategy and @mention requirements |

Config: `defaults/linkedin_post_eval_config.yaml` — task: 0.25, context: 0.35, references: 0.15, constraints: 0.25

### LinkedIn Professional Post Output Evaluation Dimensions

| Dimension | Score Range | What It Checks |
|-----------|-----------|----------------|
| `professional_tone_authenticity` | 0.0 - 1.0 | Does the post use an authentic professional voice appropriate for the author and audience? |
| `hook_scroll_stopping_power` | 0.0 - 1.0 | Does the opening line grab attention and compel readers to click "see more"? |
| `audience_engagement_potential` | 0.0 - 1.0 | Is the content likely to generate meaningful comments, shares, and professional discussion? |
| `value_delivery_expertise` | 0.0 - 1.0 | Does the post deliver actionable insights, expertise, or unique perspective? |
| `linkedin_platform_optimization` | 0.0 - 1.0 | Does the post follow LinkedIn best practices (formatting, hashtags, length, readability)? |

### Summarization Output Evaluation Dimensions

| Dimension | Score Range | What It Checks |
|-----------|-----------|----------------|
| `information_accuracy` | 0.0 - 1.0 | Does the summary accurately represent the source material? |
| `logical_structure` | 0.0 - 1.0 | Is the summary logically organized with a clear flow? |
| `key_information_coverage` | 0.0 - 1.0 | Were all essential points from the source captured? |
| `source_fidelity` | 0.0 - 1.0 | Does the summary stay faithful without adding interpretation? |
| `conciseness_precision` | 0.0 - 1.0 | Is every sentence purposeful and precise? |

### Grading Scale

| Grade | Score Range | Color |
|-------|------------|-------|
| Excellent | 85-100 | `#22C55E` (green) |
| Good | 65-84 | `#3B82F6` (blue) |
| Needs Work | 40-64 | `#F59E0B` (amber) |
| Weak | 0-39 | `#EF4444` (red) |

### Output Evaluation Dimensions (LLM-as-Judge via LangSmith)

Used in **Output** and **Full** evaluation modes. Each dimension is scored 0-1 by an LLM judge.

| Dimension | Score Range | What It Checks |
|-----------|-----------|----------------|
| `relevance` | 0.0 - 1.0 | Does the output directly address the prompt? |
| `coherence` | 0.0 - 1.0 | Is the output well-structured and logically consistent? |
| `completeness` | 0.0 - 1.0 | Does the output cover all requested points? |
| `instruction_following` | 0.0 - 1.0 | Does the output respect constraints and format requirements? |
| `hallucination_risk` | 0.0 - 1.0 | Is the output free from fabricated or unsupported claims? (higher = safer) |

### Improvement Priority

| Priority | When Used |
|----------|-----------|
| CRITICAL | Core components missing (no task, completely vague) |
| HIGH | Important elements absent (no persona, no context) |
| MEDIUM | Quality enhancements (constraints, references) |
| LOW | Polish and optimization |

---

## Always-Enhanced Evaluation Pipeline

Every evaluation automatically applies all three advanced techniques (CoT+ToT+Meta). The strategy dropdown has been removed — `get_default_strategy()` always returns `StrategyConfig(use_cot=True, use_tot=True, use_meta=True)`. The `EvaluationStrategy` enum and `resolve_strategy()` are retained for backward compatibility.

### Techniques Applied

| Technique | Node | What It Does |
|-----------|------|-------------|
| **Chain-of-Thought (CoT)** | `analyze_prompt`, `analyze_system_prompt` | Step-by-step reasoning preamble always prepended. Reasoning trace captured in `cot_reasoning_trace` state field |
| **Tree-of-Thought (ToT)** | `generate_improvements` | Generates N branches (default 3), selects/synthesizes best. Audit trail captured in `tot_branches_data`. Falls back to standard if ToT fails |
| **Meta-Evaluation** | `meta_evaluate` | Self-assessment pass always runs. Scores accuracy, completeness, actionability, faithfulness, and overall confidence |

### Multi-Execution Model & Composite Improvement

Both original and optimized prompts are executed N times (configurable 2-5 via `execution_count` setting, default 2) for output reliability. Executions run concurrently via `asyncio.gather()` with `return_exceptions=True` for graceful partial failure handling.

The headline improvement metric is a **composite score** computed by `_compute_composite_improvement()` in `report_generator.py`, combining normalized signals from all four engines: T.C.R.E.I. structural gap (weight 25%), output quality delta (35%), meta-evaluation confidence (20%), and ToT branch confidence (20%). Missing engine values default to 0.5; negative output deltas are clamped to 0.

### State Fields for Strategies

| Field | Type | Description |
|-------|------|-------------|
| `strategy` | `StrategyConfig \| None` | Active strategy config; always set to enhanced via `get_default_strategy()` |
| `execution_count` | `int` | Number of times to execute each prompt (default 2, range 2-5) |
| `original_outputs` | `list[str] \| None` | N outputs from original prompt execution |
| `original_output_summary` | `str \| None` | Formatted aggregate of N original outputs |
| `optimized_outputs` | `list[str] \| None` | N outputs from optimized prompt execution |
| `optimized_output_summary` | `str \| None` | Formatted aggregate of N optimized outputs |
| `optimized_output_evaluation` | `OutputEvaluationResult \| None` | Quality evaluation for optimized prompt output |
| `cot_reasoning_trace` | `str \| None` | CoT reasoning captured during analysis |
| `tot_branches_data` | `ToTBranchesAuditData \| None` | ToT exploration audit trail |
| `meta_assessment` | `MetaAssessment \| None` | Meta-evaluation scores |
| `meta_findings` | `list[str]` | Textual findings from meta-evaluation |

### ToTBranchesAuditData Model

| Field | Type | Description |
|-------|------|-------------|
| `branches` | `list[ToTBranchAuditEntry]` | Explored improvement branches |
| `selected_branch_index` | `int` | Index of the selected branch |
| `selection_rationale` | `str` | Why this branch was selected |
| `synthesized` | `bool` | Whether the final prompt was synthesized from multiple branches |

### ToTBranchAuditEntry Model

| Field | Type | Description |
|-------|------|-------------|
| `approach` | `str` | Description of the improvement approach |
| `improvements_count` | `int` | Number of improvements in this branch |
| `rewritten_prompt_preview` | `str` | First 200 chars of the rewritten prompt |
| `confidence` | `float` | Branch confidence score (0.0-1.0) |

### MetaAssessment Model

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `accuracy_score` | `float` | 0.0-1.0 | How accurately the evaluation assessed the prompt |
| `completeness_score` | `float` | 0.0-1.0 | Whether all relevant aspects were covered |
| `actionability_score` | `float` | 0.0-1.0 | How actionable the improvement suggestions are |
| `faithfulness_score` | `float` | 0.0-1.0 | Whether the evaluation stays grounded in the actual prompt |
| `overall_confidence` | `float` | 0.0-1.0 | Overall confidence in the evaluation quality |

### Graph Topology (Full Mode)

```
analyze_prompt (CoT) → score → run_prompt_for_output (Nx) → evaluate_output
    → generate_improvements (ToT)
    → run_optimized_prompt (Nx)      [if rewritten_prompt exists]
    → evaluate_optimized_output      [if rewritten_prompt exists]
    → meta_evaluate (always)
    → build_report
```

When no `rewritten_prompt` is produced, the pipeline skips `run_optimized_prompt` and `evaluate_optimized_output`, routing directly from `generate_improvements` to `meta_evaluate`.

---

## Documentation Update Rules

### When to Update This File

Update `docs/ARCHITECTURE.md` (this file) when ANY of the following happens:

1. **New graph node** added or removed → update Module Reference → Nodes table
2. **New database table or column** → update Database Schema + `database.dbml`
3. **New module or file** → update Module Reference
4. **New Pydantic model** → update Evaluator section
5. **New LLM prompt template** → update Prompts section
6. **New config option** → update Config section
7. **Dimension weights or criteria changed** → update Evaluation Framework
8. **New external dependency** → update System Overview

### When to Update Eraser Diagrams

Update the relevant `.eraser` file when:
- New nodes or edges added to the LangGraph → `langgraph-workflow.eraser`
- New modules or dependency arrows → `component-diagram.eraser`
- New external services (API, DB, etc.) → `architecture.eraser`
- New data flow stages → `data-flow.eraser`

### When to Update dbdiagram.io

Update `database.dbml` when:
- New table added
- Column added, removed, or type changed
- New index created
- JSON schema of JSONB columns changes

### When to Update README.md

Update `README.md` when:
- New feature is added (add to Features section)
- New environment variable (add to Configuration Reference)
- New make command (add to Commands section)
- Project structure changes (update tree)
- Setup steps change

---

## Version History

| Date | Change | Files Affected |
|------|--------|---------------|
| 2026-02-18 | Initial architecture | All files created |
| 2026-02-18 | Implement follow-up node with LLM integration, add `followup_action` state field, `FOLLOWUP_SYSTEM_PROMPT` template, conditional routing from follow-up node, fix `uv sync --group dev` → `--extra dev` | `conversational.py`, `graph.py`, `state.py`, `prompts/__init__.py`, `templates.py`, `Makefile`, `README.md` |
| 2026-02-18 | Added 3 evaluation modes (Structure/Output/Full), OpenAI provider, Langfuse integration, 3 new graph nodes (`run_prompt_for_output`, `evaluate_output`, `build_report`), centralized LLM factory, new Pydantic models (`EvalPhase`, `OutputDimensionScore`, `OutputEvaluationResult`, `FullEvaluationReport`), `OUTPUT_EVALUATION_SYSTEM_PROMPT` template, 4 new DB columns, 193 tests at 96.45% coverage | `output_runner.py`, `output_evaluator.py`, `report_builder.py`, `llm_factory.py`, `langfuse_utils.py`, `graph.py`, `state.py`, `evaluator/__init__.py`, `templates.py`, `db/models.py`, `db/repository.py`, `app.py` |
| 2026-02-18 | Refactored `app.py`: always runs Full evaluation (structure + output), fixed `astream` unpacking bug (`event.items()` not tuple), replaced Markdown report with interactive HTML dashboard (Tailwind CSS, collapsible sections, score badges, copy-to-clipboard prompt), attached as `cl.File` element | `app.py`, `README.md`, `docs/ARCHITECTURE.md`, `docs/diagrams/data-flow.eraser` |
| 2026-02-18 | Replaced Langfuse with LangSmith for output evaluation scoring. Removed all Langfuse code/config. Added `langsmith_utils.py` with `get_langsmith_client()` and `score_run()`. Output evaluator now uses `collect_runs` to capture run IDs and posts dimension scores as LangSmith feedback. Renamed DB column `langfuse_trace_id` → `langsmith_run_id`. | `langsmith_utils.py`, `output_evaluator.py`, `output_runner.py`, `report_builder.py`, `evaluator/__init__.py`, `config/__init__.py`, `db/models.py`, `repository.py`, `prompts/__init__.py`, `app.py`, `.env.example`, Alembic migration |
| 2026-02-18 | Replaced server-side HTML generation with Professional Audit Report using CSS Grid accordion and client-side JSON rendering. Created `report_generator.py` with `build_audit_data()` and `generate_audit_report()`. Removed old HTML helpers from `app.py`. Updated LangSmith project name. | `report_generator.py`, `app.py`, `config/__init__.py`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-18 | **Structured Output**: Replaced all `json.loads()` parsing in 4 nodes with Pydantic schemas via `with_structured_output()` and automatic fallback. Created `llm_schemas.py` (LLM response schemas) and `structured_output.py` (`invoke_structured()` helper). **RAG Pipeline**: Added in-memory vector store grounding evaluations with T.C.R.E.I. framework docs, scoring guides, criteria, and domain configs. Created `knowledge_store.py`, `tcrei_framework.md`, `scoring_guide.md`. Added `{rag_context}` to analysis/improvement prompts. **Adaptive Chunking**: Long prompts (2000+ tokens) auto-split at markdown/XML section boundaries, analyzed per-chunk, aggregated via token-weighted scoring. Created `chunking.py`. Added `chunk_count` to `AgentState`. 268 tests at 92% coverage. | `llm_schemas.py`, `structured_output.py`, `knowledge_store.py`, `chunking.py`, `tcrei_framework.md`, `scoring_guide.md`, `analyzer.py`, `improver.py`, `output_evaluator.py`, `conversational.py`, `state.py`, `prompts/__init__.py`, `pyproject.toml` |
| 2026-02-18 | **Fix Output Evaluation Pipeline**: Restructured graph so improvements come AFTER output evaluation (FULL: analyze→score→run→eval→improve→report). Added `recommendation` field to `OutputDimensionLLMResponse` and `OutputDimensionScore`. Enhanced output evaluation prompt to produce per-dimension recommendations. Rewrote `output_evaluator.py` to use `invoke_structured()` and return 5 placeholder dims on failure (not `[]`). Added error handling to `output_runner.py`. Enhanced `improver.py` to read `output_evaluation` and pass quality summary to LLM. Updated `report_generator.py` `_quality_item()` to use actionable recommendations. 284 tests at 94% coverage. | `llm_schemas.py`, `evaluator/__init__.py`, `prompts/__init__.py`, `output_evaluator.py`, `output_runner.py`, `graph.py`, `improver.py`, `report_generator.py`, all test files, all diagram files |
| 2026-02-19 | **Rebrand to LLMs Prompt Evaluator**: Replaced all "Lunagen" references across source code, templates, tests, and documentation. Updated LangSmith project name to `llms-prompt-evaluator`. Rewrote README with Google Prompting Essentials framing. Created `public/icon.svg`. Updated Chainlit config. | `app.py`, `report_generator.py`, `config/__init__.py`, `pyproject.toml`, `chainlit.md`, `chainlit_en-US.md`, `.chainlit/config.toml`, `README.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, `tests/unit/test_report_generator.py` |
| 2026-02-19 | **Documentation overhaul**: Comprehensive README rewrite with professional structure — project overview, key features table, two evaluation systems explained, step-by-step installation guide, technology rationale table, contributing guidelines, MIT license for Innovacores & Brandon, author links. Updated Chainlit README with intelligent detection section and Innovacores branding. | `README.md`, `chainlit.md`, `chainlit_en-US.md`, `docs/ARCHITECTURE.md` |
| 2026-02-19 | **Fix Chainlit storage warning**: Created `LocalStorageClient` implementing `BaseStorageClient` for local filesystem file uploads. Registered via `@cl.data_layer` in `app.py`. Removed unused `[data]` section from `.chainlit/config.toml` (Chainlit 2.9.6 doesn't parse it). Eliminates "No storage client configured" warning when using `cl.File`. | `src/utils/local_storage.py` (new), `src/app.py`, `.chainlit/config.toml`, `docs/ARCHITECTURE.md` |
| 2026-02-19 | **Dynamic Report Filename + Context-Aware Prompt Rewriting**: Report filenames now include `{user}-{session}-report-{datetime}.html` for unique identification. Added `prompt_type` field to `AgentState` (`"initial"` or `"continuation"`). Router node detects continuation prompts via signal phrases and anaphoric references. Improver node selects type-specific guidance (`PROMPT_TYPE_INITIAL` / `PROMPT_TYPE_CONTINUATION`) to preserve continuation context in rewrites. Added `PROMPT_TYPE_INITIAL` and `PROMPT_TYPE_CONTINUATION` template constants. | `app.py`, `state.py`, `router.py`, `improver.py`, `prompts/__init__.py`, `prompts/templates.py`, `test_router.py`, `test_improver.py`, `test_app.py`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-18 | **Auth + Embeddings + Self-Learning**: Added password authentication via Chainlit `@cl.password_auth_callback`. Created `src/embeddings/service.py` with OpenAI embedding generation, pgvector storage, and cosine similarity search. Added `conversation_embeddings` table with IVFFlat index. Integrated self-learning into analyzer (historical context injection) and improver (historical improvements). Report builder stores embeddings after each evaluation. Added recommendation UI panel showing similar past evaluations. New settings: `auth_enabled`, `auth_secret_key`, `openai_embedding_model`, `embedding_dimensions`, `similarity_threshold`, `max_similar_results`. New `AgentState` fields: `user_id`, `similar_evaluations`. | `app.py`, `embeddings/service.py`, `db/models.py`, `config/__init__.py`, `agent/state.py`, `agent/nodes/analyzer.py`, `agent/nodes/improver.py`, `agent/nodes/report_builder.py`, `docker/init.sql`, `.env.example`, `pyproject.toml`, all test files, all doc files |
| 2026-02-19 | **Added Summarization Prompts task type** with summarization-specific T.C.R.E.I. criteria, output quality dimensions, improvement guidance, Chainlit chat profile, and eval config. New `TaskType.SUMMARIZATION` enum value. Summarization criteria: `SUMMARIZATION_TASK_CRITERIA`, `SUMMARIZATION_CONTEXT_CRITERIA`, `SUMMARIZATION_REFERENCES_CRITERIA`, `SUMMARIZATION_CONSTRAINTS_CRITERIA`, `SUMMARIZATION_CRITERIA`, updated `get_criteria_for_task_type()`. New prompts: `SUMMARIZATION_ANALYSIS_SYSTEM_PROMPT`, `SUMMARIZATION_OUTPUT_EVALUATION_SYSTEM_PROMPT`, `SUMMARIZATION_IMPROVEMENT_GUIDANCE`. New config: `summarization_eval_config.yaml` (references weight 0.30). Chainlit chat profile: "Summarization Prompts". `task_type` routing added to analyzer, scorer, output_evaluator, and improver nodes. | `evaluator/__init__.py`, `evaluator/criteria.py`, `prompts/__init__.py`, `prompts/templates.py`, `config/defaults/summarization_eval_config.yaml`, `config/eval_config.py`, `agent/nodes/analyzer.py`, `agent/nodes/output_evaluator.py`, `agent/nodes/improver.py`, `app.py`, `tests/unit/test_summarization_criteria.py`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-19 | **Refined Summarization criteria per Google's Summarization Best Practices**: Renamed criteria to align with Google's specific guidance — `content_scope_specified` (which content to summarize), `format_and_tone_defined` (format AND tone/reading level), `persona_or_reading_level` (persona or 9th grade reading level), `example_summary_with_source` (example summary paired with its source), `hallucination_safeguards` (large input hallucination warning). Updated all prompt templates with Google's specific language for anchoring, hallucination prevention, and iterate guidance. Updated YAML config, tests, and documentation. | `evaluator/criteria.py`, `prompts/__init__.py`, `config/defaults/summarization_eval_config.yaml`, `tests/unit/test_summarization_criteria.py`, `tests/unit/test_analyzer.py`, `docs/ARCHITECTURE.md` |
| 2026-02-19 | **Rebrand to Professional Prompt Shaper**: Replaced all "LLMs Prompt Evaluator" references with "Professional Prompt Shaper" across source code, HTML templates, tests, and documentation. New diamond+cursor icon design for logo. Generated `favicon.ico`, `favicon.svg`, and custom JS for browser tab favicon. Updated LangSmith project name to `professional-prompt-shaper`. Updated Chainlit config with new app name and custom_js for favicon injection. | `app.py`, `report_generator.py`, `config/__init__.py`, `pyproject.toml`, `chainlit.md`, `chainlit_en-US.md`, `.chainlit/config.toml`, `README.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, `tests/unit/test_report_generator.py`, `public/icon.svg`, `public/favicon.svg`, `public/favicon.ico`, `public/favicon.js` |
| 2026-02-19 | **Fixed login page branding**: Added `public/logo_dark.svg` and `public/logo_light.svg` to override Chainlit's default login page logo. Chainlit's `/logo` endpoint checks `public/logo_{theme}.*` before falling back to the default Chainlit logo. Regenerated `favicon.ico` with proper multi-size (16/32/48px) ICO containing the diamond+cursor icon in matching indigo/violet palette. | `public/logo_dark.svg`, `public/logo_light.svg`, `public/favicon.ico`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-19 | **Login page intro panel + brand theming**: Added `public/theme.json` to set primary color `hsl(243, 75%, 59%)` (deep indigo) for both light/dark themes — applies to all buttons, focus rings, and sidebar accent. Created `public/custom.css` to style the login page right panel with brand color background and hide the default image. Created `public/custom.js` to inject introduction text (app purpose, features list, author) into the login page right panel and handle favicon/title. Replaced `favicon.js` with `custom.js`. Updated `.chainlit/config.toml` with `custom_css` and updated `custom_js` reference. | `public/theme.json`, `public/custom.css`, `public/custom.js`, `.chainlit/config.toml`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-19 | **Added Email Creation Prompts task type** with email-specific T.C.R.E.I. criteria, output quality dimensions, improvement guidance, Chainlit action buttons, and eval config. New `TaskType` enum (`GENERAL`, `EMAIL_WRITING`). Email criteria: `EMAIL_TASK_CRITERIA`, `EMAIL_CONTEXT_CRITERIA`, `EMAIL_REFERENCES_CRITERIA`, `EMAIL_CONSTRAINTS_CRITERIA`, `EMAIL_CRITERIA`, `get_criteria_for_task_type()`. New prompts: `EMAIL_ANALYSIS_SYSTEM_PROMPT`, `EMAIL_OUTPUT_EVALUATION_SYSTEM_PROMPT`, `EMAIL_IMPROVEMENT_GUIDANCE`. New config: `email_writing_eval_config.yaml`. Chainlit action buttons: `on_select_general_task`, `on_select_email_writing`. `task_type` passed to `initial_state` and used by analyzer, scorer, output_evaluator, and improver nodes. | `evaluator/__init__.py`, `evaluator/criteria.py`, `prompts/templates.py`, `prompts/__init__.py`, `config/defaults/email_writing_eval_config.yaml`, `config/eval_config.py`, `agent/state.py`, `agent/nodes/analyzer.py`, `agent/nodes/scorer.py`, `agent/nodes/output_evaluator.py`, `agent/nodes/improver.py`, `app.py`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Migrate Embeddings from VoyageAI to Ollama**: Replaced `langchain-voyageai` with `langchain-ollama` and `VoyageAIEmbeddings` with `OllamaEmbeddings(model="nomic-embed-text")` in embedding service and RAG knowledge store. Removed `voyage_api_key` setting, added `ollama_base_url`. Changed `embedding_model` default to `nomic-embed-text`, `embedding_dimensions` to 768. Fixed ORM `Vector(512)` → `Vector(768)` to match `init.sql`. Added Ollama service to Docker Compose with model auto-pull on `docker-up`. Created Alembic migration 002 to alter vector column dimension. Updated logging, tests, and all documentation. | `docker/docker-compose.yml`, `Makefile`, `pyproject.toml`, `src/config/__init__.py`, `.env.example`, `src/embeddings/service.py`, `src/rag/knowledge_store.py`, `src/db/models.py`, `src/utils/logging_config.py`, `tests/unit/test_embedding_service.py`, `alembic/versions/002_change_embedding_dimension_to_768.py`, `README.md`, `docs/ARCHITECTURE.md`, `docs/diagrams/database.dbml`, `docs/diagrams/architecture.eraser`, `docs/diagrams/component-diagram.eraser`, `docs/diagrams/data-flow.eraser` |
| 2026-02-20 | **Dual LLM Provider: Google Gemini Primary + Anthropic Fallback**: Rewrote `llm_factory.py` with `_try_google()` and `_try_anthropic()` helper functions and cascading fallback in `get_llm()`. Google Gemini 2.5 Flash via `ChatGoogleGenerativeAI` + Vertex AI is the primary provider, loading credentials from `src/agent/nodes/google-key.json`. If Google fails (missing key, auth error), automatically falls back to Anthropic Claude. If both fail, raises `RuntimeError` with setup instructions. Added `LLMProvider.GOOGLE` enum, `google_model`, `google_project`, `google_location` settings. Updated `.env.example`, README (API keys, setup, technologies, env vars), and all documentation. | `src/utils/llm_factory.py`, `src/config/__init__.py`, `.env.example`, `tests/unit/test_llm_factory.py`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Attach HTML Reports to Similar Past Evaluations + Short Thread Names**: Added `generate_similarity_report()` to `report_generator.py` — generates lightweight self-contained HTML reports for similar past evaluations with score badge, grade, original prompt, improvements, and optimized prompt with copy-to-clipboard. Updated `_send_recommendations()` in `app.py` to generate and attach downloadable HTML files (`past-eval-{i}-{uuid8}.html`) as `cl.File` elements for each similar evaluation with a `rewritten_prompt`. Removed plain-text "Optimized version available" indicator. Added `_set_thread_name()` helper to set short, unique conversation names ("Chat N · Mon DD, HH:MM AM/PM") in the history sidebar via `data_layer.update_thread()` + `first_interaction` emitter. | `src/utils/report_generator.py`, `src/app.py`, `tests/unit/test_report_generator.py`, `tests/unit/test_app.py`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **LLM Provider Selector in Chat UI**: Added `ChatSettings` with a `Select` widget in the Chainlit header so users can choose between Google Gemini and Anthropic Claude as the LLM evaluator at runtime. Default is Google Gemini. Labels reflect model versions from `.env` (e.g. "Google Gemini (gemini-2.5-flash)"). Added `@cl.on_settings_update` handler to store user selection. Added `llm_provider` field to `AgentState` and propagated through all 6 graph nodes (`analyzer.py`, `scorer.py` via analyzer, `improver.py`, `output_runner.py`, `output_evaluator.py`, `conversational.py`) to `get_llm(provider)`. Updated `_run_evaluation()` to pass `llm_provider` from session into `initial_state`. Welcome message shows selected provider. | `src/app.py`, `src/agent/state.py`, `src/agent/nodes/analyzer.py`, `src/agent/nodes/improver.py`, `src/agent/nodes/output_runner.py`, `src/agent/nodes/output_evaluator.py`, `src/agent/nodes/conversational.py`, `src/utils/llm_factory.py`, `tests/unit/test_app.py`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **RAG Knowledge Store Warmup at Startup**: Added `warmup_knowledge_store()` to `knowledge_store.py` — eagerly loads documents, chunks them, and embeds via Ollama before Chainlit accepts connections. Called at module level in `app.py` so the RAG store is ready before `localhost:8000` starts serving. Logs "Warming up RAG knowledge store ..." and "RAG knowledge store ready." on success. Graceful fallback: if Ollama is unreachable the warning is logged and the app continues (store retries lazily on first query). | `src/rag/knowledge_store.py`, `src/app.py`, `tests/unit/test_knowledge_store.py`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Fix Truncated LLM Output + Thread Deletion Cleanup**: Increased `llm_max_tokens` default from 4096 to 16384 — prevents empty evaluation results when Gemini 2.5 Flash thinking budget consumes output token quota. Added diagnostic logging to `invoke_structured()` fallback path: detects truncated responses (missing JSON closing chars) and logs response_length on parse failures. Added `thread_id` column to `Evaluation` and `ConversationEmbedding` ORM models with indexes. Created Alembic migration 003. Added `thread_id` to `AgentState`, passed from `cl.context.session.thread_id` through `_run_evaluation()` → `store_evaluation_embedding()`. Created `CustomDataLayer` extending `ChainlitDataLayer` — overrides `delete_thread()` to DELETE from `evaluations` and `conversation_embeddings` by `thread_id` before parent cleanup. Graceful: app cleanup failures are logged and do not block thread deletion. Wired into `app.py` via `@cl.data_layer`. | `src/config/__init__.py`, `.env`, `.env.example`, `src/utils/structured_output.py`, `src/db/models.py`, `src/db/repository.py`, `src/agent/state.py`, `src/app.py`, `src/embeddings/service.py`, `src/agent/nodes/report_builder.py`, `src/utils/custom_data_layer.py` (new), `alembic/versions/003_add_thread_id_columns.py` (new), `docker/init.sql`, `tests/unit/test_structured_output.py`, `tests/unit/test_custom_data_layer.py` (new), `tests/unit/test_repository.py`, `tests/unit/test_embedding_service.py`, `docs/ARCHITECTURE.md`, `docs/diagrams/database.dbml`, `docs/diagrams/component-diagram.eraser` |
| 2026-02-20 | **Example Prompts with T.C.R.E.I. Breakdown Toggle**: Added "Show Example Prompt" `cl.Action` button to welcome message. Clicking displays an annotated example prompt with full T.C.R.E.I. dimension breakdown tailored to the active task type (General, Email, Summarization). Session flag `example_shown` prevents duplicate sends; button removed after click via `action.remove()`. Created `example_prompts.py` with `ExamplePrompt` and `AnnotatedSection` dataclasses, `EXAMPLE_PROMPTS` registry, and `get_example_for_task_type()` accessor. Created `example_formatter.py` with `format_example_markdown()` producing pure Markdown output. Added `on_show_example` action callback to `app.py`. 58 new tests (51 for data/formatter + 9 for app integration) bringing total to 555. | `src/evaluator/example_prompts.py` (new), `src/utils/example_formatter.py` (new), `src/app.py`, `tests/unit/test_example_prompts.py` (new), `tests/unit/test_example_formatter.py` (new), `tests/unit/test_app.py`, `README.md`, `docs/ARCHITECTURE.md`, `docs/diagrams/component-diagram.eraser` |
| 2026-02-20 | **4 New Features: Diff + Coding + Exam + Chat**: (1) **Audit Report Text Comparison**: Word-level inline diff between original and optimized prompt in all audit reports via `generate_diff_html()` using `difflib.SequenceMatcher`. Green spans for additions, red strikethrough for deletions, collapsible "Prompt Comparison" accordion section. (2) **Coding Task Prompts Evaluator**: Full evaluation profile with coding-specific T.C.R.E.I. criteria (programming language, requirements, architecture, security), 5 output quality dimensions (code correctness, quality, requirements coverage, error handling, maintainability), dedicated prompts, YAML config, and example prompt. (3) **Exam Interview Agent Prompts Evaluator**: Full evaluation profile with exam-specific T.C.R.E.I. criteria (assessment objectives, question design, difficulty calibration, rubric, fairness), 5 output quality dimensions (question quality, assessment coverage, difficulty calibration, rubric completeness, fairness), dedicated prompts, YAML config, and example prompt. (4) **Direct Test your optimized prompts**: Two new chat profiles ("Chat with Gemini 2.5", "Chat with Claude 4.6") that bypass the LangGraph evaluation pipeline for direct multi-turn conversation with thinking/reasoning display in collapsible `cl.Step` sections. | `src/utils/report_generator.py`, `src/evaluator/__init__.py`, `src/evaluator/criteria.py`, `src/evaluator/example_prompts.py`, `src/prompts/__init__.py`, `src/config/eval_config.py`, `src/config/defaults/coding_task_eval_config.yaml` (new), `src/config/defaults/exam_interview_eval_config.yaml` (new), `src/agent/nodes/analyzer.py`, `src/agent/nodes/output_evaluator.py`, `src/agent/nodes/improver.py`, `src/app.py`, `tests/unit/test_report_generator.py`, `tests/unit/test_coding_criteria.py` (new), `tests/unit/test_exam_criteria.py` (new), `tests/unit/test_chat_handler.py` (new), `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Merge 2 Chat Profiles into 1 with LLM Selector**: Replaced two separate chat profiles ("Chat with Gemini 2.5", "Chat with Claude 4.6") with a single "Test your optimized prompts" profile. Added `ChatSettings` widget with `Select` dropdown in chat mode so users can switch between Google Gemini and Anthropic Claude at runtime. Updated `on_settings_update()` to route provider selection based on `profile_mode`: chat mode updates `chat_provider`, evaluator mode updates `llm_provider`. Total profiles reduced from 7 to 6. | `src/app.py`, `tests/unit/test_app.py`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Live Streaming + File Attachment Support for Chat**: Replaced `llm.ainvoke()` with `llm.astream()` in `_handle_chat_message()` for real-time token streaming — thinking deltas stream into a collapsible `cl.Step` via `stream_token()`, text deltas stream into a `cl.Message` via `stream_token()`. Added `_extract_chunk_deltas()` helper for parsing individual `AIMessageChunk.content` during streaming. Added file attachment support: `_process_attachments()` reads text files (`.py`, `.md`, `.json`, etc. under 100KB) into markdown code fences and base64-encodes images (`.png`, `.jpg`, `.gif`, `.webp`) into multimodal `image_url` content blocks. Updated `on_message()` chat branch to process `message.elements` and pass augmented input + image blocks to `_handle_chat_message()`. Added `_TEXT_FILE_EXTENSIONS`, `_IMAGE_EXTENSIONS`, `_MAX_TEXT_FILE_SIZE` constants. | `src/app.py`, `tests/unit/test_chat_handler.py`, `tests/unit/test_app.py`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Brand Icon in Audit Reports**: Replaced generic shield SVG icons with the actual brand diamond+cursor icon (`public/icon.svg`) in both the main audit report and similarity report templates. Icon appears in header (28px in audit, 24px in similarity) and footer (14px/12px) of all generated HTML reports. Header icons use lighter indigo tones (`#818CF8`, `#A5B4FC`, `#C4B5FD`) for visibility against the dark header background; footer icons use the original palette (`#6366F1`, `#4F46E5`, `#A78BFA`). | `src/utils/report_generator.py`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Documentation Refresh — Chat Profiles & Streaming**: Added dedicated "Chat Profiles" section to README with detailed descriptions of all 6 profiles (General Task, Email Creation, Summarization, Coding Task, Exam Interview Agent, Test your optimized prompts) including mode, criteria focus, and best-for guidance. Updated test count to 658. Updated `test_chat_handler.py` description to reflect chunk delta and file attachment test coverage. | `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Favicon in Audit Reports**: Added the brand diamond+cursor icon as an inline `data:image/svg+xml` favicon in both `_TEMPLATE` (main audit report) and `_SIMILARITY_TEMPLATE` (past evaluation report) `<head>` sections. Uses URL-encoded SVG with the original palette (`#6366F1`, `#4F46E5`, `#A78BFA`). Reports are self-contained HTML files opened locally, so the favicon must be embedded — external paths like `/public/favicon.svg` are unreachable. | `src/utils/report_generator.py`, `docs/ARCHITECTURE.md` |
| 2026-02-20 | **Comprehensive Documentation Refresh**: Rewrote Chainlit README files (`chainlit.md`, `chainlit_en-US.md`) with all 6 chat profiles, two evaluation systems, intelligent detection, direct chat mode with live streaming and file attachments, provider selector, example prompts, and prompt comparison diff. Redesigned login page intro panel (`public/custom.js` INTRO_HTML) with 3 categorized feature groups (Prompt Evaluation, Smart Profiles & Chat, Intelligence & Flexibility) covering 11 features: T.C.R.E.I. analysis, LLM-as-Judge scoring, AI rewriting, audit reports with diff, auto-detection, 5 evaluator profiles, direct chat with streaming & attachments, example prompts, RAG-grounded analysis, self-learning, dual providers, and LangSmith tracing. Updated tagline to reflect evaluation + chat scope. Added `feature-category` CSS class to `custom.css` for uppercase section headers. Fixed stale README.md items: `LLM_MAX_TOKENS` default corrected from 4096 to 16384, `llm_factory.py` description updated to dual-provider, added migration 003 and `custom_data_layer.py` to project tree. | `chainlit.md`, `chainlit_en-US.md`, `public/custom.js`, `public/custom.css`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-21 | **Ollama Qwen 3 4B LLM Provider Integration**: Added Ollama as third LLM provider in the cascade (Google → Anthropic → Ollama). Added `LLMProvider.OLLAMA` enum, `ollama_chat_model`, `ollama_num_predict`, `ollama_request_timeout` settings. Added `_try_ollama()` to `llm_factory.py` with `ChatOllama` from `langchain_ollama`. Added `OllamaConnectionError`, `OllamaModelNotFoundError` exceptions with fatal patterns (`model not found`, `connection refused`, `failed to connect`) and `format_fatal_error()` handlers. Added `_is_ollama_model()` detector to `structured_output.py`. No new dependencies — `langchain-ollama>=0.3.0` and `ollama_base_url` already existed. | `src/config/__init__.py`, `src/evaluator/exceptions.py`, `src/utils/llm_factory.py`, `src/utils/structured_output.py`, `.env.example`, `tests/unit/test_llm_factory.py`, `tests/unit/test_config.py`, `tests/unit/test_exceptions.py`, `tests/unit/test_structured_output.py`, `README.md`, `docs/ARCHITECTURE.md`, `docs/diagrams/architecture.eraser`, `docs/diagrams/component-diagram.eraser`, `docs/diagrams/data-flow.eraser` |
| 2026-02-21 | **Added LinkedIn Professional Post Prompts evaluation profile (6th profile)**: New `TaskType.LINKEDIN_POST` enum value. LinkedIn-specific T.C.R.E.I. criteria (`LINKEDIN_TASK_CRITERIA`, `LINKEDIN_CONTEXT_CRITERIA`, `LINKEDIN_REFERENCES_CRITERIA`, `LINKEDIN_CONSTRAINTS_CRITERIA`). New prompts: `LINKEDIN_ANALYSIS_SYSTEM_PROMPT`, `LINKEDIN_OUTPUT_EVALUATION_SYSTEM_PROMPT`, `LINKEDIN_IMPROVEMENT_GUIDANCE`. New config: `linkedin_post_eval_config.yaml` (context weight 0.35, references 0.15). LinkedIn-specific output quality dimensions: professional tone authenticity, hook/scroll-stopping power, audience engagement potential, value delivery/expertise, LinkedIn platform optimization. Chainlit chat profile: "LinkedIn Professional Post Prompts". Structure criteria focus on post objective, writing voice, content format, call-to-action, target audience, author identity, industry context, platform awareness, hashtag/mention requirements. | `evaluator/__init__.py`, `evaluator/criteria.py`, `prompts/__init__.py`, `prompts/templates.py`, `config/defaults/linkedin_post_eval_config.yaml` (new), `config/eval_config.py`, `agent/nodes/analyzer.py`, `agent/nodes/output_evaluator.py`, `agent/nodes/improver.py`, `app.py`, `tests/unit/test_linkedin_criteria.py` (new), `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-19 | **v5 Upgrade — Production Hardening**: Thread-safe DB engine/session with double-checked locking and `dispose_engine()` for graceful shutdown. `lru_cache` singleton for `get_settings()`. Centralized logging via `setup_logging()` with dev/prod formats and noisy logger silencing. Custom exception hierarchy (`EvaluatorError`, `LLMError`, `AnalysisError`, `ScoringError`, `ImprovementError`, `OutputEvaluationError`, `ReportBuildError`, `ConfigurationError`). Chainlit chat profiles replace action buttons for task type selection. Provider-aware embedding model selection (OpenAI or Google). New settings: `log_level`, `google_project_id`, per-provider model IDs. New tests: `test_app.py`, `test_embedding_service.py`, `test_exceptions.py`, `test_logging_config.py`. Updated README with detailed prerequisites (Python, uv, Docker, Git, Make install instructions per platform), PyCharm recommendation, expanded env var reference. | `src/db/__init__.py`, `src/config/__init__.py`, `src/utils/logging_config.py` (new), `src/evaluator/exceptions.py` (new), `src/embeddings/service.py`, `src/app.py`, `src/agent/state.py`, `src/agent/nodes/*.py`, `tests/unit/test_app.py` (new), `tests/unit/test_embedding_service.py` (new), `tests/unit/test_exceptions.py` (new), `tests/unit/test_logging_config.py` (new), `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-22 | **Advanced Evaluation Strategies — Full Integration**: Wired `meta_evaluator` node into LangGraph with conditional routing (`_after_improvements()` → `meta_evaluate` when `strategy.use_meta`, `_after_meta_evaluate()` → `build_report`). Created `PromptEvaluationService` in `src/evaluator/service.py` with `EvaluationReport` dataclass and `async evaluate()` orchestrator. Added strategy selection `Select` widget to Chainlit UI settings (5 presets: Standard, Enhanced, CoT, ToT, Meta). Added meta-evaluation section to HTML audit report with 5 progress bars (accuracy, completeness, actionability, faithfulness, confidence) and strategy badge. Updated `evaluation_runner.py` with `meta_evaluate` step extractor and strategy resolution from session. Updated `results_display.py` with strategy/meta-confidence display in chat summary. 77 new tests (graph routing, service, strategies). | `src/agent/graph.py`, `src/agent/nodes/meta_evaluator.py`, `src/evaluator/service.py` (new), `src/evaluator/strategies.py`, `src/ui/evaluation_runner.py`, `src/ui/results_display.py`, `src/utils/report_generator.py`, `src/app.py`, `tests/unit/test_graph.py`, `tests/unit/test_service.py` (new), `README.md`, `docs/ARCHITECTURE.md`, all eraser diagrams, `database.dbml` |
| 2026-02-22 | **Codebase Refactoring — 8-Phase Maintainability Overhaul**: (1) Deleted redundant `chainlit_en-US.md` and stale `[project.scripts]` from `pyproject.toml`. (2) Split `src/prompts/__init__.py` (774 LOC) into per-task-type sub-modules (`general.py`, `email.py`, `summarization.py`, `coding.py`, `exam.py`, `linkedin.py`) + thin re-export `__init__.py`. Deleted `src/prompts/templates.py`. (3) Converted `src/evaluator/criteria.py` (715 LOC) to package with `base.py` + per-type modules + `_CRITERIA_REGISTRY` dict replacing elif chain. (4) Split `src/app.py` (1,333 LOC → ~450 LOC) into `src/ui/` package: `profiles.py`, `thread_utils.py`, `chat_handler.py`, `evaluation_runner.py`, `results_display.py`, `audio_handler.py`. (5) Created `src/prompts/registry.py` with `TaskTypePrompts` dataclass + `_REGISTRY` dict; refactored 3 agent nodes (`analyzer.py`, `improver.py`, `output_evaluator.py`) to use registry lookup instead of elif chains (~-60 lines). (6) Decomposed `on_chat_start()` into `_init_chat_mode()` + `_init_evaluator_mode()` + `_WELCOME_MESSAGES` dict; replaced `_extract_step_summary()` elif chain with `_STEP_EXTRACTORS` dispatch dict. (7) Added 67 new tests: `test_prompt_registry.py`, `test_local_storage.py`, `test_criteria_registry.py`. Total: 771 tests. No file exceeds ~450 lines. All behavior preserved. | `src/app.py`, `src/ui/` (7 new files), `src/prompts/` (6 new sub-modules + registry.py), `src/evaluator/criteria/` (7 new files), `src/agent/nodes/analyzer.py`, `src/agent/nodes/improver.py`, `src/agent/nodes/output_evaluator.py`, `tests/unit/test_prompt_registry.py` (new), `tests/unit/test_local_storage.py` (new), `tests/unit/test_criteria_registry.py` (new), `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-22 | **Always-Enhanced Multi-Execution Evaluation Pipeline**: CoT, ToT, and Meta-Evaluation are now always active for every evaluation (removed strategy dropdown). Original and optimized prompts each execute N times concurrently (configurable 2-5, default 2) via `asyncio.gather()`. New graph nodes: `run_optimized_prompt` (Nx execution of rewritten prompt) and `evaluate_optimized_output` (LLM-as-Judge quality scoring for optimized output). New models: `ToTBranchAuditEntry`, `ToTBranchesAuditData` for ToT audit trail. Extended `FullEvaluationReport` with `optimized_output_result`, `execution_count`, `original_outputs`, `optimized_outputs`, `cot_reasoning_trace`, `tot_branches_data`. Added `get_default_strategy()` replacing configurable strategy selection. New state fields: `execution_count`, `original_outputs`, `optimized_outputs`, `optimized_output_summary`, `optimized_output_evaluation`, `cot_reasoning_trace`, `tot_branches_data`. New config: `DEFAULT_EXECUTION_COUNT`. Execution count `Select` widget (2-5) in Chainlit settings. HTML audit report adds 3 new sections: CoT reasoning trace, ToT branch exploration, original-vs-optimized quality comparison. Graph topology: `improve(ToT) → run_optimized(Nx) → eval_optimized → meta(always) → report`. 880 tests passing. | `src/agent/graph.py`, `src/agent/state.py`, `src/agent/nodes/analyzer.py`, `src/agent/nodes/improver.py`, `src/agent/nodes/output_runner.py`, `src/agent/nodes/optimized_runner.py` (new), `src/agent/nodes/output_evaluator.py`, `src/agent/nodes/report_builder.py`, `src/agent/nodes/meta_evaluator.py`, `src/evaluator/__init__.py`, `src/evaluator/strategies.py`, `src/evaluator/service.py`, `src/config/__init__.py`, `src/app.py`, `src/ui/evaluation_runner.py`, `src/ui/results_display.py`, `src/utils/report_generator.py`, `tests/unit/test_optimized_runner.py` (new), `tests/unit/test_eval_optimized_output.py` (new), `tests/unit/test_graph.py`, `tests/unit/test_app.py`, `tests/unit/test_cot_integration.py`, `tests/unit/test_tot_integration.py`, `tests/unit/test_service.py`, `tests/unit/test_strategies.py`, `README.md`, `docs/ARCHITECTURE.md`, all eraser diagrams, `database.dbml` |
| 2026-02-22 | **Fix ToT selection null index + Documentation refresh**: Fixed `ToTSelectionLLMResponse.selected_branch_index` validation error when LLM returns `null` — changed field type from `int` to `int | None` and added graceful fallback to highest-confidence branch in `improver.py`. Updated `chainlit.md` with detailed "Always-Enhanced Evaluation Pipeline" and "Multi-Execution Validation" sections explaining CoT reasoning, ToT branching, meta-evaluation, and the evaluate-optimize-validate loop. Updated `README.md` with expanded "Evaluate → Optimize → Validate Loop" section describing the closed-loop prompt quality assurance pipeline. 881 tests passing. | `src/evaluator/llm_schemas.py`, `src/agent/nodes/improver.py`, `tests/unit/test_tot_integration.py`, `chainlit.md`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-22 | **Composite Improvement Score from All Evaluation Engines**: Replaced simple output quality delta with a weighted composite metric incorporating all four engines: T.C.R.E.I. structural gap (25%), Output quality delta (35%), Meta-evaluation confidence (20%), ToT branch confidence (20%). Added `_compute_composite_improvement()` helper to `report_generator.py`. Updated `build_audit_data()` to compute and return composite breakdown. Header card sub-label changed from execution count to "Composite Score". Comparison section now shows per-engine contribution breakdown. Chat summary shows "Composite Improvement" with per-engine breakdown line. Missing meta/ToT values default to 0.5. Negative output deltas clamped to 0. 889 tests passing. | `src/utils/report_generator.py`, `src/ui/results_display.py`, `tests/unit/test_composite_improvement.py` (new), `tests/unit/test_app.py`, `chainlit.md`, `README.md`, `docs/ARCHITECTURE.md` |
| 2026-02-23 | **Document Processing & RAG Pipeline**: New `src/documents/` module with full document processing pipeline — load (PDF, DOCX, XLSX, PPTX via LangChain loaders), extract (LLM-based entity extraction), chunk (`RecursiveCharacterTextSplitter`), vectorize (Ollama embeddings), and store (pgvector with HNSW index). New DB tables: `documents` (metadata + extracted text) and `document_chunks` (vectorized chunks). Alembic migration `004_add_document_tables.py`. Document RAG retriever for cosine similarity search. New Pydantic models: `DocumentMetadata`, `DocumentChunk`, `ExtractionEntity`, `ProcessingResult`. New exceptions: `DocumentProcessingError`, `UnsupportedFormatError`. New `AgentState` fields: `document_context`, `document_ids`, `document_summary`. Document context injected as RAG section into analyzer and improver nodes. New config settings: `DOC_MAX_FILE_SIZE`, `DOC_CHUNK_SIZE`, `DOC_CHUNK_OVERLAP`, `DOC_MAX_CHUNKS_PER_QUERY`, `DOC_ENABLE_EXTRACTION`, `DOC_EXTRACTION_MODEL`. Chat handler `_process_attachments()` returns 3-tuple (text, images, documents). App orchestrator adds `_process_document_attachments()` and `_get_document_context_for_chat()`. `CustomDataLayer` extended to clean up documents and chunks on thread deletion. `DocumentRepository` added to `repository.py`. New dependencies: `pypdf>=4.0.0`, `docx2txt>=0.8`, `openpyxl>=3.1.0`, `python-pptx>=0.6.0`. 8 new test files for full document pipeline coverage. | `src/documents/` (9 new files), `src/app.py`, `src/agent/state.py`, `src/agent/nodes/analyzer.py`, `src/agent/nodes/improver.py`, `src/ui/profiles.py`, `src/ui/chat_handler.py`, `src/ui/evaluation_runner.py`, `src/config/__init__.py`, `src/db/models.py`, `src/db/repository.py`, `src/utils/custom_data_layer.py`, `pyproject.toml`, `.env.example`, `alembic/versions/004_add_document_tables.py`, `tests/unit/test_document_*.py` (8 new files), `README.md`, `docs/ARCHITECTURE.md`, all diagram files |
| 2026-02-23 | **Tiered OCR Fallback for PDF Loading**: Added 3-tier OCR fallback to `_load_pdf()` in `src/documents/loader.py` for scanned/image-based PDFs: Tier 1 (pypdf — always available), Tier 2 (pdfplumber — optional), Tier 3 (PyMuPDF OCR — optional, requires Tesseract). Tracks `best_text` across tiers and returns the best result. `_load_pdf` return type changed from `tuple[str, int | None]` to `tuple[str, int | None, dict[str, str]]` with extra metadata (`pdf_extraction_method`, `pdf_ocr_applied`, `pdf_tiers_attempted`). Added `_pdfplumber_available()` and `_pymupdf_available()` probe functions, `_extract_with_pdfplumber_sync()` and `_extract_with_pymupdf_ocr_sync()` sync extractors (called via `asyncio.to_thread`). New `ocr` optional dependency group in `pyproject.toml`: `pdfplumber>=0.11.0`, `pymupdf>=1.24.0`. New settings: `pdf_ocr_enabled` (default true), `pdf_ocr_min_text_chars` (default 50). Added `pdfplumber.*`, `fitz.*` to mypy overrides. 11 new tests in `TestPdfOcrFallback` and `TestOcrAvailabilityProbes` classes. 1003 tests passing. | `src/documents/loader.py`, `src/config/__init__.py`, `pyproject.toml`, `.env.example`, `tests/unit/test_document_loader.py`, `README.md`, `docs/ARCHITECTURE.md` |
