# Contributing to Professional Prompt Shaper

Thank you for your interest in contributing! This document provides guidelines
and information to make the contribution process smooth and effective.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
  - [Reporting Bugs](#reporting-bugs)
  - [Suggesting Features](#suggesting-features)
  - [Improving Documentation](#improving-documentation)
  - [Submitting Code Changes](#submitting-code-changes)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [License](#license)

## Code of Conduct

This project and everyone participating in it is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to
uphold this code. Please report unacceptable behavior to **bcolinad@gmail.com**.

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/prompt-evaluator.git
   cd prompt-evaluator
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/bcolinad/prompt-evaluator.git
   ```
4. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## How to Contribute

### Reporting Bugs

Before creating a bug report, please check the
[existing issues](https://github.com/bcolinad/prompt-evaluator/issues) to avoid
duplicates. When filing a bug report, use the
[Bug Report template](https://github.com/bcolinad/prompt-evaluator/issues/new?template=bug_report.yml)
and include:

- A clear and descriptive title
- Steps to reproduce the behavior
- Expected behavior vs. actual behavior
- Your environment (OS, Python version, Docker version if applicable)
- Relevant logs or screenshots

### Suggesting Features

Feature requests are welcome. Use the
[Feature Request template](https://github.com/bcolinad/prompt-evaluator/issues/new?template=feature_request.yml)
and describe:

- The problem your feature would solve
- Your proposed solution
- Any alternatives you have considered

### Improving Documentation

Documentation improvements are always appreciated. This includes:

- Fixing typos or clarifying existing docs
- Adding examples or tutorials
- Updating outdated information
- Translating documentation

Use the
[Documentation template](https://github.com/bcolinad/prompt-evaluator/issues/new?template=documentation.yml)
to propose documentation changes.

### Submitting Code Changes

For anything beyond trivial fixes, please open an issue first to discuss the
change. This helps avoid wasted effort and ensures alignment with the project
direction.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker & Docker Compose
- PostgreSQL (or use the Docker setup)

### Installation

```bash
# Install all dependencies including dev tools
uv sync --group dev

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys and settings

# Start infrastructure (PostgreSQL, Ollama, pgAdmin)
make docker-up

# Run database migrations
make migrate

# Verify everything works
make test
make lint
```

## Development Workflow

1. **Keep your fork up to date**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Make your changes** on a dedicated branch (not `main`).

3. **Run quality checks** before committing:
   ```bash
   make test     # Run tests with 80% coverage minimum
   make lint     # Run ruff + mypy
   make format   # Auto-format code
   ```

4. **Push** your branch and open a pull request.

## Coding Standards

This project follows strict coding standards. All contributions must adhere to:

- **Python 3.11+** with full type hints on all functions
- **Google-style docstrings** on all public functions
- **Absolute imports** from the `src` package
- **Async-first**: use `async def` for all IO operations
- **Pydantic models** for all data structures

### Linting & Formatting

- **Ruff** for linting and formatting
- **MyPy** for static type checking

Run `make lint` and `make format` before submitting. CI will reject code that
fails these checks.

### Testing

- **80% minimum coverage** is enforced
- Unit tests must mock LLM calls — never hit real APIs
- Integration tests use a test PostgreSQL or SQLite in-memory database
- Place test fixtures in `tests/fixtures/`

Run the full test suite with:

```bash
make test
```

## Commit Messages

Write clear, meaningful commit messages. Follow these conventions:

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Keep the first line under 72 characters
- Reference issues and PRs in the body when relevant

**Format**:

```
<type>: <short summary>

<optional body — explain what and why, not how>

Refs: #<issue-number>
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

**Examples**:

```
feat: add system prompt evaluation mode

Adds a new graph node that evaluates system prompts against expected
outcomes using the T.C.R.E.I. framework.

Refs: #42
```

```
fix: correct scoring weight for References dimension

The References dimension was using 25% instead of the configured 20%.

Refs: #58
```

## Pull Request Process

1. **Fill out the PR template** completely — PRs missing required information
   may be closed.
2. **Ensure all checks pass**: tests, linting, type checking, and coverage.
3. **Update documentation** if your change affects:
   - Public APIs or behavior
   - Project structure (new files added/removed)
   - Configuration (new environment variables)
   - Database schema
   - LangGraph workflow nodes or edges
4. **Keep PRs focused** — one logical change per PR. Large PRs are harder to
   review and more likely to have merge conflicts.
5. **Respond to review feedback** promptly. If you disagree with a suggestion,
   explain your reasoning.
6. A maintainer will merge your PR once it is approved and all checks pass.

### What to Expect

- **Acknowledgement** within 3 business days
- **Review** within 7 business days for most PRs
- Complex changes may require multiple review rounds

## License

By contributing to Professional Prompt Shaper, you agree that your
contributions will be licensed under the [MIT License](LICENSE). This means your
code can be freely used, modified, and distributed by anyone under the same
terms.

---

Thank you for helping make Professional Prompt Shaper better!
