"""Professional Audit Report generator — builds a self-contained HTML dashboard.

Injects evaluation data as JSON into a Tailwind CSS template that renders
client-side. Uses CSS Grid accordion transitions (grid-template-rows: 0fr/1fr)
to prevent content leakage.
"""

from __future__ import annotations

import difflib
import html
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.evaluator import (
        DimensionScore,
        FullEvaluationReport,
        Improvement,
        MetaAssessment,
        OutputDimensionScore,
        OutputEvaluationResult,
        ToTBranchesAuditData,
    )

# ---------------------------------------------------------------------------
# Word-level diff generator
# ---------------------------------------------------------------------------


def generate_diff_html(original: str, rewritten: str) -> str:
    """Generate word-level inline diff with color-coded HTML spans.

    Uses ``difflib.SequenceMatcher`` to compare words and produces
    green spans for additions and red strikethrough spans for deletions.
    All text is HTML-escaped before wrapping to prevent XSS.

    Args:
        original: The original prompt text.
        rewritten: The rewritten/optimized prompt text.

    Returns:
        HTML string with color-coded diff spans, or empty string if
        either input is empty.
    """
    if not original or not rewritten:
        return ""

    original_words = original.split()
    rewritten_words = rewritten.split()

    matcher = difflib.SequenceMatcher(None, original_words, rewritten_words)
    parts: list[str] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            parts.append(html.escape(" ".join(original_words[i1:i2])))
        elif tag == "replace":
            old = html.escape(" ".join(original_words[i1:i2]))
            new = html.escape(" ".join(rewritten_words[j1:j2]))
            parts.append(
                f'<span style="color:#ef4444;text-decoration:line-through;background:#fef2f2;padding:1px 3px;border-radius:3px;">{old}</span>'
            )
            parts.append(
                f'<span style="color:#16a34a;background:#f0fdf4;padding:1px 3px;border-radius:3px;">{new}</span>'
            )
        elif tag == "delete":
            old = html.escape(" ".join(original_words[i1:i2]))
            parts.append(
                f'<span style="color:#ef4444;text-decoration:line-through;background:#fef2f2;padding:1px 3px;border-radius:3px;">{old}</span>'
            )
        elif tag == "insert":
            new = html.escape(" ".join(rewritten_words[j1:j2]))
            parts.append(
                f'<span style="color:#16a34a;background:#f0fdf4;padding:1px 3px;border-radius:3px;">{new}</span>'
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# HTML Template — uses __PLACEHOLDER__ tokens replaced via str.replace()
# to avoid conflicts with JS ${...} template literals and CSS {...} braces.
# ---------------------------------------------------------------------------

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Prompt Shaper &mdash; Professional Audit Report</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32' fill='none'%3E%3Cpath d='M16 2 L28 12 L16 30 L4 12 Z' fill='%23E0E7FF' stroke='%236366F1' stroke-width='1.5' stroke-linejoin='round'/%3E%3Cpath d='M4 12 L16 16 L28 12' stroke='%236366F1' stroke-width='1' opacity='0.5'/%3E%3Cpath d='M16 2 L16 16' stroke='%236366F1' stroke-width='1' opacity='0.5'/%3E%3Cpath d='M12 7 L18 10 L12 13' stroke='%234F46E5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' fill='none'/%3E%3Ccircle cx='25' cy='5' r='1.5' fill='%23A78BFA'/%3E%3Cline x1='25' y1='2' x2='25' y2='8' stroke='%23A78BFA' stroke-width='0.8' stroke-linecap='round'/%3E%3Cline x1='22' y1='5' x2='28' y2='5' stroke='%23A78BFA' stroke-width='0.8' stroke-linecap='round'/%3E%3C/svg%3E">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        body { font-family: 'Inter', sans-serif; }

        /* Fixed Grid Transition: Prevents content leakage */
        .accordion-content {
            display: grid;
            grid-template-rows: 0fr;
            transition: grid-template-rows 0.35s cubic-bezier(0.4, 0, 0.2, 1);
            visibility: hidden;
        }
        .accordion-content.expanded {
            grid-template-rows: 1fr;
            visibility: visible;
            margin-top: 0.5rem;
        }
        .accordion-inner { overflow: hidden; }

        .rotate-icon { transition: transform 0.3s ease; }
        .rotate-icon.expanded { transform: rotate(180deg); }
    </style>
</head>
<body class="bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-4 min-h-screen">

<div class="max-w-4xl mx-auto space-y-3">

    <!-- Header Card -->
    <div class="bg-slate-900 dark:bg-slate-800 rounded-[2rem] p-6 text-white mb-6 shadow-2xl relative overflow-hidden border border-slate-700">
        <div class="relative z-10">
            <div class="flex items-center gap-3 mb-6">
                <svg width="28" height="28" viewBox="0 0 32 32" fill="none"><path d="M16 2 L28 12 L16 30 L4 12 Z" fill="#E0E7FF" stroke="#818CF8" stroke-width="1.5" stroke-linejoin="round"/><path d="M4 12 L16 16 L28 12" stroke="#818CF8" stroke-width="1" opacity="0.5"/><path d="M16 2 L16 16" stroke="#818CF8" stroke-width="1" opacity="0.5"/><path d="M12 7 L18 10 L12 13" stroke="#A5B4FC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="25" cy="5" r="1.5" fill="#C4B5FD"/><line x1="25" y1="2" x2="25" y2="8" stroke="#C4B5FD" stroke-width="0.8" stroke-linecap="round"/><line x1="22" y1="5" x2="28" y2="5" stroke="#C4B5FD" stroke-width="0.8" stroke-linecap="round"/></svg>
                <h2 class="text-xs font-black uppercase tracking-widest text-indigo-100">Professional Prompt Shaper &mdash; Professional Audit Report</h2>
            </div>
            __STRATEGY_BADGE__
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="bg-white/10 p-4 rounded-2xl border border-white/10 backdrop-blur-md">
                    <div class="text-[10px] font-black uppercase opacity-60 mb-1">T.C.R.E.I. Structure</div>
                    <div class="flex items-baseline gap-1">
                        <span class="text-3xl font-black">__STRUCT_SCORE__%</span>
                        <span class="text-[10px] font-bold text-indigo-400 uppercase">__STRUCT_GRADE__</span>
                    </div>
                    <div class="w-full bg-white/20 h-1 rounded-full mt-3">
                        <div class="bg-indigo-400 h-full rounded-full" style="width:__STRUCT_SCORE__%"></div>
                    </div>
                </div>
                <div class="bg-white/10 p-4 rounded-2xl border border-white/10 backdrop-blur-md">
                    <div class="text-[10px] font-black uppercase opacity-60 mb-1">Original Output</div>
                    <div class="flex items-baseline gap-1">
                        <span class="text-3xl font-black text-emerald-400">__OUTPUT_SCORE__%</span>
                        <span class="text-[10px] font-bold text-emerald-400 uppercase">__OUTPUT_GRADE__</span>
                    </div>
                    <div class="w-full bg-white/20 h-1 rounded-full mt-3">
                        <div class="bg-emerald-400 h-full rounded-full" style="width:__OUTPUT_SCORE__%"></div>
                    </div>
                </div>
                <div class="bg-white/10 p-4 rounded-2xl border border-white/10 backdrop-blur-md">
                    <div class="text-[10px] font-black uppercase opacity-60 mb-1">Optimized Output</div>
                    <div class="flex items-baseline gap-1">
                        <span class="text-3xl font-black text-cyan-400">__OPT_OUTPUT_SCORE__%</span>
                        <span class="text-[10px] font-bold text-cyan-400 uppercase">__OPT_OUTPUT_GRADE__</span>
                    </div>
                    <div class="w-full bg-white/20 h-1 rounded-full mt-3">
                        <div class="bg-cyan-400 h-full rounded-full" style="width:__OPT_OUTPUT_SCORE__%"></div>
                    </div>
                </div>
                <div class="bg-white/10 p-4 rounded-2xl border border-white/10 backdrop-blur-md">
                    <div class="text-[10px] font-black uppercase opacity-60 mb-1">Improvement</div>
                    <div class="flex items-baseline gap-1">
                        <span class="text-3xl font-black __DELTA_COLOR__">__DELTA_SIGN____DELTA__%</span>
                    </div>
                    <div class="text-[10px] mt-2 opacity-60">Composite Score</div>
                </div>
            </div>
        </div>
    </div>
        
    <!-- Optimized Prompt -->
    <div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <button onclick="toggleSection('optimized')" class="w-full flex items-center justify-between p-5 focus:outline-none group">
            <div class="flex items-center gap-4">
                <div class="p-3 rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 group-hover:scale-110 transition-transform">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>
                </div>
                <div class="text-left">
                    <h3 class="font-bold text-sm uppercase tracking-tight">Optimized Prompt</h3>
                    <p class="text-[10px] font-bold text-slate-400 uppercase">Actionable Result</p>
                </div>
            </div>
            <svg id="icon-optimized" class="rotate-icon text-slate-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
        <div id="content-optimized" class="accordion-content">
            <div class="accordion-inner px-5 pb-5">
                <div class="bg-slate-950 rounded-2xl p-4 font-mono text-[11px] text-slate-300 relative border border-slate-800">
                    <button onclick="copyPrompt()" class="absolute top-3 right-3 p-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg active:scale-95 transition-all">
                        <svg id="copy-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                    </button>
                    <div id="prompt-text" class="pr-8 leading-relaxed whitespace-pre-wrap">__OPTIMIZED_PROMPT__</div>
                </div>
            </div>
        </div>
    </div>
    
    __META_SECTION__
        
    __COMPARISON_SECTION__
    
    __TOT_SECTION__
    
    <!-- Structural Scorecard -->
    <div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm transition-all duration-300">
        <button onclick="toggleSection('structural')" class="w-full flex items-center justify-between p-5 focus:outline-none group">
            <div class="flex items-center gap-4">
                <div class="p-3 rounded-2xl bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 group-hover:scale-110 transition-transform">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                </div>
                <div class="text-left">
                    <h3 class="font-bold text-sm uppercase tracking-tight">Structural Scorecard</h3>
                    <p class="text-[10px] font-bold text-slate-400 uppercase">Engine: T.C.R.E.I. Validator</p>
                </div>
            </div>
            <svg id="icon-structural" class="rotate-icon text-slate-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
        <div id="content-structural" class="accordion-content">
            <div class="accordion-inner px-5 pb-5 space-y-3" id="inner-structural"></div>
        </div>
    </div>

    <!-- Quality Analysis -->
    <div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <button onclick="toggleSection('quality')" class="w-full flex items-center justify-between p-5 focus:outline-none group">
            <div class="flex items-center gap-4">
                <div class="p-3 rounded-2xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 group-hover:scale-110 transition-transform">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>
                </div>
                <div class="text-left">
                    <h3 class="font-bold text-sm uppercase tracking-tight">Quality Analysis</h3>
                    <p class="text-[10px] font-bold text-slate-400 uppercase">Engine: Prompt Output Quality Judge</p>
                </div>
            </div>
            <svg id="icon-quality" class="rotate-icon text-slate-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        </button>
        <div id="content-quality" class="accordion-content">
            <div class="accordion-inner px-5 pb-5 space-y-3" id="inner-quality"></div>
        </div>
    </div>

    __COT_SECTION__

    __DIFF_SECTION__

    <!-- Footer -->
    <div class="mt-12 pt-4 border-t border-slate-200 dark:border-slate-900 flex justify-between items-center opacity-40 px-2">
        <div class="flex items-center gap-1.5">
            <svg width="14" height="14" viewBox="0 0 32 32" fill="none"><path d="M16 2 L28 12 L16 30 L4 12 Z" fill="#E0E7FF" stroke="#6366F1" stroke-width="1.5" stroke-linejoin="round"/><path d="M4 12 L16 16 L28 12" stroke="#6366F1" stroke-width="1" opacity="0.5"/><path d="M16 2 L16 16" stroke="#6366F1" stroke-width="1" opacity="0.5"/><path d="M12 7 L18 10 L12 13" stroke="#4F46E5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="25" cy="5" r="1.5" fill="#A78BFA"/><line x1="25" y1="2" x2="25" y2="8" stroke="#A78BFA" stroke-width="0.8" stroke-linecap="round"/><line x1="22" y1="5" x2="28" y2="5" stroke="#A78BFA" stroke-width="0.8" stroke-linecap="round"/></svg>
            <span class="text-[9px] font-bold uppercase tracking-widest">Professional Prompt Shaper &mdash; T.C.R.E.I. Certified Audit</span>
        </div>
        <span class="text-[9px] font-mono tracking-tighter">EVAL_FULL // TCREI_V2</span>
    </div>

</div>

<script>
const tcreiData = __TCREI_JSON__;

const qualityData = __QUALITY_JSON__;

function render() {
    document.getElementById('inner-structural').innerHTML = tcreiData.map(item => `
        <div class="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-slate-100 dark:border-slate-800">
            <div class="flex justify-between items-center mb-3">
                <span class="text-[10px] font-black text-slate-400 uppercase">${item.label} Health</span>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded ${item.score > 80 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">${item.score}%</span>
            </div>
            <div class="space-y-3">
                <p class="text-[10px] font-mono bg-white dark:bg-slate-800 p-2 rounded-lg border border-slate-100 dark:border-slate-700 text-slate-500 italic leading-snug">${item.original}</p>
                <div>
                    <div class="text-[9px] font-bold text-indigo-500 uppercase mb-1">Recommendation</div>
                    <p class="text-[11px] font-bold text-slate-800 dark:text-slate-200">${item.rec}</p>
                </div>
            </div>
        </div>
    `).join('');

    document.getElementById('inner-quality').innerHTML = qualityData.map(m => `
        <div class="p-4 bg-slate-50 dark:bg-slate-800/50 rounded-2xl border border-slate-100 dark:border-slate-800">
            <div class="flex justify-between items-start mb-4">
                <div>
                    <div class="text-[10px] font-black uppercase text-slate-400">${m.name}</div>
                    <div class="text-[11px] font-bold text-slate-600 dark:text-slate-300">${m.desc}</div>
                </div>
                <div class="text-sm font-black text-indigo-500">${m.value}%</div>
            </div>
            <div class="grid grid-cols-2 gap-3">
                <div class="bg-rose-50 dark:bg-rose-900/10 p-2 rounded-xl border border-rose-100 dark:border-rose-900/20">
                    <div class="text-[9px] font-bold text-rose-600 uppercase mb-1">Issue</div>
                    <p class="text-[10px] font-medium text-rose-800 dark:text-rose-400 leading-tight">${m.issue}</p>
                </div>
                <div class="bg-emerald-50 dark:bg-emerald-900/10 p-2 rounded-xl border border-emerald-100 dark:border-emerald-900/20">
                    <div class="text-[9px] font-bold text-emerald-600 uppercase mb-1">Fix</div>
                    <p class="text-[10px] font-medium text-emerald-800 dark:text-emerald-400 leading-tight">${m.fix}</p>
                </div>
            </div>
        </div>
    `).join('');
}

function toggleSection(id) {
    const content = document.getElementById(`content-${id}`);
    const icon = document.getElementById(`icon-${id}`);
    const isExpanded = content.classList.contains('expanded');

    // Close others (exclusive accordion)
    document.querySelectorAll('.accordion-content').forEach(c => c.classList.remove('expanded'));
    document.querySelectorAll('.rotate-icon').forEach(i => i.classList.remove('expanded'));

    if (!isExpanded) {
        content.classList.add('expanded');
        icon.classList.add('expanded');
    }
}

function copyPrompt() {
    const text = document.getElementById('prompt-text').innerText;
    navigator.clipboard.writeText(text).then(() => {
        const icon = document.getElementById('copy-icon');
        const original = icon.innerHTML;
        icon.innerHTML = '<polyline points="20 6 9 17 4 12"></polyline>';
        setTimeout(() => { icon.innerHTML = original; }, 2000);
    });
}

render();
toggleSection('structural');
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Data mapping helpers
# ---------------------------------------------------------------------------


def _tcrei_item(
    dim: DimensionScore, improvements: list[Improvement]
) -> dict[str, object]:
    """Map a T.C.R.E.I. dimension to the template data format.

    Args:
        dim: A scored dimension with sub-criteria details.
        improvements: The full list of improvement suggestions.

    Returns:
        Dict with keys: label, score, original, rec.
    """
    found = [html.escape(sc.detail) for sc in dim.sub_criteria if sc.found]
    original = "; ".join(found) if found else "No specific elements detected."

    rec = "No changes required."
    for imp in improvements:
        if (
            dim.name.lower() in imp.title.lower()
            or dim.name.lower() in imp.suggestion.lower()
        ):
            rec = f"[{html.escape(imp.priority.value)}] {html.escape(imp.suggestion)}"
            break

    return {
        "label": html.escape(dim.name.title()),
        "score": dim.score,
        "original": original,
        "rec": rec,
    }


def _quality_item(dim: OutputDimensionScore) -> dict[str, object]:
    """Map an output quality dimension to the template data format.

    Args:
        dim: A scored output dimension.

    Returns:
        Dict with keys: name, value, desc, issue, fix.
    """
    pct = int(dim.score * 100)
    recommendation = getattr(dim, "recommendation", "") or ""
    if dim.score >= 0.85:
        issue = "None."
        fix = "Maintain current quality."
    else:
        issue = html.escape(dim.comment)
        if recommendation and recommendation not in ("", "No change needed."):
            fix = html.escape(recommendation)
        else:
            fix = (
                f"Improve {html.escape(dim.name.replace('_', ' '))} "
                f"scoring above 85% threshold."
            )

    return {
        "name": html.escape(dim.name.replace("_", " ").title()),
        "value": pct,
        "desc": html.escape(dim.comment),
        "issue": issue,
        "fix": fix,
    }


def _build_meta_section_html(meta: MetaAssessment) -> str:
    """Build the Meta-Evaluation accordion section HTML.

    Args:
        meta: The MetaAssessment with quality scores.

    Returns:
        HTML string for the meta-evaluation section.
    """
    scores = [
        ("Accuracy", meta.accuracy_score),
        ("Completeness", meta.completeness_score),
        ("Actionability", meta.actionability_score),
        ("Faithfulness", meta.faithfulness_score),
        ("Overall Confidence", meta.overall_confidence),
    ]
    bars = []
    for label, score in scores:
        pct = int(score * 100)
        color = "bg-emerald-400" if pct >= 80 else ("bg-amber-400" if pct >= 60 else "bg-rose-400")
        bars.append(
            f'<div class="flex items-center justify-between mb-2">'
            f'<span class="text-[10px] font-bold text-slate-500 uppercase w-32">{html.escape(label)}</span>'
            f'<div class="flex-1 mx-3 bg-slate-200 dark:bg-slate-700 h-2 rounded-full">'
            f'<div class="{color} h-full rounded-full" style="width:{pct}%"></div></div>'
            f'<span class="text-[10px] font-bold text-slate-600 dark:text-slate-300 w-10 text-right">{pct}%</span>'
            f'</div>'
        )
    bars_html = "\n".join(bars)

    return (
        '<div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">'
        '<button onclick="toggleSection(\'meta\')" class="w-full flex items-center justify-between p-5 focus:outline-none group">'
        '<div class="flex items-center gap-4">'
        '<div class="p-3 rounded-2xl bg-purple-50 dark:bg-purple-900/30 text-purple-600 group-hover:scale-110 transition-transform">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
        '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'
        '</svg></div>'
        '<div class="text-left">'
        '<h3 class="font-bold text-sm uppercase tracking-tight">Meta-Evaluation</h3>'
        '<p class="text-[10px] font-bold text-slate-400 uppercase">Engine: Self-Reflection Quality Assessment</p>'
        '</div></div>'
        '<svg id="icon-meta" class="rotate-icon text-slate-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'
        '</button>'
        '<div id="content-meta" class="accordion-content">'
        '<div class="accordion-inner px-5 pb-5">'
        '<div class="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-4 border border-slate-100 dark:border-slate-800">'
        f'{bars_html}'
        '</div></div></div></div>'
    )


def _build_cot_section_html(trace: str) -> str:
    """Build the Chain-of-Thought accordion section HTML.

    Args:
        trace: The captured CoT reasoning trace text.

    Returns:
        HTML string for the CoT section.
    """
    escaped = html.escape(trace)
    return (
        '<div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">'
        '<button onclick="toggleSection(\'cot\')" class="w-full flex items-center justify-between p-5 focus:outline-none group">'
        '<div class="flex items-center gap-4">'
        '<div class="p-3 rounded-2xl bg-blue-50 dark:bg-blue-900/30 text-blue-600 group-hover:scale-110 transition-transform">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
        '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
        '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>'
        '</svg></div>'
        '<div class="text-left">'
        '<h3 class="font-bold text-sm uppercase tracking-tight">Chain-of-Thought Analysis</h3>'
        '<p class="text-[10px] font-bold text-slate-400 uppercase">Engine: Step-by-Step T.C.R.E.I. Reasoning</p>'
        '</div></div>'
        '<svg id="icon-cot" class="rotate-icon text-slate-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'
        '</button>'
        '<div id="content-cot" class="accordion-content">'
        '<div class="accordion-inner px-5 pb-5">'
        '<div class="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-4 border border-slate-100 dark:border-slate-800">'
        f'<pre class="text-[11px] font-mono text-slate-600 dark:text-slate-300 whitespace-pre-wrap leading-relaxed">{escaped}</pre>'
        '</div></div></div></div>'
    )


def _build_tot_section_html(data: ToTBranchesAuditData) -> str:
    """Build the Tree-of-Thought accordion section HTML.

    Args:
        data: The ToT branches audit data.

    Returns:
        HTML string for the ToT section.
    """
    branches_html_parts = []
    for i, branch in enumerate(data.branches):
        is_selected = i == data.selected_branch_index
        badge = (
            '<span class="text-[9px] font-bold px-2 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 '
            'text-emerald-700 dark:text-emerald-400 ml-2">SELECTED</span>'
            if is_selected else ""
        )
        conf_pct = int(branch.confidence * 100)
        conf_color = "bg-emerald-400" if conf_pct >= 70 else ("bg-amber-400" if conf_pct >= 40 else "bg-rose-400")
        preview = html.escape(branch.rewritten_prompt_preview) if branch.rewritten_prompt_preview else "<em>No preview</em>"

        branches_html_parts.append(
            f'<div class="p-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-100 dark:border-slate-700 mb-2">'
            f'<div class="flex items-center justify-between mb-2">'
            f'<span class="text-[10px] font-bold text-slate-500 uppercase">Branch {i + 1}{badge}</span>'
            f'<span class="text-[10px] font-bold text-slate-600 dark:text-slate-300">{conf_pct}%</span>'
            f'</div>'
            f'<div class="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full mb-2">'
            f'<div class="{conf_color} h-full rounded-full" style="width:{conf_pct}%"></div></div>'
            f'<div class="text-[10px] text-slate-600 dark:text-slate-400 mb-1"><strong>Approach:</strong> {html.escape(branch.approach)}</div>'
            f'<div class="text-[10px] text-slate-500"><strong>Improvements:</strong> {branch.improvements_count} suggestions</div>'
            f'<div class="text-[10px] text-slate-500 mt-1 font-mono truncate">{preview}</div>'
            f'</div>'
        )
    branches_html = "\n".join(branches_html_parts)
    rationale = html.escape(data.selection_rationale)
    synth_label = " (synthesized)" if data.synthesized else ""

    return (
        '<div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">'
        '<button onclick="toggleSection(\'tot\')" class="w-full flex items-center justify-between p-5 focus:outline-none group">'
        '<div class="flex items-center gap-4">'
        '<div class="p-3 rounded-2xl bg-amber-50 dark:bg-amber-900/30 text-amber-600 group-hover:scale-110 transition-transform">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
        '<path d="M12 2v6"/><path d="M12 8l-4 4"/><path d="M12 8l4 4"/>'
        '<path d="M8 12l-3 3"/><path d="M8 12l3 3"/><path d="M16 12l-3 3"/><path d="M16 12l3 3"/>'
        '</svg></div>'
        '<div class="text-left">'
        '<h3 class="font-bold text-sm uppercase tracking-tight">Tree-of-Thought Optimization</h3>'
        '<p class="text-[10px] font-bold text-slate-400 uppercase">Engine: Multi-Branch Exploration</p>'
        '</div></div>'
        '<svg id="icon-tot" class="rotate-icon text-slate-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'
        '</button>'
        '<div id="content-tot" class="accordion-content">'
        '<div class="accordion-inner px-5 pb-5 space-y-2">'
        f'{branches_html}'
        f'<div class="mt-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-100 dark:border-slate-800">'
        f'<div class="text-[9px] font-bold text-indigo-500 uppercase mb-1">Selection Rationale{synth_label}</div>'
        f'<p class="text-[10px] text-slate-600 dark:text-slate-400">{rationale}</p>'
        f'</div>'
        '</div></div></div>'
    )


def _build_comparison_section_html(
    original: OutputEvaluationResult | None,
    optimized: OutputEvaluationResult | None,
    execution_count: int = 2,
    composite_breakdown: dict[str, object] | None = None,
) -> str:
    """Build the quality comparison accordion section HTML.

    Args:
        original: Original prompt output evaluation result.
        optimized: Optimized prompt output evaluation result.
        execution_count: Number of executions per prompt.
        composite_breakdown: Per-engine breakdown from _compute_composite_improvement().

    Returns:
        HTML string for the comparison section.
    """
    if not original or not optimized:
        return ""

    orig_pct = int(original.overall_score * 100)
    opt_pct = int(optimized.overall_score * 100)
    delta = opt_pct - orig_pct
    delta_sign = "+" if delta >= 0 else ""
    delta_color = "text-emerald-500" if delta > 0 else ("text-rose-500" if delta < 0 else "text-slate-500")

    # Per-dimension comparison
    dim_rows = []
    orig_dims = {d.name: d for d in original.dimensions}
    opt_dims = {d.name: d for d in optimized.dimensions}
    all_dim_names = list(dict.fromkeys(list(orig_dims.keys()) + list(opt_dims.keys())))

    for name in all_dim_names:
        o = orig_dims.get(name)
        p = opt_dims.get(name)
        o_pct = int(o.score * 100) if o else 0
        p_pct = int(p.score * 100) if p else 0
        d = p_pct - o_pct
        d_sign = "+" if d >= 0 else ""
        d_color = "text-emerald-600" if d > 0 else ("text-rose-600" if d < 0 else "text-slate-500")
        label = html.escape(name.replace("_", " ").title())
        dim_rows.append(
            f'<div class="flex items-center justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">'
            f'<span class="text-[10px] font-bold text-slate-500 uppercase w-36">{label}</span>'
            f'<span class="text-[10px] font-bold text-slate-600 w-12 text-center">{o_pct}%</span>'
            f'<span class="text-[10px] font-bold text-slate-600 w-12 text-center">{p_pct}%</span>'
            f'<span class="text-[10px] font-bold {d_color} w-12 text-right">{d_sign}{d}%</span>'
            f'</div>'
        )
    dim_html = "\n".join(dim_rows)

    # Engine contributions breakdown (only when composite data available)
    engine_breakdown_html = ""
    if composite_breakdown:
        cb = composite_breakdown
        engine_breakdown_html = (
            '<div class="mt-4 pt-3 border-t-2 border-dashed border-slate-200 dark:border-slate-700">'
            '<div class="text-[9px] font-black text-indigo-500 uppercase mb-2">Engine Contributions</div>'
            '<div class="grid grid-cols-2 gap-2">'
            f'<div class="flex justify-between text-[10px]">'
            f'<span class="font-bold text-slate-500">T.C.R.E.I. Gap</span>'
            f'<span class="font-bold text-slate-600 dark:text-slate-300">{cb["structural_signal_pct"]}% <span class="text-slate-400">(w:25%)</span></span>'
            f'</div>'
            f'<div class="flex justify-between text-[10px]">'
            f'<span class="font-bold text-slate-500">Output Quality</span>'
            f'<span class="font-bold text-slate-600 dark:text-slate-300">{cb["output_delta_sign"]}{cb["output_delta"]}% <span class="text-slate-400">(w:35%)</span></span>'
            f'</div>'
            f'<div class="flex justify-between text-[10px]">'
            f'<span class="font-bold text-slate-500">Meta Confidence</span>'
            f'<span class="font-bold text-slate-600 dark:text-slate-300">{cb["meta_confidence_pct"]}% <span class="text-slate-400">(w:20%)</span></span>'
            f'</div>'
            f'<div class="flex justify-between text-[10px]">'
            f'<span class="font-bold text-slate-500">ToT Confidence</span>'
            f'<span class="font-bold text-slate-600 dark:text-slate-300">{cb["tot_confidence_pct"]}% <span class="text-slate-400">(w:20%)</span></span>'
            f'</div>'
            '</div>'
            f'<div class="flex justify-between items-center mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">'
            f'<span class="text-[10px] font-black text-indigo-600 dark:text-indigo-400 uppercase">Composite Score</span>'
            f'<span class="text-sm font-black text-indigo-600 dark:text-indigo-400">{cb["composite_pct"]}%</span>'
            f'</div>'
            '</div>'
        )

    return (
        '<div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">'
        '<button onclick="toggleSection(\'comparison\')" class="w-full flex items-center justify-between p-5 focus:outline-none group">'
        '<div class="flex items-center gap-4">'
        '<div class="p-3 rounded-2xl bg-cyan-50 dark:bg-cyan-900/30 text-cyan-600 group-hover:scale-110 transition-transform">'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
        '<path d="M16 3h5v5"/><path d="M21 3l-7 7"/><path d="M8 21H3v-5"/><path d="M3 21l7-7"/>'
        '</svg></div>'
        '<div class="text-left">'
        '<h3 class="font-bold text-sm uppercase tracking-tight">Quality Comparison: Original vs Optimized</h3>'
        f'<p class="text-[10px] font-bold text-slate-400 uppercase">Engine: Multi-Execution Validation ({execution_count}x per prompt)</p>'
        '</div></div>'
        '<svg id="icon-comparison" class="rotate-icon text-slate-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'
        '</button>'
        '<div id="content-comparison" class="accordion-content">'
        '<div class="accordion-inner px-5 pb-5">'
        '<div class="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-4 border border-slate-100 dark:border-slate-800">'
        # Header row
        '<div class="flex items-center justify-between pb-2 mb-2 border-b-2 border-slate-200 dark:border-slate-700">'
        '<span class="text-[9px] font-black text-slate-400 uppercase w-36">Dimension</span>'
        '<span class="text-[9px] font-black text-slate-400 uppercase w-12 text-center">Original</span>'
        '<span class="text-[9px] font-black text-slate-400 uppercase w-12 text-center">Optimized</span>'
        '<span class="text-[9px] font-black text-slate-400 uppercase w-12 text-right">Delta</span>'
        '</div>'
        f'{dim_html}'
        # Overall row
        '<div class="flex items-center justify-between pt-3 mt-2 border-t-2 border-slate-300 dark:border-slate-600">'
        '<span class="text-[10px] font-black text-slate-700 dark:text-slate-200 uppercase w-36">Overall</span>'
        f'<span class="text-[10px] font-black text-slate-700 w-12 text-center">{orig_pct}%</span>'
        f'<span class="text-[10px] font-black text-slate-700 w-12 text-center">{opt_pct}%</span>'
        f'<span class="text-[11px] font-black {delta_color} w-12 text-right">{delta_sign}{delta}%</span>'
        '</div>'
        f'{engine_breakdown_html}'
        '</div></div></div></div>'
    )


def _compute_composite_improvement(
    struct_score: int,
    output_score: int,
    opt_output_score: int,
    meta_confidence: float | None,
    tot_branch_confidence: float | None,
) -> dict[str, object]:
    """Compute composite improvement score from all evaluation engines.

    Each engine contributes a normalized signal (0.0-1.0) with weights:
      - T.C.R.E.I. structural gap: 25%
      - Output quality delta: 35%
      - Meta-evaluation confidence: 20%
      - ToT branch confidence: 20%

    Args:
        struct_score: T.C.R.E.I. structural score (0-100).
        output_score: Original output quality score (0-100).
        opt_output_score: Optimized output quality score (0-100).
        meta_confidence: Meta-evaluation confidence (0.0-1.0), or None.
        tot_branch_confidence: ToT selected branch confidence (0.0-1.0), or None.

    Returns:
        Dict with composite_pct, structural_signal_pct, output_delta,
        output_delta_sign, meta_confidence_pct, tot_confidence_pct.
    """
    structural_signal = (100 - struct_score) / 100
    raw_delta = opt_output_score - output_score
    output_signal = max(0, raw_delta) / 100
    meta_signal = meta_confidence if meta_confidence is not None else 0.5
    tot_signal = tot_branch_confidence if tot_branch_confidence is not None else 0.5

    composite_raw = (
        structural_signal * 0.25
        + output_signal * 0.35
        + meta_signal * 0.20
        + tot_signal * 0.20
    )
    composite_pct = round(composite_raw * 100)

    delta_sign = "+" if raw_delta >= 0 else ""

    return {
        "composite_pct": composite_pct,
        "structural_signal_pct": round(structural_signal * 100),
        "output_delta": abs(raw_delta),
        "output_delta_sign": delta_sign,
        "meta_confidence_pct": round(meta_signal * 100),
        "tot_confidence_pct": round(tot_signal * 100),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_audit_data(report: FullEvaluationReport) -> dict[str, object]:
    """Extract template data from a FullEvaluationReport.

    Args:
        report: The combined evaluation report.

    Returns:
        Dict with keys: tcrei_data, quality_data, optimized_prompt,
        struct_score, struct_grade, output_score, output_grade.
    """
    structure = report.structure_result
    output = report.output_result

    # T.C.R.E.I. dimension data
    tcrei_data: list[dict[str, object]] = []
    if structure:
        for dim in structure.dimensions:
            tcrei_data.append(_tcrei_item(dim, structure.improvements))

    # Output quality data
    quality_data: list[dict[str, object]] = []
    if output:
        for out_dim in output.dimensions:
            quality_data.append(_quality_item(out_dim))

    # Scores
    struct_score = structure.overall_score if structure else 0
    struct_grade = structure.grade.value if structure else "N/A"
    output_score = int(output.overall_score * 100) if output else 0
    output_grade = output.grade.value if output else "N/A"

    # Optimized prompt: prefer top-level, fall back to structure
    optimized_prompt = report.rewritten_prompt or ""
    if not optimized_prompt and structure:
        optimized_prompt = structure.rewritten_prompt or ""

    # Word-level diff between original and optimized prompt
    diff_html = generate_diff_html(report.input_text, optimized_prompt)

    # Optimized output scores
    opt_output = report.optimized_output_result
    opt_output_score = int(opt_output.overall_score * 100) if opt_output else 0
    opt_output_grade = opt_output.grade.value if opt_output else "N/A"

    # Composite improvement from all four engines
    tot_confidence = None
    if report.tot_branches_data and report.tot_branches_data.branches:
        idx = report.tot_branches_data.selected_branch_index
        if 0 <= idx < len(report.tot_branches_data.branches):
            tot_confidence = report.tot_branches_data.branches[idx].confidence

    meta_confidence = (
        report.meta_assessment.overall_confidence if report.meta_assessment else None
    )

    composite = _compute_composite_improvement(
        struct_score=struct_score,
        output_score=output_score,
        opt_output_score=opt_output_score,
        meta_confidence=meta_confidence,
        tot_branch_confidence=tot_confidence,
    )
    delta = composite["composite_pct"]

    return {
        "tcrei_data": tcrei_data,
        "quality_data": quality_data,
        "optimized_prompt": optimized_prompt,
        "diff_html": diff_html,
        "struct_score": struct_score,
        "struct_grade": struct_grade,
        "output_score": output_score,
        "output_grade": output_grade,
        "opt_output_score": opt_output_score,
        "opt_output_grade": opt_output_grade,
        "delta": delta,
        "composite": composite,
        "execution_count": report.execution_count,
        "meta_assessment": report.meta_assessment,
        "strategy_used": report.strategy_used,
        "cot_reasoning_trace": report.cot_reasoning_trace,
        "tot_branches_data": report.tot_branches_data,
        "original_output_result": report.output_result,
        "optimized_output_result": report.optimized_output_result,
    }


def generate_audit_report(report: FullEvaluationReport) -> str:
    """Generate a self-contained HTML audit report from evaluation results.

    Builds JSON data arrays from the report, then injects them into the
    HTML template via placeholder replacement. All string values are
    HTML-escaped before JSON serialization, and ``</script>`` sequences
    are escaped to prevent XSS injection.

    Args:
        report: The combined evaluation report.

    Returns:
        Complete HTML string ready for file write or inline display.
    """
    data = build_audit_data(report)

    tcrei_json = json.dumps(data["tcrei_data"], ensure_ascii=False)
    quality_json = json.dumps(data["quality_data"], ensure_ascii=False)

    # XSS protection: escape </script> inside JSON payloads
    tcrei_json = tcrei_json.replace("</", "<\\/")
    quality_json = quality_json.replace("</", "<\\/")

    optimized = html.escape(str(data["optimized_prompt"]))

    # Build CoT section (only if trace present)
    cot_trace = data.get("cot_reasoning_trace")
    cot_section = _build_cot_section_html(cot_trace) if cot_trace else ""

    # Build ToT section (only if branch data present)
    tot_data = data.get("tot_branches_data")
    tot_section = _build_tot_section_html(tot_data) if tot_data else ""

    # Build comparison section (only if both original and optimized results present)
    comparison_section = _build_comparison_section_html(
        data.get("original_output_result"),
        data.get("optimized_output_result"),
        data.get("execution_count", 2),
        composite_breakdown=data.get("composite"),
    )

    # Build meta section (only if meta-assessment present)
    meta_assessment = data.get("meta_assessment")
    meta_section = _build_meta_section_html(meta_assessment) if meta_assessment else ""

    # Build strategy badge (always shown for enhanced)
    strategy_used = str(data.get("strategy_used", "standard"))
    if strategy_used != "standard":
        strategy_badge = (
            '<div class="mb-4">'
            '<span class="text-[9px] font-bold px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 uppercase tracking-wider">'
            f'Strategy: {html.escape(strategy_used)}'
            '</span></div>'
        )
    else:
        strategy_badge = ""

    # Build diff section (hidden when no diff available)
    diff_html = data.get("diff_html", "")
    if diff_html:
        diff_section = (
            '<div class="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm">'
            '<button onclick="toggleSection(\'diff\')" class="w-full flex items-center justify-between p-5 focus:outline-none group">'
            '<div class="flex items-center gap-4">'
            '<div class="p-3 rounded-2xl bg-violet-50 dark:bg-violet-900/30 text-violet-600 group-hover:scale-110 transition-transform">'
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">'
            '<path d="M12 3v18"/><path d="M3 12h18"/>'
            '</svg></div>'
            '<div class="text-left">'
            '<h3 class="font-bold text-sm uppercase tracking-tight">Prompt Comparison</h3>'
            '<p class="text-[10px] font-bold text-slate-400 uppercase">Word-Level Diff: Original vs Optimized</p>'
            '</div></div>'
            '<svg id="icon-diff" class="rotate-icon text-slate-400" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'
            '</button>'
            '<div id="content-diff" class="accordion-content">'
            '<div class="accordion-inner px-5 pb-5">'
            '<div class="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-4 border border-slate-100 dark:border-slate-800">'
            '<div class="flex items-center gap-4 mb-3">'
            '<span class="text-[9px] font-bold px-2 py-0.5 rounded bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400">Removed</span>'
            '<span class="text-[9px] font-bold px-2 py-0.5 rounded bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">Added</span>'
            '<span class="text-[9px] font-bold text-slate-400">Unchanged</span>'
            '</div>'
            f'<div class="text-[11px] leading-relaxed text-slate-700 dark:text-slate-300">{diff_html}</div>'
            '</div></div></div></div>'
        )
    else:
        diff_section = ""

    # Compute delta display values
    delta = data.get("delta", 0)
    delta_sign = "+" if delta >= 0 else ""
    delta_color = "text-emerald-400" if delta > 0 else ("text-rose-400" if delta < 0 else "text-slate-400")
    exec_count = data.get("execution_count", 2)

    result = _TEMPLATE
    result = result.replace("__TCREI_JSON__", tcrei_json)
    result = result.replace("__QUALITY_JSON__", quality_json)
    result = result.replace("__STRUCT_SCORE__", str(data["struct_score"]))
    result = result.replace("__STRUCT_GRADE__", html.escape(str(data["struct_grade"])))
    result = result.replace("__OUTPUT_SCORE__", str(data["output_score"]))
    result = result.replace("__OUTPUT_GRADE__", html.escape(str(data["output_grade"])))
    result = result.replace("__OPT_OUTPUT_SCORE__", str(data.get("opt_output_score", 0)))
    result = result.replace("__OPT_OUTPUT_GRADE__", html.escape(str(data.get("opt_output_grade", "N/A"))))
    result = result.replace("__DELTA_SIGN__", delta_sign)
    result = result.replace("__DELTA__", str(abs(delta)))
    result = result.replace("__DELTA_COLOR__", delta_color)
    result = result.replace("__EXEC_COUNT__", str(exec_count))
    result = result.replace("__OPTIMIZED_PROMPT__", optimized)
    result = result.replace("__COT_SECTION__", cot_section)
    result = result.replace("__TOT_SECTION__", tot_section)
    result = result.replace("__COMPARISON_SECTION__", comparison_section)
    result = result.replace("__META_SECTION__", meta_section)
    result = result.replace("__STRATEGY_BADGE__", strategy_badge)
    result = result.replace("__DIFF_SECTION__", diff_section)

    return result


# ---------------------------------------------------------------------------
# Similarity Report — lightweight HTML for past evaluations
# ---------------------------------------------------------------------------

_SIMILARITY_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Prompt Shaper &mdash; Past Evaluation</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='32' height='32' viewBox='0 0 32 32' fill='none'%3E%3Cpath d='M16 2 L28 12 L16 30 L4 12 Z' fill='%23E0E7FF' stroke='%236366F1' stroke-width='1.5' stroke-linejoin='round'/%3E%3Cpath d='M4 12 L16 16 L28 12' stroke='%236366F1' stroke-width='1' opacity='0.5'/%3E%3Cpath d='M16 2 L16 16' stroke='%236366F1' stroke-width='1' opacity='0.5'/%3E%3Cpath d='M12 7 L18 10 L12 13' stroke='%234F46E5' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' fill='none'/%3E%3Ccircle cx='25' cy='5' r='1.5' fill='%23A78BFA'/%3E%3Cline x1='25' y1='2' x2='25' y2='8' stroke='%23A78BFA' stroke-width='0.8' stroke-linecap='round'/%3E%3Cline x1='22' y1='5' x2='28' y2='5' stroke='%23A78BFA' stroke-width='0.8' stroke-linecap='round'/%3E%3C/svg%3E">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-slate-50 text-slate-900 p-6 min-h-screen">

<div class="max-w-4xl mx-auto space-y-5">

    <!-- Header Card -->
    <div class="bg-slate-900 rounded-2xl p-6 text-white shadow-xl">
        <div class="flex items-center gap-3 mb-4">
            <svg width="24" height="24" viewBox="0 0 32 32" fill="none"><path d="M16 2 L28 12 L16 30 L4 12 Z" fill="#E0E7FF" stroke="#818CF8" stroke-width="1.5" stroke-linejoin="round"/><path d="M4 12 L16 16 L28 12" stroke="#818CF8" stroke-width="1" opacity="0.5"/><path d="M16 2 L16 16" stroke="#818CF8" stroke-width="1" opacity="0.5"/><path d="M12 7 L18 10 L12 13" stroke="#A5B4FC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="25" cy="5" r="1.5" fill="#C4B5FD"/><line x1="25" y1="2" x2="25" y2="8" stroke="#C4B5FD" stroke-width="0.8" stroke-linecap="round"/><line x1="22" y1="5" x2="28" y2="5" stroke="#C4B5FD" stroke-width="0.8" stroke-linecap="round"/></svg>
            <h2 class="text-xs font-black uppercase tracking-widest text-indigo-100">Past Evaluation Report</h2>
        </div>
        <div class="flex items-center gap-6">
            <div class="bg-white/10 px-4 py-3 rounded-xl border border-white/10">
                <div class="text-[10px] font-bold uppercase opacity-60 mb-1">Score</div>
                <span class="text-2xl font-black">__SCORE__%</span>
            </div>
            <div class="bg-white/10 px-4 py-3 rounded-xl border border-white/10">
                <div class="text-[10px] font-bold uppercase opacity-60 mb-1">Grade</div>
                <span class="text-2xl font-black __GRADE_COLOR__">__GRADE__</span>
            </div>
            __OUTPUT_SCORE_BLOCK__
        </div>
    </div>

    <!-- Original Prompt -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
        <h3 class="text-xs font-black uppercase tracking-tight text-slate-400 mb-3">Original Prompt</h3>
        <p class="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">__ORIGINAL_PROMPT__</p>
    </div>

    __IMPROVEMENTS_BLOCK__

    __OPTIMIZED_BLOCK__

    <!-- Footer -->
    <div class="mt-8 pt-3 border-t border-slate-200 flex justify-between items-center opacity-40 px-1">
        <div class="flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 32 32" fill="none"><path d="M16 2 L28 12 L16 30 L4 12 Z" fill="#E0E7FF" stroke="#6366F1" stroke-width="1.5" stroke-linejoin="round"/><path d="M4 12 L16 16 L28 12" stroke="#6366F1" stroke-width="1" opacity="0.5"/><path d="M16 2 L16 16" stroke="#6366F1" stroke-width="1" opacity="0.5"/><path d="M12 7 L18 10 L12 13" stroke="#4F46E5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><circle cx="25" cy="5" r="1.5" fill="#A78BFA"/><line x1="25" y1="2" x2="25" y2="8" stroke="#A78BFA" stroke-width="0.8" stroke-linecap="round"/><line x1="22" y1="5" x2="28" y2="5" stroke="#A78BFA" stroke-width="0.8" stroke-linecap="round"/></svg>
            <span class="text-[9px] font-bold uppercase tracking-widest">Professional Prompt Shaper</span>
        </div>
        <span class="text-[9px] font-mono">SIMILARITY_REPORT</span>
    </div>

</div>

<script>
function copyPrompt() {
    const text = document.getElementById('optimized-text').innerText;
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById('copy-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
    });
}
</script>
</body>
</html>"""


def generate_similarity_report(eval_data: dict[str, object]) -> str:
    """Generate a lightweight HTML report for a similar past evaluation.

    Args:
        eval_data: Dict from ``find_similar_evaluations()`` with keys:
            ``input_text``, ``rewritten_prompt``, ``overall_score``,
            ``grade``, ``output_score``, ``improvements_summary``.

    Returns:
        Complete self-contained HTML string.
    """
    score = int(eval_data.get("overall_score", 0))
    grade = html.escape(str(eval_data.get("grade", "N/A")))
    original = html.escape(str(eval_data.get("input_text", "")))
    rewritten = eval_data.get("rewritten_prompt") or ""
    improvements_summary = eval_data.get("improvements_summary") or ""
    output_score = eval_data.get("output_score")

    # Grade color
    grade_color = "text-emerald-400" if score >= 85 else (
        "text-blue-400" if score >= 65 else (
            "text-amber-400" if score >= 40 else "text-red-400"
        )
    )

    # Output score block (only if present)
    if output_score is not None:
        output_pct = int(float(output_score) * 100)
        output_block = (
            '<div class="bg-white/10 px-4 py-3 rounded-xl border border-white/10">'
            '<div class="text-[10px] font-bold uppercase opacity-60 mb-1">Output Quality</div>'
            f'<span class="text-2xl font-black text-emerald-400">{output_pct}%</span>'
            "</div>"
        )
    else:
        output_block = ""

    # Improvements block
    if improvements_summary:
        escaped_improvements = html.escape(str(improvements_summary))
        improvements_block = (
            '<div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">'
            '<h3 class="text-xs font-black uppercase tracking-tight text-slate-400 mb-3">Improvements</h3>'
            f'<p class="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{escaped_improvements}</p>'
            "</div>"
        )
    else:
        improvements_block = ""

    # Optimized prompt block (only if present)
    if rewritten:
        escaped_rewritten = html.escape(str(rewritten))
        optimized_block = (
            '<div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">'
            '<h3 class="text-xs font-black uppercase tracking-tight text-slate-400 mb-3">Optimized Prompt</h3>'
            '<div class="bg-slate-950 rounded-xl p-4 font-mono text-[11px] text-slate-300 relative border border-slate-800">'
            '<button id="copy-btn" onclick="copyPrompt()" '
            'class="absolute top-3 right-3 px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white text-[10px] '
            'font-bold rounded-lg active:scale-95 transition-all">Copy</button>'
            f'<div id="optimized-text" class="pr-16 leading-relaxed whitespace-pre-wrap">{escaped_rewritten}</div>'
            "</div></div>"
        )
    else:
        optimized_block = ""

    result = _SIMILARITY_TEMPLATE
    result = result.replace("__SCORE__", str(score))
    result = result.replace("__GRADE__", grade)
    result = result.replace("__GRADE_COLOR__", grade_color)
    result = result.replace("__OUTPUT_SCORE_BLOCK__", output_block)
    result = result.replace("__ORIGINAL_PROMPT__", original)
    result = result.replace("__IMPROVEMENTS_BLOCK__", improvements_block)
    result = result.replace("__OPTIMIZED_BLOCK__", optimized_block)

    return result
