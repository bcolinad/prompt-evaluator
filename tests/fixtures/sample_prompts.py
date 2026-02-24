"""Sample prompts with expected evaluation ranges for testing."""

WEAK_PROMPT = "Write me something about dogs"

MEDIUM_PROMPT = (
    "Create a bulleted list including the latest developments in the "
    "restaurant industry specific to urban areas that could impact the "
    "public reception of a dining experience using only ingredients native to the region."
)

STRONG_PROMPT = (
    "You're a veterinarian writing for a pet owner blog aimed at first-time dog owners. "
    "Write a 500-word article about the top 5 health concerns for senior dogs (ages 8+), "
    "including early symptoms to watch for and when to visit the vet.\n\n"
    "Use a friendly, accessible tone — avoid medical jargon. Format as numbered sections "
    "with a brief intro paragraph. Reference the AVMA guidelines on senior pet care.\n\n"
    "Constraints: Focus only on large breed dogs (50+ lbs). Do not include dietary "
    "supplement recommendations."
)

SYSTEM_PROMPT_EXAMPLE = (
    "You are a medical transcription assistant specializing in converting "
    "audio recordings of doctor-patient consultations into structured SOAP notes. "
    "Always output in the format: Subjective, Objective, Assessment, Plan. "
    "Use standard medical abbreviations. Flag any mentions of medication allergies "
    "with [ALLERGY ALERT]. If the audio is unclear, mark sections with [INAUDIBLE]."
)

SYSTEM_PROMPT_EXPECTED_OUTCOME = (
    "Structured SOAP notes from audio transcripts with allergy alerts and "
    "inaudible markers, using standard medical abbreviations."
)

# Expected score ranges (min, max) for validation
EXPECTED_RANGES = {
    "weak": {
        "overall": (0, 25),
        "task": (5, 30),
        "context": (0, 15),
        "references": (0, 5),
        "constraints": (0, 15),
    },
    "medium": {
        "overall": (35, 65),
        "task": (55, 85),
        "context": (40, 70),
        "references": (0, 10),
        "constraints": (20, 50),
    },
    "strong": {
        "overall": (75, 100),
        "task": (80, 100),
        "context": (75, 100),
        "references": (45, 80),
        "constraints": (75, 100),
    },
}
