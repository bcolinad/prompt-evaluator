"""Chat profile definitions and constants for the Chainlit UI."""

from __future__ import annotations

from src.evaluator import TaskType

_PROFILE_TO_TASK_TYPE = {
    "General Task Prompts": TaskType.GENERAL,
    "Email Creation Prompts": TaskType.EMAIL_WRITING,
    "Summarization Prompts": TaskType.SUMMARIZATION,
    "Coding Task Prompts": TaskType.CODING_TASK,
    "Exam Interview Agent Prompts": TaskType.EXAM_INTERVIEW,
    "LinkedIn Professional Post Prompts": TaskType.LINKEDIN_POST,
}

_CHAT_PROFILE_NAME = "Test your optimized prompts"

# Welcome messages keyed by TaskType — used by on_chat_start() to avoid elif chain
_WELCOME_MESSAGES: dict[TaskType, str] = {
    TaskType.EMAIL_WRITING: (
        "You are in **Email Creation Prompts** mode.\n\n"
        "Your prompt will be evaluated using email-specific criteria:\n"
        "- **Structure Analysis**: Tone/style, recipient clarity, email structure, purpose\n"
        "- **Output Quality**: Tone appropriateness, professional structure, audience fit, "
        "purpose achievement, conciseness"
    ),
    TaskType.SUMMARIZATION: (
        "You are in **Summarization Prompts** mode.\n\n"
        "Your prompt will be evaluated using summarization-specific criteria:\n"
        "- **Structure Analysis**: Summary type, source material, length constraints, audience\n"
        "- **Output Quality**: Information accuracy, logical structure, key information coverage, "
        "source fidelity, conciseness & precision"
    ),
    TaskType.CODING_TASK: (
        "You are in **Coding Task Prompts** mode.\n\n"
        "Your prompt will be evaluated using coding-specific criteria:\n"
        "- **Structure Analysis**: Language/stack, requirements clarity, architecture guidance, "
        "code quality standards\n"
        "- **Output Quality**: Code correctness, code quality, requirements coverage, "
        "error handling & security, maintainability"
    ),
    TaskType.EXAM_INTERVIEW: (
        "You are in **Exam Interview Agent Prompts** mode.\n\n"
        "Your prompt will be evaluated using assessment-specific criteria:\n"
        "- **Structure Analysis**: Assessment objective, question design, difficulty calibration, "
        "rubric/scoring\n"
        "- **Output Quality**: Question quality, assessment coverage, difficulty calibration, "
        "rubric completeness, fairness & objectivity"
    ),
    TaskType.LINKEDIN_POST: (
        "You are in **LinkedIn Professional Post Prompts** mode.\n\n"
        "Your prompt will be evaluated using LinkedIn-specific criteria:\n"
        "- **Structure Analysis**: Post objective, writing voice, audience targeting, "
        "platform awareness, hashtag strategy\n"
        "- **Output Quality**: Professional tone & authenticity, hook & scroll-stopping power, "
        "audience engagement, value delivery, LinkedIn optimization"
    ),
}

_DEFAULT_WELCOME = (
    "You are in **General Task Prompts** mode.\n\n"
    "Your prompt will be evaluated using the standard T.C.R.E.I. criteria "
    "(Task, Context, References, Constraints) and general output quality dimensions."
)

# File attachment support for chat mode
_TEXT_FILE_EXTENSIONS: frozenset[str] = frozenset({
    ".txt", ".py", ".md", ".json", ".csv", ".yaml", ".yml", ".html", ".xml",
    ".log", ".js", ".ts", ".css", ".sql", ".sh", ".toml", ".ini", ".java",
    ".c", ".cpp", ".h", ".rs", ".go", ".rb", ".swift", ".kt", ".r", ".tex",
    ".cfg", ".conf", ".env", ".gitignore", ".dockerfile", ".makefile",
})
_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp"})
_MAX_TEXT_FILE_SIZE: int = 100 * 1024  # 100 KB

# Document processing support (PDF, DOCX, XLSX, PPTX, CSV)
_DOCUMENT_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".docx", ".xlsx", ".pptx", ".csv"})
_MAX_DOCUMENT_SIZE: int = 100 * 1024 * 1024  # 100 MB
