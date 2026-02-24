# Robust Long-Prompt Handling — Token Budget Management

## Context

When users submit long prompts (especially with uploaded document context), the evaluator and optimization nodes fail silently. The root cause: context-length errors from LLM providers are not detected by `is_fatal_llm_error()`, so the pipeline catches them as generic exceptions and falls back to zero scores / empty improvements — giving the user the impression that "nothing works." Additionally, there is no pre-flight token validation or context truncation anywhere in the pipeline, so unbounded document context, RAG results, and historical evaluations accumulate until the LLM rejects the request.

**User problem:** "When the prompt is too long the evaluator and the optimization prompt failed totally."

## Root Causes Identified

1. **`_FATAL_PATTERNS` missing context-length errors** — `src/evaluator/exceptions.py:73-97` doesn't match "context length exceeded", "token limit", "input too long", etc.
2. **No pre-flight token validation** — No node estimates total tokens before calling the LLM.
3. **Document context injected unbounded** — `analyzer.py:234-237` and `improver.py:242-245` inject full `doc_context` without size limits.
4. **Improver doesn't chunk** — Sends full `input_text` + `analysis_summary` + `rag_section` + `output_quality_section` + ToT branches (3x full context).
5. **Output evaluator sends prompt+output unbounded** — `output_evaluator.py:52-53`.
6. **Meta-evaluator accumulates everything** — `meta_evaluator.py:81-88`.

## Changes

### 1. `src/evaluator/exceptions.py` — Detect context-length errors

Add context-length patterns to `_FATAL_PATTERNS` (line 73):
```python
# Context length / token limit
"context length",
"token limit",
"maximum context",
"input too long",
"request too large",
"content too large",
"prompt is too long",
"max_tokens",
"exceeds the model",
"request entity too large",
```

Add a dedicated `format_fatal_error` case (after line 145) for context-length errors with actionable guidance ("Your input is too long for the selected model. Try a shorter prompt or remove document attachments.").

### 2. `src/utils/token_budget.py` — New utility (small, focused)

Create a token budget management utility:

```python
_TOKEN_CHAR_RATIO = 4  # ~4 chars per token (reuse chunking.py's ratio)

def estimate_tokens(text: str) -> int
def truncate_to_budget(text: str, max_tokens: int, label: str = "") -> str
    """Truncate text to fit token budget, preserving start, adding [truncated] marker."""
def fit_context_sections(
    sections: dict[str, str],
    total_budget: int,
    priorities: list[str],
) -> dict[str, str]
    """Fit multiple context sections into a total budget, allocating by priority order."""
```

Key design: `fit_context_sections` allocates token budget to sections in priority order (e.g., `input_text` first, then `analysis_summary`, then `rag_context`, then `doc_context`). Lower-priority sections get truncated first.

### 3. `src/config/__init__.py` — Add token budget settings

```python
# Token budget management
llm_context_budget: int = Field(
    default=120_000,
    description="Max tokens per LLM call (conservative default for most models).",
)
doc_context_max_tokens: int = Field(
    default=4_000,
    description="Max tokens for injected document context.",
)
rag_context_max_tokens: int = Field(
    default=2_000,
    description="Max tokens for RAG knowledge context.",
)
```

### 4. `.env.example` — Add token budget env vars

```
# ── Token Budget Management ───────────────────────────
LLM_CONTEXT_BUDGET=120000
DOC_CONTEXT_MAX_TOKENS=4000
RAG_CONTEXT_MAX_TOKENS=2000
```

### 5. `src/agent/nodes/analyzer.py` — Apply token budgets

In `analyze_prompt()` (after line 231):
- Truncate `rag_section` to `settings.rag_context_max_tokens`
- Truncate `doc_section` to `settings.doc_context_max_tokens`

In `analyze_system_prompt()` (line 332-338):
- Same truncation for `rag_section` and `doc_section`

### 6. `src/agent/nodes/improver.py` — Apply token budgets + chunked improvement

In `generate_improvements()`:
- Truncate `rag_section` to `settings.rag_context_max_tokens`
- Truncate `doc_section` to `settings.doc_context_max_tokens`
- For `_generate_tot_improvements`: truncate `input_text` if it exceeds budget (it's duplicated in 3 branches)
- For the standard fallback path: same truncation

In `_generate_tot_improvements()`:
- Truncate `input_text` to fit within budget before injecting into branch generation prompt
- Truncate `branches_text` before selection prompt if it gets too long

### 7. `src/agent/nodes/output_runner.py` — Cap prompt size

In `run_prompt_for_output()`:
- Truncate `input_text` if it exceeds `settings.llm_context_budget` (with warning log)
- Note: this is the user's actual prompt being executed, so truncation is a last resort with a clear warning

### 8. `src/agent/nodes/output_evaluator.py` — Cap input sizes

In `evaluate_output()`:
- Truncate `llm_output` to fit within budget (LLM outputs can be very long)
- Use `fit_context_sections` to allocate budget between `input_text` and `llm_output`

In `evaluate_optimized_output()`:
- Same truncation for `optimized_summary`

### 9. `src/agent/nodes/meta_evaluator.py` — Cap accumulated context

In `meta_evaluate()`:
- Truncate `rewritten_prompt` if very long
- Use `fit_context_sections` for `input_text`, `dimension_summary`, `improvements_text`, `rewritten_prompt`

### 10. `tests/unit/test_token_budget.py` — Unit tests

- `estimate_tokens`: basic correctness
- `truncate_to_budget`: preserves text under budget, truncates over budget, adds marker
- `fit_context_sections`: allocates by priority, truncates low-priority first
- Edge cases: empty text, zero budget

### 11. `tests/unit/test_document_loader.py` — No changes needed (OCR tests already passing)

### 12. Update existing tests where context truncation affects mocked behavior

Review and update test mocks in:
- `tests/unit/test_analyzer.py` — Verify truncated context still flows correctly
- `tests/unit/test_improver.py` — Verify truncated context in ToT path

### 13. Documentation updates

- `README.md`: Token budget feature, 3 new env vars
- `docs/ARCHITECTURE.md`: New `token_budget.py` module, config reference, version history entry
- `.env.example`: Already covered in step 4

## Files to Modify

| File | Change |
|------|--------|
| `src/evaluator/exceptions.py` | Add context-length patterns + format case |
| `src/utils/token_budget.py` | **NEW** — token estimation + truncation utilities |
| `src/config/__init__.py` | Add 3 token budget settings |
| `.env.example` | Add 3 token budget env vars |
| `src/agent/nodes/analyzer.py` | Truncate RAG + doc context before LLM calls |
| `src/agent/nodes/improver.py` | Truncate context + cap ToT input size |
| `src/agent/nodes/output_runner.py` | Cap prompt size with warning |
| `src/agent/nodes/output_evaluator.py` | Cap input_text + llm_output sizes |
| `src/agent/nodes/meta_evaluator.py` | Cap accumulated context |
| `tests/unit/test_token_budget.py` | **NEW** — unit tests for budget utility |
| `README.md` | Token budget docs |
| `docs/ARCHITECTURE.md` | Module ref + version history |

## Verification

1. `make lint` — ruff + mypy pass
2. `make test` — all tests pass, 80%+ coverage
3. Manual test: submit a very long prompt (8000+ words) and verify:
   - Pipeline completes without silent zeros
   - Context is truncated with log warnings
   - User gets meaningful results or a clear error message
4. Manual test: submit prompt with large document attachment and verify truncation works
