# Professional Prompt Shaper

**Create optimized prompts that bring real value to your day-to-day life** — coding, studying, writing, and beyond.

Built on the **T.C.R.E.I.** framework from Google's [Prompting Essentials](https://www.skills.google/paths/2337) certification, this platform evaluates your prompts using two complementary systems and lets you chat directly with leading LLMs.

---

## Chat Profiles

Select a profile from the header bar to configure the tool for your use case:

### Evaluator Profiles

- **General Task Prompts** (default) — Standard T.C.R.E.I. evaluation for any prompt type. Scores Task, Context, References, and Constraints using general-purpose sub-criteria.
- **Email Creation Prompts** — Email-specific criteria emphasizing tone, recipient clarity, professional structure, and purpose achievement. Context weight increased to 30%.
- **Summarization Prompts** — Summarization-specific criteria focused on source material description, summary format, length constraints, and information fidelity. References weight increased to 30%.
- **Coding Task Prompts** — Coding-specific criteria evaluating programming language specification, requirements clarity, architecture guidance, code quality standards, and security considerations.
- **Exam Interview Agent Prompts** — Assessment-specific criteria for exam and interview prompts, covering question design, difficulty calibration (Bloom's taxonomy), rubric definition, and fairness safeguards.
- **LinkedIn Professional Post Prompts** — LinkedIn-specific criteria evaluating post objective, writing voice, audience targeting, platform optimization, hook quality, and engagement potential. Context weight increased to 35%.

### Direct Chat

- **Test your optimized prompts** — The natural next step after evaluation: copy your optimized prompt from the audit report, switch to this profile, and paste it to see the actual LLM output. Compare how the improved prompt performs versus your original — closing the evaluate → optimize → validate loop in one place. Also works as a full-featured LLM chat — just like Google AI Studio, Claude, or ChatGPT. Attach documents and images directly in the conversation, exactly as you would in any modern AI chat. Features **live token streaming** (responses appear word-by-word), collapsible thinking/reasoning display, and support for text files (`.py`, `.md`, `.json`, `.csv`, and more) and images (`.png`, `.jpg`, `.gif`, `.webp`). Switch between Google Gemini and Anthropic Claude anytime using the in-chat settings widget.

---

## Two Evaluation Systems

**1. Structure Analysis (T.C.R.E.I.)** — Scores your prompt across four weighted dimensions:
- **Task** (30%) — Action verb, deliverable, persona, output format
- **Context** (25%) — Background, audience, goals, domain specificity
- **References** (20%) — Examples, structured materials, labeled inputs
- **Constraints** (25%) — Scope boundaries, length limits, format restrictions

**2. Output Quality (LLM-as-Judge)** — Executes your prompt through an LLM, then scores the result across five dimensions tailored to your selected profile (e.g., Relevance, Coherence, Completeness for general tasks; Code Correctness, Maintainability for coding tasks; Professional Tone, Hook Power, Engagement Potential for LinkedIn posts).

---

## Always-Enhanced Evaluation Pipeline

Every evaluation automatically applies three advanced AI techniques — no configuration needed:

**Chain-of-Thought (CoT)** — During analysis, the LLM reasons step-by-step through each T.C.R.E.I. dimension before scoring. This structured reasoning produces more accurate and consistent evaluations. The reasoning trace is captured in the audit report so you can see exactly how each score was derived.

**Tree-of-Thought (ToT)** — During improvement generation, the system explores multiple distinct improvement branches simultaneously (like brainstorming 3 different approaches), evaluates the confidence of each, and selects or synthesizes the strongest path. The branch exploration is captured in the audit report showing each approach and why the best was chosen.

**Meta-Evaluation** — After improvements are generated, a self-assessment pass evaluates the quality of the evaluation itself — scoring accuracy, completeness, actionability, faithfulness, and overall confidence. This acts as a quality gate on the evaluation output.

## Multi-Execution Validation & Composite Improvement

Both the original and the optimized prompt are executed **multiple times** (configurable 2-5 via the settings widget, default 2) to ensure output reliability. Running prompts more than once reveals whether the LLM produces consistent quality or varies between attempts. The audit report shows a **side-by-side quality comparison** between the original and optimized outputs with per-dimension score deltas.

The headline **Composite Improvement** percentage combines signals from all four evaluation engines:
- **T.C.R.E.I. Gap** (25%) — structural room for improvement identified
- **Output Quality Delta** (35%) — empirical quality gain from multi-execution validation
- **Meta-Evaluation Confidence** (20%) — assessment trustworthiness
- **ToT Exploration Confidence** (20%) — selected improvement branch confidence

The per-engine breakdown is shown in both the audit report comparison section and the chat summary.

---

## How It Works

1. **Select a profile** from the header bar (or use the default General Task)
2. **Paste any prompt** into the chat below
3. The evaluator runs a full professional audit in a single pass:
   - **Analyze** your prompt's structure using Chain-of-Thought reasoning across all T.C.R.E.I. dimensions
   - **Score** each dimension with configurable weights and assign an overall grade
   - **Execute** your original prompt N times through an LLM and evaluate the output quality
   - **Generate improvements** using Tree-of-Thought branching — exploring multiple approaches and selecting the best
   - **Execute the optimized prompt** N times and evaluate its output quality for comparison
   - **Meta-evaluate** the entire assessment for accuracy and confidence
4. Receive a detailed **audit report** (interactive HTML dashboard) with scores, CoT reasoning trace, ToT branch exploration, original vs optimized quality comparison, a word-level diff, and the optimized prompt
5. **Validate the optimized prompt** — Switch to the **Test your optimized prompts** profile, paste the optimized prompt, and see the real output. Compare the results against your original to confirm the improvement before using it in production

## Intelligent Detection

You don't need to tell the tool what you're doing — just type naturally:
- **Paste a prompt** — triggers full evaluation with real-time progress tracking
- **Ask a follow-up** (e.g., "explain the context score") — responds contextually without re-running the pipeline
- **System prompts** are auto-detected from signal phrases like "system prompt" or "system instruction"
- **Continuation prompts** (e.g., "now add error handling") are detected and rewritten while preserving context references

## Additional Features

- **LLM Provider Selector** — Switch between Google Gemini, Anthropic Claude, and Ollama Qwen 3 at runtime via the settings widget
- **Example Prompts** — Click "Show Example Prompt" on the welcome message for an annotated T.C.R.E.I. breakdown tailored to your selected profile
- **Prompt Comparison (Diff)** — Every audit report includes a word-level inline diff between your original prompt and the optimized rewrite
- **Interactive Audit Reports** — Self-contained HTML dashboards you can download and share
- **Self-Learning** — Past evaluations are vectorized; similar historical evaluations automatically enrich new analyses

---

*An [Innovacores](https://innovacores.com) open-source project by [Brandon](https://www.linkedin.com/in/bcolinad/). Select your profile and paste a prompt to begin.*
