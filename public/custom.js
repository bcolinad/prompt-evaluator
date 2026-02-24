// Professional Prompt Shaper — Custom UI
// Handles: favicon injection, page title, login page introduction panel.
(function () {
  "use strict";

  // ── Favicon ────────────────────────────────────────────────────────────
  var link = document.querySelector("link[rel~='icon']");
  if (!link) {
    link = document.createElement("link");
    link.rel = "icon";
    document.head.appendChild(link);
  }
  link.type = "image/svg+xml";
  link.href = "/public/favicon.svg";

  // ── Page title ─────────────────────────────────────────────────────────
  document.title = "Professional Prompt Shaper";

  // ── Login page introduction panel ──────────────────────────────────────

  // White version of the diamond+cursor icon (inline SVG for the login panel)
  var ICON_SVG =
    '<svg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 32 32" fill="none" class="login-intro-icon">' +
    '<path d="M16 2 L28 12 L16 30 L4 12 Z" fill="rgba(255,255,255,0.15)" stroke="rgba(255,255,255,0.8)" stroke-width="1.5" stroke-linejoin="round"/>' +
    '<path d="M4 12 L16 16 L28 12" stroke="rgba(255,255,255,0.4)" stroke-width="1" />' +
    '<path d="M16 2 L16 16" stroke="rgba(255,255,255,0.4)" stroke-width="1" />' +
    '<path d="M12 7 L18 10 L12 13" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>' +
    '<circle cx="25" cy="5" r="1.5" fill="rgba(255,255,255,0.6)"/>' +
    '<line x1="25" y1="2" x2="25" y2="8" stroke="rgba(255,255,255,0.6)" stroke-width="0.8" stroke-linecap="round"/>' +
    '<line x1="22" y1="5" x2="28" y2="5" stroke="rgba(255,255,255,0.6)" stroke-width="0.8" stroke-linecap="round"/>' +
    "</svg>";

  var INTRO_HTML =
    '<div class="login-intro">' +
    ICON_SVG +
    "<h2>Professional Prompt Shaper</h2>" +
    '<p class="login-intro-tagline">' +
    "Evaluate, improve, and rewrite your prompts using Google's T.C.R.E.I. framework — " +
    "or chat directly with leading LLMs." +
    "</p>" +
    '<div class="login-intro-features">' +
    '<div class="feature-category">Prompt Evaluation</div>' +
    "<div>T.C.R.E.I. Structural Analysis &amp; LLM-as-Judge Scoring</div>" +
    "<div>Prioritized Improvements &amp; AI Prompt Rewriting</div>" +
    "<div>Interactive Audit Reports with Word-Level Diff</div>" +
    "<div>Auto-Detection of prompt types, system prompts &amp; follow-ups</div>" +
    '<div class="feature-category">Smart Profiles &amp; Chat</div>' +
    "<div>6 Evaluator Profiles: General, Email, Summarization, Coding, Exam &amp; LinkedIn</div>" +
    "<div>Direct Chat — test optimized prompts, attach files &amp; images</div>" +
    "<div>Annotated T.C.R.E.I. example prompts per profile</div>" +
    '<div class="feature-category">Intelligence &amp; Flexibility</div>' +
    "<div>RAG-Grounded analysis with T.C.R.E.I. knowledge base</div>" +
    "<div>Self-Learning from past evaluations via vector similarity</div>" +
    "<div>Dual Providers: Google Gemini &amp; Anthropic Claude</div>" +
    "<div>Full LangSmith tracing &amp; observability</div>" +
    "</div>" +
    '<div class="login-intro-divider"></div>' +
    '<div class="login-intro-author">Built by <a href="https://www.linkedin.com/in/bcolinad/">Brandon</a><a href="https://www.innovacores.com/">   @Innovacores</a></div>' +
    '<div class="login-intro-framework">Grounded in Google Prompting Essentials</div>' +
    "</div>";

  function customizeLoginPage() {
    // The login page uses a 2-column grid. The right panel has class "bg-muted".
    var rightPanel = document.querySelector(
      ".grid.min-h-svh .bg-muted.lg\\:block"
    );
    if (!rightPanel) {
      // Fallback: look for any bg-muted inside a 2-column grid
      rightPanel = document.querySelector(".grid.min-h-svh .bg-muted");
    }
    if (!rightPanel || rightPanel.dataset.customized) return false;

    rightPanel.dataset.customized = "true";
    rightPanel.innerHTML = INTRO_HTML;
    return true;
  }

  // Poll for the login page (SPA renders asynchronously)
  var attempts = 0;
  var interval = setInterval(function () {
    if (customizeLoginPage() || attempts > 100) {
      clearInterval(interval);
    }
    attempts++;
  }, 100);

  // Also observe DOM changes in case the login page appears later (e.g., session expiry)
  var observer = new MutationObserver(function () {
    customizeLoginPage();
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // Stop the observer after 30 seconds to avoid unnecessary overhead
  setTimeout(function () {
    observer.disconnect();
  }, 30000);
})();
