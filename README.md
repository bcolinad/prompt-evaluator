# Professional Prompt Shaper

**Create optimized prompts that bring real value to your day-to-day life** — whether you're coding, studying, writing, or building AI-powered workflows.

An AI-powered prompt quality assurance platform built on the **T.C.R.E.I.** framework from Google's [Prompting Essentials](https://grow.google/ai-essentials/) certification. It evaluates prompts using two complementary systems — **structural analysis** and **output quality scoring** — delivering a professional audit report with scores, detailed findings, and an optimized prompt in a single pass.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Built with LangGraph](https://img.shields.io/badge/Built%20with-LangGraph-purple.svg)](https://langchain-ai.github.io/langgraph/)
[![Google Prompting Certified](https://img.shields.io/badge/Google-Prompting%20Essentials-4285F4.svg)](https://www.skills.google/paths/2337)

<div align="center">

**Demo**

https://streamable.com/zrvd22

</div>

---

## Table of Contents

- [Project Overview](#project-overview)
- [Key Features](#key-features)
- [Two Evaluation Systems](#two-evaluation-systems)
- [Installation Guide](#installation-guide)
  - [Prerequisites](#prerequisites)
  - [Recommended IDE](#recommended-ide)
  - [Step-by-Step Setup](#step-by-step-setup)
- [Usage Instructions](#usage-instructions)
  - [Chat Profiles](#chat-profiles)
- [Architecture](#architecture)
- [Technologies Used](#technologies-used)
- [Project Structure](#project-structure)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)
- [Authors & Links](#authors--links)

---

## Project Overview

Professional Prompt Shaper is an open-source tool that helps anyone — from students to senior engineers — write better prompts. Instead of guessing whether your prompt is "good enough," paste it into the evaluator and receive:

- A **structural score** (0-100) based on Google's T.C.R.E.I. prompting framework
- An **output quality score** from an LLM-as-Judge that actually runs your prompt and evaluates the result
- **Prioritized, actionable improvements** ranked from Critical to Low
- A **fully rewritten prompt** that preserves your intent while fixing gaps
- An **interactive HTML audit report** you can download and share

The tool is grounded in knowledge from Google's Prompting Essentials certification and is designed to make prompt engineering accessible to everyone.

---

## Key Features

### Intelligent Input Detection

The core differentiator of this tool is its **intelligent detection system** that automatically determines whether user input is:

- **An initial prompt** to evaluate (triggers full T.C.R.E.I. structural analysis + output quality scoring)
- **A conversation continuation** such as follow-up questions, rewrite adjustments, or mode switches (handled by the conversational node without re-running the full pipeline)
- **A continuation prompt** (e.g., "now add error handling to the code above") — detected via signal phrases and anaphoric references, and rewritten while preserving context anchors
- **A system prompt** automatically detected via signal phrases like "system prompt," "system message," or "system instruction"

This means you don't need to tell the tool what you're doing — just type naturally. The routing engine and conversational handler work together to give you the right response every time.

### Full Feature List

| Feature | Description |
|---------|-------------|
| **Single-Paste Full Evaluation** | Paste any prompt and get both structural analysis and output quality evaluation in one pass |
| **Real-Time Progress Tracking** | Each pipeline step displays live in the chat with scores and timing as the evaluation progresses |
| **Professional Audit Report** | Self-contained HTML dashboard with interactive accordion sections, score badges, and a copy-to-clipboard optimized prompt |
| **Auto-Detection** | Automatically identifies system prompts vs standard prompts from the input text — no manual mode switching required |
| **System Prompt Evaluation** | Evaluate system prompts against expected outcomes to check alignment |
| **Actionable Improvements** | Prioritized suggestions (Critical, High, Medium, Low) with specific, implementable guidance |
| **Prompt Rewriting** | AI-generated improved version that preserves your original intent while closing structural gaps. Automatically detects continuation prompts (e.g., "now add error handling") and preserves context references instead of converting to standalone |
| **Conversation Loop** | Ask follow-ups, adjust rewrites, re-evaluate updated prompts, or switch modes — all without restarting |
| **RAG-Grounded Evaluation** | Evaluations are enriched with retrieved context from T.C.R.E.I. framework docs, scoring guides, and domain configs |
| **Adaptive Chunking** | Long prompts (2000+ tokens) are automatically split at section boundaries, analyzed per-chunk, and aggregated via token-weighted scoring |
| **Self-Learning** | Past evaluations are vectorized and stored; similar historical evaluations enhance new analyses automatically |
| **Configurable Criteria** | YAML-based evaluation config with domain-specific presets (e.g., healthcare terminology) |
| **Full Tracing** | Every evaluation is traced in LangSmith with per-dimension feedback scores for quality monitoring |
| **User Authentication** | Password-based login via Chainlit's built-in auth; enable/disable via environment variable |
| **Prompt Comparison (Diff)** | Word-level inline diff between your original prompt and the optimized rewrite in every audit report — additions in green, deletions in red with strikethrough |
| **Direct Chat Mode** | Test your optimized prompts in real time and see the actual LLM output for yourself — or use it as a full-featured chat, just like Google AI Studio, Claude, or ChatGPT. Attach documents and images directly in the conversation. Features **live token streaming**, collapsible thinking/reasoning display, and support for text files and images. Switch between Google Gemini and Anthropic Claude via the in-chat settings widget |
| **Example Prompt with T.C.R.E.I. Breakdown** | "Show Example Prompt" button on the welcome message displays an annotated example prompt with full T.C.R.E.I. dimension breakdown tailored to the selected task type |
| **Task Type Selection** | Profile selector to choose between 6 evaluation modes (General, Email, Summarization, Coding Task, Exam Interview, LinkedIn Post) and 1 direct chat mode (Test your optimized prompts), each with tailored criteria and output quality dimensions |
| **LLM Provider Selector** | In-chat settings widget to switch between Google Gemini and Anthropic Claude at runtime; model versions configurable via `.env` variables |
| **Evaluation History** | PostgreSQL persistence with pgvector similarity search for tracking prompt quality over time |
| **Always-Enhanced Evaluation (CoT+ToT+Meta)** | Every evaluation automatically applies Chain-of-Thought reasoning (step-by-step dimension analysis), Tree-of-Thought branching (multi-branch improvement exploration), and Meta-Evaluation self-assessment (confidence scoring). The audit report includes dedicated sections for CoT reasoning trace, ToT branch exploration, and meta-assessment |
| **Multi-Execution Validation** | Both original and optimized prompts are executed N times (configurable 2-5, default 2) for output reliability. Executions run concurrently via `asyncio.gather()` with graceful partial failure handling. The audit report includes a side-by-side quality comparison between original and optimized outputs |
| **Execution Count Selector** | In-chat settings widget to choose how many times each prompt is executed (2-5), enabling users to balance thoroughness vs speed |
| **Document Processing & RAG** | Upload PDF, DOCX, XLSX, and PPTX files directly in chat. Documents are parsed, chunked, vectorized (Ollama embeddings → pgvector with HNSW index), and injected as RAG context into prompt evaluations — enabling document-grounded analysis and improvement suggestions |
| **Scanned PDF OCR Fallback** | Tiered OCR extraction for scanned/image-based PDFs: `pypdf → pdfplumber → PyMuPDF OCR`. Automatically detects when a PDF has no text layer and falls back through progressively more capable extractors. Install optional OCR dependencies with `uv sync --extra ocr` (requires Tesseract for Tier 3 OCR) |

---

## Two Evaluation Systems

### 1. Structure Analysis (T.C.R.E.I.)

Derived from Google's Prompting Essentials certification, this system scores your prompt across four weighted dimensions:

| Dimension | Weight | What It Checks |
|-----------|--------|----------------|
| **Task** | 30% | Clear action verb, specific deliverable, persona definition, output format specification |
| **Context** | 25% | Background information, target audience, stated goals, domain specificity |
| **References** | 20% | Examples included, structured reference materials, labeled inputs |
| **Constraints** | 25% | Scope boundaries, length limits, format restrictions, explicit exclusions |

Each dimension is broken into sub-criteria, scored individually by an LLM, and combined using configured weights.

> **Email Creation Prompts Mode:** When the Email Creation Prompts task type is selected, the T.C.R.E.I. analysis uses different criteria weights optimized for email evaluation: Task 30%, Context 30%, References 15%, Constraints 25%. The email-specific criteria focus on tone/style, recipient clarity, email structure, and purpose rather than the general sub-criteria used in General Task Prompts mode.

> **Summarization Prompts Mode:** When the Summarization Prompts task type is selected, the T.C.R.E.I. analysis uses criteria weights that emphasize references (source material): Task 25%, Context 25%, References 30%, Constraints 20%. The summarization-specific criteria focus on summary type, source document description, length constraints, information fidelity, and key section prioritization.

> **Coding Task Prompts Mode:** When the Coding Task Prompts task type is selected, the T.C.R.E.I. analysis uses criteria optimized for coding prompts: Task 30%, Context 25%, References 20%, Constraints 25%. The coding-specific criteria focus on programming language specification, requirements clarity, architecture guidance, code quality standards, and security considerations.

> **Exam Interview Agent Prompts Mode:** When the Exam Interview Agent Prompts task type is selected, the T.C.R.E.I. analysis uses criteria designed for assessment prompts: Task 30%, Context 25%, References 20%, Constraints 25%. The exam-specific criteria focus on assessment objectives, question design, difficulty calibration, rubric definition, and fairness safeguards.

> **LinkedIn Professional Post Prompts Mode:** When the LinkedIn Professional Post Prompts task type is selected, the T.C.R.E.I. analysis uses criteria optimized for professional social media content: Task 25%, Context 35%, References 15%, Constraints 25%. The LinkedIn-specific criteria focus on post objective, writing voice, content format, call-to-action, target audience, author identity, industry context, platform awareness, and hashtag/mention requirements.

### 2. Output Quality (LLM-as-Judge)

After structural analysis, the evaluator **executes your prompt** through an LLM and then scores the generated output across five quality dimensions:

| Dimension | Score Range | What It Checks |
|-----------|------------|----------------|
| **Relevance** | 0.0 - 1.0 | Does the output directly address the prompt? |
| **Coherence** | 0.0 - 1.0 | Is the output well-structured and logically consistent? |
| **Completeness** | 0.0 - 1.0 | Does the output cover all requested points? |
| **Instruction Following** | 0.0 - 1.0 | Does the output respect constraints and format requirements? |
| **Hallucination Risk** | 0.0 - 1.0 | Is the output free from fabricated or unsupported claims? (higher = safer) |

### 2b. Email Creation Prompts Output Quality

When the **Email Creation Prompts** task type is selected, the output quality evaluation uses email-specific dimensions instead of the general ones above:

| Dimension | Score Range | What It Checks |
|-----------|------------|----------------|
| **Tone Appropriateness** | 0.0 - 1.0 | Does the email use the right tone for the audience and context? (formal, casual, empathetic, etc.) |
| **Professional Email Structure** | 0.0 - 1.0 | Does the output follow proper email conventions? (greeting, body paragraphs, clear call-to-action, sign-off) |
| **Audience Fit** | 0.0 - 1.0 | Is the language, detail level, and framing appropriate for the intended recipient? |
| **Purpose Achievement** | 0.0 - 1.0 | Does the email clearly accomplish its stated goal? (request, inform, persuade, follow up, etc.) |
| **Conciseness & Clarity** | 0.0 - 1.0 | Is the email free of unnecessary filler, jargon, or ambiguity while remaining complete? |

### 2c. Summarization Prompts Output Quality

When the **Summarization Prompts** task type is selected, the output quality evaluation uses summarization-specific dimensions:

| Dimension | Score Range | What It Checks |
|-----------|------------|----------------|
| **Information Accuracy** | 0.0 - 1.0 | Does the summary accurately represent the source material? Are all facts correctly stated? |
| **Logical Structure** | 0.0 - 1.0 | Is the summary logically organized with a clear, coherent flow? |
| **Key Information Coverage** | 0.0 - 1.0 | Were all essential points, findings, and conclusions from the source captured? |
| **Source Fidelity** | 0.0 - 1.0 | Does the summary stay faithful to the source without adding interpretation or opinion? |
| **Conciseness & Precision** | 0.0 - 1.0 | Is every sentence purposeful and precise? Does it avoid unnecessary repetition or filler? |

### 2d. Coding Task Prompts Output Quality

When the **Coding Task Prompts** task type is selected, the output quality evaluation uses coding-specific dimensions:

| Dimension | Score Range | What It Checks |
|-----------|------------|----------------|
| **Code Correctness** | 0.0 - 1.0 | Does the generated code have correct syntax, logic, and produce expected functionality? |
| **Code Quality** | 0.0 - 1.0 | Does the code follow best practices — readability, naming conventions, documentation, SOLID principles? |
| **Requirements Coverage** | 0.0 - 1.0 | Does the code implement ALL specified requirements from the prompt? |
| **Error Handling & Security** | 0.0 - 1.0 | Does the code include proper input validation, error handling, and avoid security vulnerabilities? |
| **Maintainability** | 0.0 - 1.0 | Is the code well-structured, testable, and easily extensible for future changes? |

### 2e. Exam Interview Agent Prompts Output Quality

When the **Exam Interview Agent Prompts** task type is selected, the output quality evaluation uses assessment-specific dimensions:

| Dimension | Score Range | What It Checks |
|-----------|------------|----------------|
| **Question Quality** | 0.0 - 1.0 | Are the questions clear, unambiguous, and well-structured for the target assessment? |
| **Assessment Coverage** | 0.0 - 1.0 | Does the assessment proportionally cover all specified topics and learning objectives? |
| **Difficulty Calibration** | 0.0 - 1.0 | Does the difficulty match the specified level and distribution (e.g., Bloom's taxonomy)? |
| **Rubric Completeness** | 0.0 - 1.0 | Is the scoring guide thorough, fair, and actionable for consistent grading? |
| **Fairness & Objectivity** | 0.0 - 1.0 | Is the assessment free from bias, cultural assumptions, and trick questions? |

### 2f. LinkedIn Professional Post Prompts Output Quality

When the **LinkedIn Professional Post Prompts** task type is selected, the output quality evaluation uses LinkedIn-specific dimensions:

| Dimension | Score Range | What It Checks |
|-----------|------------|----------------|
| **Professional Tone Authenticity** | 0.0 - 1.0 | Does the post use an authentic professional voice appropriate for the author and audience? |
| **Hook / Scroll-Stopping Power** | 0.0 - 1.0 | Does the opening line grab attention and compel readers to click "see more"? |
| **Audience Engagement Potential** | 0.0 - 1.0 | Is the content likely to generate meaningful comments, shares, and professional discussion? |
| **Value Delivery / Expertise** | 0.0 - 1.0 | Does the post deliver actionable insights, expertise, or unique perspective? |
| **LinkedIn Platform Optimization** | 0.0 - 1.0 | Does the post follow LinkedIn best practices (formatting, hashtags, length, readability)? |

### Grading Scale

| Grade | Score Range | Meaning |
|-------|------------|---------|
| Excellent | 85-100 | All dimensions well-covered |
| Good | 65-84 | Most dimensions present, minor gaps |
| Needs Work | 40-64 | Key dimensions missing |
| Weak | 0-39 | Minimal prompt structure |

### Always-Enhanced Evaluation (CoT+ToT+Meta)

Every evaluation automatically applies all three advanced AI techniques — no strategy selection or configuration needed. These techniques work together to produce more accurate, well-reasoned, and trustworthy evaluations:

| Technique | Applied In | What It Does |
|-----------|-----------|-------------|
| **Chain-of-Thought (CoT)** | Analysis | The LLM reasons step-by-step through each T.C.R.E.I. dimension before scoring, producing more consistent and explainable results. The full reasoning trace is captured in the audit report so you can see exactly how each score was derived |
| **Tree-of-Thought (ToT)** | Improvements | Instead of generating a single set of improvements, the system explores multiple distinct improvement branches simultaneously (default: 3 branches). Each branch proposes a different approach with its own confidence score. The system then selects or synthesizes the strongest path. The branch exploration is captured in the audit report showing each approach, its confidence, and why the best was chosen |
| **Meta-Evaluation** | Post-Improvements | A self-assessment pass evaluates the quality of the evaluation itself — scoring accuracy (did it assess the prompt correctly?), completeness (did it cover all aspects?), actionability (are the suggestions implementable?), faithfulness (does it stay grounded in the prompt?), and overall confidence (0-100%). This acts as a quality gate on the evaluation output |

### Multi-Execution Validation & Composite Improvement

Both the original and optimized prompts are executed **N times** (configurable 2-5 via the settings widget, default 2) to ensure output reliability. Running prompts more than once reveals whether the LLM produces consistent quality or varies between attempts. Executions run concurrently for speed.

The audit report includes a **Quality Comparison** section showing:
- Per-dimension scores for original vs optimized outputs
- Improvement deltas per dimension (e.g., Relevance: 72% → 89%, +17%)
- **Composite Improvement Score** — a weighted metric combining all four engines:
  - T.C.R.E.I. structural gap (25%), Output quality delta (35%), Meta-evaluation confidence (20%), ToT branch confidence (20%)
- Per-engine breakdown showing each engine's contribution to the composite score

### The Evaluate → Optimize → Validate Loop

This is the core value proposition of the tool — a complete closed-loop prompt quality assurance pipeline:

1. **Evaluate** — Your original prompt is analyzed structurally (T.C.R.E.I. with CoT reasoning) and its output is scored (LLM-as-Judge after N executions)
2. **Optimize** — The system generates an improved prompt using Tree-of-Thought branching, exploring multiple approaches and synthesizing the best
3. **Validate** — The optimized prompt is executed N times and its output is scored using the same LLM-as-Judge criteria, producing a direct quality comparison against the original
4. **Verify** — Meta-evaluation checks the entire assessment for accuracy and confidence
5. **Test in Production** — Switch to the "Test your optimized prompts" profile, paste the optimized prompt, and see the actual output for yourself

The audit report captures every step of this loop — from CoT reasoning to ToT branch exploration to side-by-side quality comparison — giving you full transparency into how your prompt was evaluated and improved.

---

## Installation Guide

### Prerequisites

Before starting, install the following tools on your machine:

#### 1. Python 3.12+

Python is the runtime for the entire application.

| Platform | Install Method |
|----------|---------------|
| **macOS** | `brew install python@3.12` or download from [python.org](https://www.python.org/downloads/) |
| **Ubuntu/Debian** | `sudo apt update && sudo apt install python3.12 python3.12-venv` |
| **Windows** | Download installer from [python.org](https://www.python.org/downloads/) (check "Add to PATH") |

Verify: `python --version` (should show 3.12.x or higher)

#### 2. uv (Python Package Manager)

[uv](https://docs.astral.sh/uv/) is a modern Python package manager that replaces pip. It's 10-100x faster and handles virtual environments automatically.

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip (any platform)
pip install uv
```

Verify: `uv --version`

#### 3. Docker & Docker Compose

Docker runs the PostgreSQL database (with pgvector), pgAdmin, and Ollama (embedding model). Docker Compose v2 is included with Docker Desktop.

| Platform | Install Method |
|----------|---------------|
| **macOS** | Download [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) |
| **Windows** | Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) (requires WSL 2) |
| **Linux** | Follow [Docker Engine install guide](https://docs.docker.com/engine/install/) + [Compose plugin](https://docs.docker.com/compose/install/linux/) |

Verify:
```bash
docker --version          # Docker 24+ recommended
docker compose version    # Compose v2+ required
```

#### 4. Git

Git is needed to clone the repository and manage branches.

| Platform | Install Method |
|----------|---------------|
| **macOS** | `xcode-select --install` (included with Xcode CLI tools) or `brew install git` |
| **Ubuntu/Debian** | `sudo apt install git` |
| **Windows** | Download from [git-scm.com](https://git-scm.com/downloads) |

Verify: `git --version`

#### 5. Make (optional but recommended)

The project includes a `Makefile` with shortcuts for common commands. Make is pre-installed on macOS and most Linux distributions.

| Platform | Install Method |
|----------|---------------|
| **macOS** | Pre-installed with Xcode CLI tools |
| **Ubuntu/Debian** | `sudo apt install make` |
| **Windows** | Install via [Chocolatey](https://chocolatey.org/): `choco install make`, or use [Git Bash](https://git-scm.com/) |

Verify: `make --version`

#### Quick Verification

Run these commands to confirm everything is ready:

```bash
python --version          # 3.12+
uv --version              # any version
docker --version          # 24+
docker compose version    # v2+
git --version             # any version
```

#### API Keys / Credentials Required

The application uses a **three-provider cascade** strategy: Google Gemini is the primary LLM, Anthropic Claude is the first fallback, and Ollama (self-hosted) is the second fallback. You need **at least one** configured.

| Provider | Priority | Get Credentials | Notes |
|----------|----------|-----------------|-------|
| **Google Vertex AI** (primary) | 1st | [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts) | Gemini 2.5 Flash via Vertex AI. Place `google-key.json` at `src/agent/nodes/google-key.json` |
| **Anthropic** (fallback) | 2nd | [console.anthropic.com](https://console.anthropic.com/) | Claude — used automatically if Google credentials are missing or fail |
| **Ollama** (self-hosted fallback) | 3rd | No API key needed | Qwen 3 4B via local Ollama server. Auto-started by `make docker-up`. Used if both cloud providers fail |

**Google Vertex AI setup:**
1. Go to [Google Cloud Console > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Create a service account with the **Vertex AI User** role
3. Generate a JSON key and save it as `src/agent/nodes/google-key.json`
4. Ensure the Vertex AI API is enabled in your project

**Anthropic setup:**
1. Go to [console.anthropic.com](https://console.anthropic.com/)
2. Create an API key
3. Add `ANTHROPIC_API_KEY=sk-ant-...` to your `.env` file

Optional but recommended:
- [LangSmith API key](https://smith.langchain.com/) for evaluation tracing and debugging

> **Note:** Embeddings are generated locally by [Ollama](https://ollama.com/) using the `nomic-embed-text` model (768 dimensions). Ollama runs as a Docker container alongside PostgreSQL — no additional API keys or cloud services are needed for embeddings.

### Recommended IDE

We recommend **[PyCharm](https://www.jetbrains.com/pycharm/)** (Professional or Community Edition) as the primary IDE for developing and testing this project. PyCharm provides:

- Built-in support for **pytest** with coverage visualization
- **Docker integration** for managing the PostgreSQL container
- **Database tools** for inspecting PostgreSQL tables and running queries
- **Python type checking** and Pydantic model support
- **`.env` file support** for environment variable management
- **Async debugging** for the async-first codebase

> **Tip:** After cloning, open the project root in PyCharm and it will auto-detect the `pyproject.toml` configuration. Configure the Python interpreter to use the uv-managed virtual environment (`.venv/` in the project root).

Other editors like VS Code, Cursor, or Neovim work fine too — the project has no IDE-specific dependencies.

### Step-by-Step Setup

```bash
# 1. Clone the repository
git clone https://github.com/innovacores/prompt-evaluator.git
cd prompt-evaluator

# 2. Install all dependencies (including dev tools)
uv sync --extra dev

# 2b. (Optional) Install OCR support for scanned PDFs
uv sync --extra ocr
# macOS: brew install tesseract  (needed for Tier 3 PyMuPDF OCR)

# 3. Create your environment file
cp .env.example .env
```

Now configure your LLM provider (at least one is required):

**Option A — Google Vertex AI (primary):**
```bash
# Place your service-account key file:
cp /path/to/your/service-account.json src/agent/nodes/google-key.json
```

**Option B — Anthropic Claude (fallback):**
Open `.env` and add your API key:
```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Optional:** Add LangSmith tracing:
```env
LANGCHAIN_API_KEY=your-langsmith-key-here
```

Continue setup:

```bash
# 4. Start PostgreSQL, pgAdmin, and Ollama (auto-pulls embedding model)
make docker-up

# 5. Run database migrations
make migrate

# 6. Start the application
make dev
```

Open your browser to **http://localhost:8000** and you're ready to go.

### One-Command Setup (Shortcut)

If you prefer, steps 2-5 can be run in one command:

```bash
make setup    # Installs deps, copies .env, starts DB, runs migrations
make dev      # Start the app
```

### Docker Deployment (Full Stack)

Run the entire application — including the Chainlit app — inside Docker. No local Python or uv required (only Docker).

#### Development (with hot reload)

Source code is mounted into the container. Chainlit runs with `-w` (watch mode) so changes to `src/` are picked up automatically.

```bash
# 1. Create your .env (if not done already)
cp .env.example .env
# Edit .env with your API keys

# 2. Start everything (app + PostgreSQL + Ollama + pgAdmin)
make docker-dev

# 3. Open http://localhost:8000
```

Edit files locally — the running container picks up changes via the volume mount and Chainlit's watch mode.

To stop: `make docker-dev-down`

#### Production

The app is baked into an optimized image (no source mounts, no watch mode). The container restarts automatically on failure.

```bash
# Build and start in detached mode
make docker-prod

# Open http://localhost:8000
```

To stop: `make docker-prod-down`

> **Note:** Both profiles start the infrastructure services (PostgreSQL, Ollama, pgAdmin) alongside the app. The `DATABASE_URL` and `OLLAMA_BASE_URL` are automatically overridden inside Docker to use internal container networking — no manual changes to `.env` needed.

---

## Usage Instructions

### Evaluating a Prompt

1. **Log in** — Use the configured admin credentials (default: `admin@prompteval.dev` / `evaluator2026`)
2. **Paste any prompt** into the chat input
3. **Watch the real-time progress** as each evaluation step completes with live scores
4. **Review the results**:
   - In-chat summary with per-dimension scores and grade
   - Downloadable HTML audit report with interactive dashboard
   - Prioritized improvement suggestions
   - Fully rewritten prompt

**Example input:**
```
Write me something about dogs
```

**What you get back:**
- Overall structural score with letter grade
- Dimension-by-dimension breakdown (Task, Context, References, Constraints)
- Output quality scores across 5 dimensions
- Specific improvement suggestions ranked by priority
- A rewritten prompt that fixes the identified gaps
- An HTML report you can download and share

### Chat Profiles

After logging in, a **profile selector** appears in the Chainlit header bar. Select a profile to configure the tool for your specific use case. The active profile persists across messages until you switch.

| Profile | Mode | Description |
|---------|------|-------------|
| **General Task Prompts** (default) | Evaluator | Standard T.C.R.E.I. framework evaluation — scores Task, Context, References, and Constraints using general-purpose sub-criteria. Output quality checks relevance, coherence, completeness, instruction following, and hallucination risk. Best for: any prompt that doesn't fit a specialized category. |
| **Email Creation Prompts** | Evaluator | Email-specific criteria — evaluates email purpose, recipient clarity, sender role, tone/style, professional structure, audience fit, purpose achievement, and conciseness. Weights emphasize Context (30%) and reduce References (15%). Best for: prompts that generate emails, replies, or professional correspondence. |
| **Summarization Prompts** | Evaluator | Summarization-specific criteria — evaluates source material description, summary type/format, length constraints, audience, hallucination safeguards, information accuracy, source fidelity, and conciseness. Weights emphasize References (30%) for source material. Best for: prompts that summarize documents, articles, or research papers. |
| **Coding Task Prompts** | Evaluator | Coding-specific criteria — evaluates programming language specification, requirements clarity, architecture guidance, code quality standards, error handling, and security. Output quality checks code correctness, quality, requirements coverage, error handling & security, and maintainability. Best for: prompts that generate code, scripts, or technical implementations. |
| **Exam Interview Agent Prompts** | Evaluator | Assessment-specific criteria — evaluates assessment objectives, question design, difficulty calibration (Bloom's taxonomy), rubric/scoring definition, candidate profile, fairness safeguards, and anti-cheating measures. Best for: prompts that create exams, quizzes, interview questions, or assessment rubrics. |
| **LinkedIn Professional Post Prompts** | Evaluator | LinkedIn-specific criteria — evaluates post objective, writing voice, content format, call-to-action, target audience, author identity, industry context, platform awareness, hashtag/mention requirements, and content exclusions. Weights emphasize Context (35%) and reduce References (15%). Output quality checks professional tone authenticity, hook/scroll-stopping power, audience engagement potential, value delivery/expertise, and LinkedIn platform optimization. Best for: prompts that generate LinkedIn posts, thought leadership content, or professional social media updates. |
| **Test your optimized prompts** | Direct Chat | Test your newly optimized prompts in real time and see the actual output for yourself — or use it as a full-featured LLM chat, just like Google AI Studio, Claude, or ChatGPT. Attach documents and images directly in the conversation. Features live token streaming (responses appear word-by-word), collapsible thinking/reasoning display, and support for text files (`.py`, `.md`, `.json`, `.csv`, and more), images (`.png`, `.jpg`, `.gif`, `.webp`), and documents (`.pdf`, `.docx`, `.xlsx`, `.pptx`). Uploaded documents are automatically parsed, chunked, vectorized, and available as RAG context. Switch between Google Gemini and Anthropic Claude using the in-chat settings widget. |

### Evaluating a System Prompt

Type `system prompt mode` to switch modes, then paste your system prompt:

```
You are a medical transcription assistant specializing in
converting audio recordings into structured SOAP notes...
```

The evaluator will analyze the system prompt's structure and assess whether it will reliably produce the expected behavior.

### Follow-Up Conversations

After an evaluation, you can ask follow-up questions naturally:

- *"Explain the context score in more detail"*
- *"Adjust the rewrite for a healthcare audience"*
- *"Re-evaluate with this updated prompt: [new prompt]"*
- *"Switch to system prompt mode"*

The tool automatically detects that these are follow-ups and responds accordingly — no need to restart.

### Customizing Evaluation Criteria

Edit `src/config/defaults/eval_config.yaml` to change:
- Dimension weights (how much each T.C.R.E.I. dimension counts)
- Grading scale thresholds
- Sub-criteria definitions

Add domain-specific configs in `src/config/defaults/domains/`:
- `healthcare.yaml` — Medical terminology and constraint expectations
- `software.yaml` — Technical prompt patterns

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 Chainlit Chat UI (:8000)                 │
│           Authentication + Real-Time Progress            │
└────────────────────────┬────────────────────────────────┘
                         v
┌─────────────────────────────────────────────────────────┐
│               LangGraph StateGraph                       │
│                                                           │
│  route_input ──> analyze_prompt (CoT) ──> score_prompt     │
│       |              |                        |            │
│       +──> analyze_system_prompt (CoT) ──+    |            │
│       |                                       v            │
│       |  +──[FULL]── run_prompt_for_output (Nx)            │
│       |  |                    |                            │
│       |  |           evaluate_output                       │
│       |  |                    |                            │
│       |  |                    v                            │
│       |  +───────> generate_improvements (ToT)             │
│       |  [STRUCTURE]─────+    |                            │
│       |                       v                            │
│       |           run_optimized_prompt (Nx)                 │
│       |                       |                            │
│       |           evaluate_optimized_output                 │
│       |                       |                            │
│       |                 meta_evaluate (always)              │
│       |                       |                            │
│       +─[OUTPUT]─> run_output ──> eval_output              │
│       |                               |                    │
│       |            build_report <─────+                    │
│       |                 v                                  │
│       |       conversation_loop ──> (repeat)               │
└───────┼──────────┬──────────────────┬────────────────────┘
        |          |                  |
   ┌────┴──────┐ ┌──────────────────────────┐ ┌──────────────────┐
   │PostgreSQL │ │  LangSmith               │ │ Gemini 2.5 Flash │
   │ (history  │ │  (traces + feedback)     │ │   (primary)      │
   │+ vectors) │ └──────────────────────────┘ │ Claude (fallback) │
   └───────────┘                              │ Ollama (fallback) │
                                              └──────────────────┘
```

### How the Pipeline Works

1. **Route Input** — Detects whether the input is a standard prompt, system prompt, or follow-up conversation
2. **Analyze Prompt (CoT)** — LLM evaluates each T.C.R.E.I. dimension with Chain-of-Thought reasoning; retrieves similar past evaluations via embeddings for context enrichment; captures reasoning trace
3. **Score Prompt** — Computes weighted scores per dimension and assigns an overall grade
4. **Run Prompt (Nx)** (Full mode) — Executes the user's prompt N times concurrently through an LLM, captures all outputs with graceful partial failure handling
5. **Evaluate Output** — LLM-as-Judge scores the aggregated output across 5 quality dimensions via LangSmith
6. **Generate Improvements (ToT)** — Tree-of-Thought exploration generates multiple improvement branches, selects/synthesizes the best, and produces a complete prompt rewrite with audit trail
7. **Run Optimized Prompt (Nx)** — Executes the rewritten prompt N times concurrently, capturing optimized outputs
8. **Evaluate Optimized Output** — LLM-as-Judge scores the optimized output for quality comparison
9. **Meta-Evaluate** — Self-assessment pass scores the evaluation's accuracy, completeness, actionability, faithfulness, and overall confidence
10. **Build Report** — Merges all results into a `FullEvaluationReport` with CoT trace, ToT branches, quality comparison, and stores the evaluation embedding for future self-learning
11. **Conversation Loop** — Handles follow-ups without re-running the full pipeline

---

## Technologies Used

Every technology in this project was chosen for a specific reason. Here's the full stack and why each piece is here:

### Core Agent Framework

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **[LangGraph](https://langchain-ai.github.io/langgraph/)** | Agent orchestration | Provides a stateful, graph-based workflow with conditional routing between nodes — essential for the multi-step evaluation pipeline with branching logic (structure-only vs full vs output-only) |
| **[LangChain](https://python.langchain.com/)** | LLM abstraction layer | Unified interface for LLM interactions with structured output parsing, prompt templates, and embeddings integration via LangChain's provider ecosystem |
| **[LangSmith](https://smith.langchain.com/)** | Observability and tracing | Full evaluation pipeline tracing with per-dimension feedback scores. Critical for debugging multi-step LLM chains and monitoring evaluation quality over time |

### LLM Providers

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **[Google Gemini](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini) (2.5 Flash)** | Primary LLM provider | Fast, cost-effective model via Vertex AI. Used for all analysis, scoring, improvement generation, and output quality evaluation when Google credentials are available |
| **[Anthropic Claude](https://docs.anthropic.com/)** | Fallback LLM provider | Industry-leading instruction-following. Automatically used when Google credentials are missing or initialization fails |
| **[Ollama](https://ollama.com/) (Qwen 3 4B)** | Self-hosted fallback LLM | Free, local LLM via Ollama. Automatically used when both cloud providers fail. No API key required — runs in Docker alongside PostgreSQL |

### User Interface

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **[Chainlit](https://docs.chainlit.io/)** | Chat UI framework | Purpose-built for LLM applications with built-in features: real-time streaming, step-by-step display, file attachments (for the HTML audit report), password authentication, and session management — all without writing frontend code |

### Data & Storage

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **[PostgreSQL](https://www.postgresql.org/)** | Primary database | Production-grade relational database for evaluation history, config snapshots, and user data. Chosen over SQLite for concurrent access and pgvector support |
| **[pgvector](https://github.com/pgvector/pgvector)** | Vector similarity search | Enables cosine similarity search on evaluation embeddings directly in PostgreSQL — no separate vector database needed. Powers the self-learning retrieval of similar past evaluations |
| **[SQLAlchemy](https://www.sqlalchemy.org/)** | ORM + async DB access | Async-first ORM with full type support. The `asyncpg` driver enables non-blocking database operations inside the async LangGraph pipeline |
| **[Alembic](https://alembic.sqlalchemy.org/)** | Database migrations | Schema version control for safe, repeatable database updates across environments |

### Configuration & Validation

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **[Pydantic](https://docs.pydantic.dev/)** | Data validation + models | Every data structure in the project is a Pydantic model — from evaluation results to LLM response schemas. Provides runtime validation, serialization, and `with_structured_output()` integration for reliable LLM parsing |
| **[Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)** | Environment configuration | Type-safe environment variable loading with `.env` file support and validation. No more `os.getenv()` with string defaults |
| **[PyYAML](https://pyyaml.org/)** | Evaluation config files | Human-readable configuration for dimension weights, grading scales, and domain-specific presets |

### Quality & Testing

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **[pytest](https://docs.pytest.org/)** | Test framework | Industry-standard Python testing with async support (`pytest-asyncio`), coverage enforcement (80% minimum via `pytest-cov`), and mock support (`pytest-mock`) for isolating LLM calls |
| **[Ruff](https://docs.astral.sh/ruff/)** | Linter + formatter | Replaces flake8, isort, and black in a single, fast tool. Enforces consistent code style across the project |
| **[MyPy](https://mypy-lang.org/)** | Static type checker | Strict mode enabled — catches type errors before runtime. Essential for a project with complex Pydantic models and LangChain integrations |

### Package Management & Build

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **[uv](https://docs.astral.sh/uv/)** | Python package manager | 10-100x faster than pip. Handles dependency resolution, virtual environments, and workspace management. Chosen over Poetry for speed and simplicity |
| **[Hatchling](https://hatch.pypa.io/)** | Build backend | Lightweight build system that works with the modern `pyproject.toml` standard. Minimal config needed |
| **[Docker Compose](https://docs.docker.com/compose/)** | Local infrastructure | One command to spin up PostgreSQL with pgvector, pgAdmin, and Ollama. Ensures consistent dev environments across machines |
| **[Ollama](https://ollama.com/)** | Local embedding model | Self-hosted embedding generation using `nomic-embed-text` (768 dimensions). Free, no API key required |

### Development Tooling

| Technology | Role | Why This Choice |
|-----------|------|-----------------|
| **[Claude Code](https://claude.com/claude-code) (Opus 4.6)** | AI-assisted development | Used for developing this project under human supervision. All code is reviewed and validated by the project maintainer before merging |

---

## Project Structure

```
prompt-evaluator/
├── CLAUDE.md                       # Claude Code project guide
├── .claude/                        # Claude Code configuration
│   ├── settings.json
│   └── commands/                   # Slash commands: /test, /lint, /dev, /migrate, /doc
├── Dockerfile                         # Multi-stage build (dev + production targets)
├── .dockerignore                      # Docker build context exclusions
├── docker/
│   ├── docker-compose.yml          # PostgreSQL + pgAdmin + Ollama + app (dev/prod profiles)
│   └── init.sql                    # Database schema with pgvector
├── alembic.ini                        # Alembic configuration
├── alembic/
│   ├── env.py                      # Alembic environment setup
│   └── versions/                   # Migration scripts
│       ├── 001_rename_langfuse_to_langsmith.py
│       ├── 002_change_embedding_dimension_to_768.py
│       ├── 003_add_thread_id_columns.py
│       └── 004_add_document_tables.py
├── public/
│   ├── icon.svg                    # Application logo (diamond + prompt cursor)
│   ├── logo_dark.svg               # Login page logo for dark theme (icon + text)
│   ├── logo_light.svg              # Login page logo for light theme (icon + text)
│   ├── favicon.svg                 # Browser tab favicon (SVG)
│   ├── favicon.ico                 # Browser tab favicon (ICO fallback)
│   ├── theme.json                  # Chainlit theme: primary color (indigo hsl(243, 75%, 59%))
│   ├── custom.css                  # Login page right panel + brand styling
│   └── custom.js                   # Favicon injection + login page intro panel
├── docs/
│   ├── ARCHITECTURE.md             # Detailed architecture documentation
│   └── diagrams/                   # Visual diagrams for external platforms
│       ├── architecture.eraser     # System architecture (eraser.io)
│       ├── langgraph-workflow.eraser # LangGraph node/edge topology (eraser.io)
│       ├── component-diagram.eraser  # Module dependencies (eraser.io)
│       ├── data-flow.eraser        # Data flow through pipeline (eraser.io)
│       └── database.dbml           # Database schema (dbdiagram.io)
├── src/
│   ├── app.py                      # Chainlit entry point (orchestrator) — auth, profiles, handlers
│   ├── ui/                         # UI helpers extracted from app.py
│   │   ├── __init__.py
│   │   ├── profiles.py             # Profile-to-task-type mapping, welcome messages, file constants
│   │   ├── thread_utils.py         # Chat counter + thread naming helper
│   │   ├── chat_handler.py         # Direct chat mode: streaming, thinking, attachments
│   │   ├── evaluation_runner.py    # LangGraph evaluation pipeline with real-time progress
│   │   ├── results_display.py      # Audit report generation + recommendations panel
│   │   └── audio_handler.py        # Audio transcription via Gemini
│   ├── agent/
│   │   ├── graph.py                # LangGraph workflow definition (nodes + edges)
│   │   ├── state.py                # AgentState TypedDict (all fields between nodes)
│   │   └── nodes/                  # One file per graph node
│   │       ├── router.py           # Intelligent input detection + mode routing + prompt type classification
│   │       ├── analyzer.py         # T.C.R.E.I. structural analysis via LLM (task-type-aware)
│   │       ├── scorer.py           # Weighted scoring + grade assignment (task-type-aware config loading)
│   │       ├── improver.py         # Improvement generation + context-aware prompt rewriting
│   │       ├── meta_evaluator.py   # Meta-evaluation self-assessment (accuracy, completeness, confidence)
│   │       ├── conversational.py   # Follow-up handler (explain, adjust, re-evaluate)
│   │       ├── output_runner.py    # Execute prompt N times through LLM, capture outputs
│   │       ├── output_evaluator.py # LLM-as-Judge scoring via LangSmith (task-type-aware) + optimized output eval
│   │       ├── optimized_runner.py # Execute optimized prompt N times through LLM
│   │       └── report_builder.py   # Merge structure + output + comparison into final report + store embeddings
│   ├── evaluator/
│   │   ├── __init__.py             # Pydantic domain models (scores, grades, reports, TaskType enum)
│   │   ├── criteria/               # T.C.R.E.I. criteria package
│   │   │   ├── __init__.py         # Registry + get_criteria_for_task_type()
│   │   │   ├── base.py             # Criterion dataclass
│   │   │   ├── general.py          # General task criteria (Task, Context, References, Constraints)
│   │   │   ├── email.py            # Email-specific criteria
│   │   │   ├── summarization.py    # Summarization-specific criteria
│   │   │   ├── coding.py           # Coding-specific criteria
│   │   │   ├── exam.py             # Exam/interview-specific criteria
│   │   │   └── linkedin.py         # LinkedIn-specific criteria
│   │   ├── example_prompts.py      # Annotated example prompts with T.C.R.E.I. breakdowns per task type
│   │   ├── exceptions.py           # Custom exception hierarchy (EvaluatorError, LLMError, etc.)
│   │   ├── llm_schemas.py          # Pydantic schemas for structured LLM output
│   │   ├── strategies.py           # Evaluation strategy presets (EvaluationStrategy enum, StrategyConfig)
│   │   └── service.py              # High-level PromptEvaluationService orchestrator
│   ├── prompts/
│   │   ├── __init__.py             # Re-exports all prompt constants from sub-modules
│   │   ├── general.py              # General analysis, improvement, output evaluation, followup prompts
│   │   ├── email.py                # Email-specific prompts
│   │   ├── summarization.py        # Summarization-specific prompts
│   │   ├── coding.py               # Coding-specific prompts
│   │   ├── exam.py                 # Exam/interview-specific prompts
│   │   ├── linkedin.py             # LinkedIn-specific prompts
│   │   ├── registry.py             # TaskTypePrompts dataclass + centralized task-type prompt registry
│   │   └── strategies/             # Strategy-specific prompt templates (CoT, ToT, Meta)
│   │       ├── __init__.py
│   │       ├── cot.py              # Chain-of-Thought prompts
│   │       ├── tot.py              # Tree-of-Thought prompts
│   │       └── meta.py             # Meta-evaluation prompts
│   ├── rag/
│   │   └── knowledge_store.py      # In-memory vector store for RAG retrieval (Ollama embeddings)
│   ├── knowledge/
│   │   ├── tcrei_framework.md      # T.C.R.E.I. framework reference document
│   │   └── scoring_guide.md        # Scoring rubrics with examples
│   ├── config/
│   │   ├── __init__.py             # Pydantic Settings (env var loading, lru_cache singleton)
│   │   ├── eval_config.py          # YAML config loader + grade calculation (task-type-aware)
│   │   └── defaults/               # YAML configs + domain presets
│   │       ├── eval_config.yaml                # General task type config
│   │       ├── email_writing_eval_config.yaml   # Email Creation Prompts task type config
│   │       ├── summarization_eval_config.yaml   # Summarization Prompts task type config
│   │       ├── coding_task_eval_config.yaml     # Coding Task Prompts task type config
│   │       ├── exam_interview_eval_config.yaml  # Exam Interview Agent Prompts task type config
│   │       ├── linkedin_post_eval_config.yaml   # LinkedIn Professional Post Prompts task type config
│   │       └── domains/
│   │           └── healthcare.yaml             # Healthcare-specific terminology and constraints
│   ├── db/
│   │   ├── __init__.py             # Async engine + session factory (thread-safe, double-checked locking)
│   │   ├── models.py               # SQLAlchemy ORM models (incl. pgvector Vector(768))
│   │   └── repository.py           # CRUD operations for evaluations + configs
│   ├── embeddings/
│   │   ├── __init__.py             # Module init
│   │   └── service.py              # Ollama embedding generation, storage, pgvector ORM similarity search
│   ├── documents/
│   │   ├── __init__.py              # Public API exports
│   │   ├── models.py               # Pydantic: DocumentMetadata, DocumentChunk, ExtractionEntity, ProcessingResult
│   │   ├── loader.py               # LangChain loaders: PyPDFLoader, Docx2txtLoader, etc. → text + metadata
│   │   ├── extractor.py            # LLM-based: raw text → structured entities
│   │   ├── chunker.py              # Document-specific chunking (RecursiveCharacterTextSplitter)
│   │   ├── vectorizer.py           # Ollama embeddings → pgvector storage
│   │   ├── retriever.py            # Document RAG: cosine similarity search on pgvector
│   │   ├── processor.py            # Orchestrator: load → extract → chunk → vectorize → store
│   │   └── exceptions.py           # DocumentProcessingError, UnsupportedFormatError
│   └── utils/
│       ├── example_formatter.py     # Markdown formatter for example prompt T.C.R.E.I. breakdowns
│       ├── llm_factory.py          # Centralized LLM provider factory (Google Gemini + Anthropic Claude + Ollama)
│       ├── langsmith_utils.py      # LangSmith client + feedback scoring helpers
│       ├── structured_output.py    # invoke_structured() with automatic fallback
│       ├── chunking.py             # Adaptive section-boundary chunking
│       ├── report_generator.py     # HTML audit report generator (Tailwind CSS)
│       ├── local_storage.py        # Local filesystem storage client for Chainlit file uploads
│       ├── custom_data_layer.py    # Custom Chainlit data layer (thread deletion cleanup)
│       └── logging_config.py       # Centralized logging setup (dev/prod formats, noisy logger silencing)
├── tests/
│   ├── unit/                       # Unit tests (all LLM calls mocked, 881 tests)
│   │   ├── test_analyzer.py        # Tests for analyzer node
│   │   ├── test_app.py             # Tests for Chainlit app handlers
│   │   ├── test_chat_handler.py   # Tests for chat mode helpers (thinking extraction, chunk deltas, file attachments)
│   │   ├── test_chunking.py        # Tests for adaptive chunking utilities
│   │   ├── test_coding_criteria.py # Tests for coding-specific evaluation criteria
│   │   ├── test_config.py          # Tests for Pydantic Settings
│   │   ├── test_conversational.py  # Tests for conversational follow-up node
│   │   ├── test_criteria.py        # Tests for general T.C.R.E.I. criteria
│   │   ├── test_criteria_registry.py # Tests for criteria registry completeness
│   │   ├── test_db_engine.py       # Tests for async DB engine/session factory
│   │   ├── test_db_models.py       # Tests for SQLAlchemy ORM models
│   │   ├── test_email_criteria.py  # Tests for email-specific evaluation criteria
│   │   ├── test_embedding_service.py # Tests for embedding generation and similarity search
│   │   ├── test_eval_config.py     # Tests for YAML config loading
│   │   ├── test_exam_criteria.py  # Tests for exam/interview-specific evaluation criteria
│   │   ├── test_example_formatter.py # Tests for example prompt Markdown formatter
│   │   ├── test_example_prompts.py # Tests for example prompts data module
│   │   ├── test_exceptions.py      # Tests for custom exception hierarchy
│   │   ├── test_graph.py           # Tests for LangGraph workflow definition
│   │   ├── test_improver.py        # Tests for improver node
│   │   ├── test_knowledge_store.py # Tests for RAG knowledge store
│   │   ├── test_langsmith_utils.py # Tests for LangSmith utilities
│   │   ├── test_linkedin_criteria.py # Tests for LinkedIn-specific evaluation criteria
│   │   ├── test_llm_factory.py     # Tests for LLM provider factory
│   │   ├── test_llm_schemas.py     # Tests for Pydantic LLM response schemas
│   │   ├── test_local_storage.py   # Tests for local filesystem storage client
│   │   ├── test_logging_config.py  # Tests for logging configuration
│   │   ├── test_models.py          # Tests for Pydantic domain models
│   │   ├── test_output_evaluator.py # Tests for output evaluator node
│   │   ├── test_output_runner.py   # Tests for output runner node (multi-execution)
│   │   ├── test_optimized_runner.py # Tests for optimized prompt runner node
│   │   ├── test_eval_optimized_output.py # Tests for optimized output evaluator node
│   │   ├── test_prompt_registry.py # Tests for centralized prompt registry
│   │   ├── test_prompts.py         # Tests for LLM prompt templates
│   │   ├── test_report_builder.py  # Tests for report builder node
│   │   ├── test_report_generator.py # Tests for HTML report generation
│   │   ├── test_repository.py      # Tests for DB repository CRUD
│   │   ├── test_router.py          # Tests for router node
│   │   ├── test_scorer.py          # Tests for scorer node
│   │   ├── test_structured_output.py # Tests for structured output helper
│   │   ├── test_summarization_criteria.py # Tests for summarization-specific evaluation criteria
│   │   ├── test_strategies.py         # Tests for evaluation strategy presets and resolution
│   │   ├── test_strategy_prompts.py   # Tests for strategy-specific prompt templates
│   │   ├── test_cot_integration.py    # Tests for Chain-of-Thought integration in analyzer/improver
│   │   ├── test_tot_integration.py    # Tests for Tree-of-Thought integration in improver
│   │   ├── test_meta_evaluator.py     # Tests for meta-evaluation node
│   │   ├── test_service.py            # Tests for PromptEvaluationService
│   │   ├── test_document_models.py    # Tests for document Pydantic models
│   │   ├── test_document_exceptions.py # Tests for document processing exceptions
│   │   ├── test_document_chunker.py   # Tests for document-specific chunking
│   │   ├── test_document_loader.py    # Tests for document file loaders
│   │   ├── test_document_processor.py # Tests for document processing orchestrator
│   │   ├── test_document_retriever.py # Tests for document RAG retriever
│   │   ├── test_document_vectorizer.py # Tests for document vectorizer
│   │   └── test_document_extractor.py # Tests for LLM-based entity extraction
│   ├── integration/                # Integration tests (requires DB)
│   └── fixtures/                   # Sample prompts with expected scores
├── pyproject.toml                  # Project config (deps, ruff, pytest, mypy)
├── Makefile                        # Common commands
└── .env.example                    # Environment variable template
```

---

## Development

### Commands

```bash
# Start the application (local Python, requires 'make docker-up' first)
make dev              # Launches Chainlit with hot reload on localhost:8000

# Docker — full stack (app + all infrastructure in Docker)
make docker-dev       # Build & start everything with hot-reload (-w), source mounted
make docker-dev-down  # Stop dev containers
make docker-prod      # Build & start production stack (detached, no watch, restart policy)
make docker-prod-down # Stop production containers

# Docker — infrastructure only (for local Python development)
make docker-up        # Start PostgreSQL + pgAdmin + Ollama containers, pull embedding model
make docker-down      # Stop infrastructure containers
make docker-reset     # Reset database (destroys all data)

# Testing
make test             # Run all tests with 80% coverage enforcement
make test-unit        # Run unit tests only (no external deps needed)
make test-integration # Run integration tests (requires running DB)

# Code quality
make lint             # Ruff check + MyPy strict mode
make format           # Auto-format with Ruff

# Database
make migrate          # Run pending Alembic migrations
make migration        # Create a new migration from model changes

# Maintenance
make clean            # Remove __pycache__, .pytest_cache, coverage artifacts
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Environment (`development` / `staging` / `production`) |
| `LOG_LEVEL` | `INFO` | Root logging level (`DEBUG` / `INFO` / `WARNING` / `ERROR`) |
| `GOOGLE_MODEL` | `gemini-2.5-flash` | Google Gemini model ID |
| `GOOGLE_PROJECT` | `gen-lang-client-0285221421` | Google Cloud project ID |
| `GOOGLE_LOCATION` | `us-central1` | Vertex AI region |
| `ANTHROPIC_API_KEY` | — | Anthropic API key for Claude (fallback) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Anthropic model ID |
| `LLM_TEMPERATURE` | `0.0` | LLM temperature |
| `LLM_MAX_TOKENS` | `16384` | Max tokens for LLM responses |
| `LANGCHAIN_TRACING_V2` | `true` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | `professional-prompt-shaper` | LangSmith project name |
| `DATABASE_URL` | `postgresql://...localhost:5432/prompt_evaluator` | PostgreSQL connection string |
| `OLLAMA_CHAT_MODEL` | `qwen3:4b` | Ollama chat model name (self-hosted fallback) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL for chat LLM and embeddings |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model for vectorization |
| `EMBEDDING_DIMENSIONS` | `768` | Embedding vector dimensions |
| `SIMILARITY_THRESHOLD` | `0.75` | Minimum cosine similarity for retrieval |
| `MAX_SIMILAR_RESULTS` | `5` | Max similar evaluations returned |
| `AUTH_ENABLED` | `true` | Enable/disable password authentication |
| `AUTH_SECRET_KEY` | `change-me-in-production` | Secret key for auth tokens |
| `AUTH_ADMIN_EMAIL` | `admin@prompteval.dev` | Admin login email |
| `AUTH_ADMIN_PASSWORD` | `evaluator2026` | Admin login password |
| `DEFAULT_EXECUTION_COUNT` | `2` | Number of times to execute each prompt (2-5) |
| `DOC_MAX_FILE_SIZE` | — | Maximum file size for uploaded documents |
| `DOC_CHUNK_SIZE` | — | Chunk size for document text splitting |
| `DOC_CHUNK_OVERLAP` | — | Overlap between document chunks |
| `DOC_MAX_CHUNKS_PER_QUERY` | — | Max chunks returned per RAG query |
| `DOC_ENABLE_EXTRACTION` | — | Enable/disable LLM-based entity extraction |
| `DOC_EXTRACTION_MODEL` | — | LLM model used for document entity extraction |
| `PDF_OCR_ENABLED` | `true` | Enable tiered OCR fallback for scanned/image-based PDFs |
| `PDF_OCR_MIN_TEXT_CHARS` | `50` | Minimum extracted characters before triggering OCR fallback |

### LangSmith Tracing

All evaluations are automatically traced to LangSmith when `LANGCHAIN_TRACING_V2=true`. View traces at [smith.langchain.com](https://smith.langchain.com) under your project name. Each evaluation includes per-dimension feedback scores for quality monitoring.

---

## Contributing

We welcome contributions from developers of all skill levels. Here's how to get involved:

### How to Contribute

1. **Fork the repository** and clone your fork locally
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Install dev dependencies**:
   ```bash
   uv sync --extra dev
   ```
4. **Make your changes** — follow the existing code style:
   - Python 3.11+ with full type hints
   - Google-style docstrings on all public functions
   - Async-first: use `async def` for all I/O operations
   - Pydantic models for all data structures
5. **Run quality checks** before committing:
   ```bash
   make lint     # Must pass with zero errors
   make test     # Must maintain 80%+ coverage
   ```
6. **Submit a Pull Request** with a clear description of what you changed and why

### Ways to Contribute

- **Add evaluation criteria** — New sub-criteria for T.C.R.E.I. dimensions
- **Add domain presets** — YAML configs for specific fields (legal, education, marketing, etc.)
- **Improve the knowledge base** — Expand `src/knowledge/` with better scoring guides and framework references
- **Report bugs** — Open an issue with reproduction steps
- **Suggest features** — Open a discussion with your use case
- **Improve documentation** — Fix typos, add examples, clarify instructions

### Code Quality Standards

- **80% minimum test coverage** — enforced by CI
- **Strict MyPy** — all functions must have type annotations
- **Ruff linting** — enforces consistent style
- All LLM calls in unit tests must be **mocked** — never hit real APIs in CI

---

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 Innovacores & Brandon

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

This is a **public collaboration project** — fork it, improve it, and share it back with the community.

---

## Authors & Links

**Brandon** — Creator & Maintainer

| | Link                                                              |
|---|-------------------------------------------------------------------|
| LinkedIn | [linkedin.com/in/bcolinad](https://www.linkedin.com/in/bcolinad/) |
| Google Prompting Certification | [skills.google/paths/2337](https://www.skills.google/paths/2337)  |
| Company | [Innovacores](https://innovacores.com)                            |

### Development Approach

This project was built using **[Claude Code](https://claude.com/claude-code)** (Opus 4.6) as an AI-assisted development tool, with all code written under human supervision and review. Every architectural decision, code change, and test was validated by the project maintainer before inclusion.

---

*Built with knowledge from Google's Prompting Essentials certification. If this tool helps you write better prompts, give it a star and share it with your team.*
