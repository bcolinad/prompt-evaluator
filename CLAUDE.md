# Professional Prompt Shaper — Project Guide

## Overview

A conversational AI agent built with **LangGraph** that evaluates user prompts against Google's **T.C.R.E.I.** prompting framework (Task, Context, References, Evaluate, Iterate). It provides scoring, detailed analysis, actionable improvements, and rewritten prompts — all through a **Chainlit** chat interface with **LangSmith** tracing.

## Architecture

```
Chainlit Chat UI
    ↓
LangGraph StateGraph (agent/graph.py)
    ├── route_input        → Detect: prompt eval vs system prompt eval
    ├── analyze_prompt     → Parse T.C.R.E.I. dimensions
    ├── analyze_system     → Evaluate system prompts against expected outcomes
    ├── score_prompt       → LLM-powered scoring per dimension (0-100)
    ├── generate_improve   → Suggestions + full rewrite
    ├── save_results       → PostgreSQL + LangSmith trace
    ├── present_results    → Format for Chainlit display
    └── conversation_loop  → Handle follow-ups, re-evaluation
        ↓
PostgreSQL (evaluation history) + LangSmith (traces)
```

## Tech Stack

- **Agent**: LangGraph + LangChain + ChatAnthropic (Claude)
- **UI**: Chainlit
- **Tracing**: LangSmith
- **DB**: PostgreSQL via SQLAlchemy + Alembic
- **Config**: Pydantic Settings + YAML
- **Deps**: uv
- **Testing**: pytest + pytest-cov (80% minimum)
- **Linting**: ruff + mypy

## Key Conventions

### Code Style
- Python 3.11+, full type hints everywhere
- Google-style docstrings on all public functions
- Absolute imports from `src` package
- Async-first: use `async def` for all IO operations
- Pydantic models for all data structures

### Testing
- 80% minimum coverage enforced (`--cov-fail-under=80`)
- Unit tests mock LLM calls — never hit real APIs
- Integration tests use test PostgreSQL or SQLite in-memory
- Fixtures in `tests/fixtures/` for sample prompts with expected scores

### Project Structure
```
src/
├── app.py                         # Chainlit entry point
├── agent/
│   ├── graph.py                   # LangGraph StateGraph definition
│   ├── state.py                   # TypedDict state schema
│   └── nodes/                     # One file per graph node
│       ├── router.py
│       ├── analyzer.py
│       ├── scorer.py
│       ├── improver.py
│       └── conversational.py
├── evaluator/
│   ├── prompt_evaluator.py        # Core prompt evaluation logic
│   ├── system_prompt_evaluator.py # System prompt evaluation
│   ├── criteria.py                # Evaluation criteria definitions
│   └── models.py                  # Pydantic models for scores/results
├── prompts/
│   ├── templates.py               # All LLM prompt templates
│   └── *.md                       # Prompt template files
├── config/
│   ├── settings.py                # Pydantic Settings (env-based)
│   ├── eval_config.py             # YAML config loader
│   └── defaults/                  # YAML evaluation configs
├── db/
│   ├── engine.py                  # SQLAlchemy engine/session
│   ├── models.py                  # DB models
│   └── repository.py              # CRUD operations
└── utils/
    ├── formatting.py              # Display helpers
    └── langsmith_utils.py         # Custom LangSmith callbacks
```

## ⚠️ MANDATORY: Documentation Updates on Every Change

**Every time you add, modify, or remove a component, module, node, database table, feature, or dependency, you MUST update ALL of the following:**

### 1. `README.md`
- Features section (if new feature)
- Project Structure tree (if files added/removed)
- Commands section (if new make target)
- Configuration Reference (if new env var)
- Architecture diagram (if topology changes)

### 2. `docs/ARCHITECTURE.md`
- Module Reference tables
- Database Schema tables
- Evaluation Framework (if criteria change)
- Version History table (append every change with date)

### 3. Eraser.io Diagrams (`docs/diagrams/*.eraser`)
- `architecture.eraser` → New external services, major components
- `langgraph-workflow.eraser` → New/changed graph nodes or edges
- `component-diagram.eraser` → New modules, changed dependencies
- `data-flow.eraser` → New processing stages

### 4. Database Schema (`docs/diagrams/database.dbml`)
- New tables or columns
- Changed types or constraints
- New indexes
- Updated JSONB column schemas

### Checklist (run mentally before completing any task):
```
□ Did I add a new file?           → Update README tree + ARCHITECTURE module ref
□ Did I add a graph node?         → Update langgraph-workflow.eraser + ARCHITECTURE nodes table
□ Did I change the DB?            → Update database.dbml + ARCHITECTURE schema + init.sql
□ Did I add a feature?            → Update README features
□ Did I add a dependency?         → Update architecture.eraser if external service
□ Did I change eval criteria?     → Update ARCHITECTURE evaluation framework
□ Did I add an env var?           → Update .env.example + README config reference
```

**This is non-negotiable. Outdated documentation is a bug.**

---

## Commands

```bash
# Setup
uv sync                      # Install dependencies
uv sync --group dev          # Install with dev dependencies
cp .env.example .env         # Configure environment

# Development (local Python)
make docker-up               # Start PostgreSQL + Ollama + pgAdmin
make migrate                 # Run database migrations
make dev                     # Start Chainlit dev server (local)

# Docker full stack (app + infrastructure in Docker)
make docker-dev              # Dev mode: hot-reload (-w), source mounted
make docker-dev-down         # Stop dev containers
make docker-prod             # Production mode: optimized image, detached
make docker-prod-down        # Stop production containers

# Quality
make test                    # Run tests with coverage
make lint                    # Ruff + MyPy
make format                  # Auto-format code

# All-in-one
make setup                   # Full setup from scratch
```

## Evaluation Framework

### T.C.R.E.I. Dimensions

| Dimension | Weight | What It Checks |
|-----------|--------|----------------|
| Task | 30% | Action verb, specific deliverable, persona, output format |
| Context | 25% | Background, audience, goals, domain specificity |
| References | 20% | Examples, structured references, labeled materials |
| Constraints | 25% | Scope boundaries, length limits, format restrictions, exclusions |

### Grading Scale
- **Excellent** (85-100): All dimensions well-covered
- **Good** (65-84): Most dimensions present, minor gaps
- **Needs Work** (40-64): Key dimensions missing
- **Weak** (0-39): Minimal prompt structure

### Two Evaluation Modes
1. **Prompt Evaluation**: User pastes a prompt → full T.C.R.E.I. analysis
2. **System Prompt Evaluation**: User provides system prompt + expected outcome → evaluates whether the system prompt will reliably produce the desired result
