"""Exam/interview assessment evaluation criteria."""

from __future__ import annotations

from src.evaluator.criteria.base import Criterion

EXAM_TASK_CRITERIA = [
    Criterion(
        name="assessment_objective_defined",
        description="The prompt clearly defines what the exam or interview should assess — knowledge, skills, competencies, or aptitude",
        detection_hint="Look for: 'assess knowledge of', 'test understanding of', 'evaluate ability to', 'measure competency in', 'gauge proficiency', learning objectives, assessment goals",
        weight=0.25,
    ),
    Criterion(
        name="question_design_specified",
        description="The prompt specifies the type and format of questions to generate — multiple choice, open-ended, scenario-based, coding challenges, behavioral",
        detection_hint="Look for: 'multiple choice questions', 'open-ended', 'scenario-based', 'behavioral questions', 'STAR format', 'coding challenge', 'case study', 'true/false', 'fill in the blank', question type specifications",
        weight=0.30,
    ),
    Criterion(
        name="difficulty_calibration",
        description="The prompt specifies the difficulty level or distribution of questions (beginner, intermediate, advanced, or a mix)",
        detection_hint="Look for: 'beginner level', 'advanced difficulty', 'mix of easy and hard', 'senior-level', 'entry-level', 'progressive difficulty', 'Bloom's taxonomy', difficulty percentages or distributions",
        weight=0.25,
    ),
    Criterion(
        name="rubric_or_scoring_defined",
        description="The prompt requests a scoring rubric, answer key, or evaluation criteria for the generated questions",
        detection_hint="Look for: 'include an answer key', 'scoring rubric', 'point values', 'grading criteria', 'model answers', 'expected responses', 'evaluation criteria', 'pass/fail threshold'",
        weight=0.20,
    ),
]

EXAM_CONTEXT_CRITERIA = [
    Criterion(
        name="candidate_profile_defined",
        description="The prompt describes the target candidate — their experience level, background, role being assessed, or expected knowledge base",
        detection_hint="Look for: 'for junior developers', 'senior marketing candidates', 'medical students', 'new graduates', 'experienced professionals', candidate descriptions, role specifications, experience level",
        weight=0.30,
    ),
    Criterion(
        name="assessment_context_provided",
        description="The prompt provides context about the assessment setting — hiring, certification, classroom, training, or performance review",
        detection_hint="Look for: 'for a job interview', 'certification exam', 'classroom quiz', 'annual review', 'training assessment', 'screening test', 'final exam', assessment purpose and setting",
        weight=0.25,
    ),
    Criterion(
        name="subject_domain_specified",
        description="The prompt specifies the subject area, topic, or domain the assessment should cover",
        detection_hint="Look for: subject names, 'covering data structures', 'about machine learning', 'on project management', 'regarding compliance', topic lists, curriculum references, specific technical domains",
        weight=0.25,
    ),
    Criterion(
        name="time_constraints_defined",
        description="The prompt specifies time limits for the assessment or individual questions",
        detection_hint="Look for: '60-minute exam', '5 minutes per question', 'time-boxed', 'timed assessment', 'allotted time', duration specifications, pacing guidance",
        weight=0.20,
    ),
]

EXAM_REFERENCES_CRITERIA = [
    Criterion(
        name="sample_questions_provided",
        description="The prompt includes sample questions, past exam examples, or question templates to follow",
        detection_hint="Look for: 'like this example question', 'similar to', sample Q&A pairs, question templates, 'in the style of', past exam references, example format demonstrations",
        weight=0.40,
    ),
    Criterion(
        name="source_material_referenced",
        description="The prompt references textbooks, courses, documentation, or knowledge bases the questions should draw from",
        detection_hint="Look for: 'based on chapter 5', 'from the AWS Solutions Architect guide', 'per the curriculum', 'reference material', textbook names, course syllabi, official documentation",
        weight=0.30,
    ),
    Criterion(
        name="assessment_standards_referenced",
        description="The prompt references established assessment standards, frameworks, or methodologies",
        detection_hint="Look for: 'Bloom's taxonomy', 'competency-based', 'ABET standards', 'Common Core aligned', 'ISO certification requirements', assessment frameworks, educational standards",
        weight=0.30,
    ),
]

EXAM_CONSTRAINTS_CRITERIA = [
    Criterion(
        name="fairness_and_bias_safeguards",
        description="The prompt includes instructions to ensure questions are fair, unbiased, and accessible",
        detection_hint="Look for: 'avoid cultural bias', 'gender-neutral', 'accessible language', 'no trick questions', 'fair assessment', 'inclusive', 'avoid stereotypes', 'equitable', ADA compliance references",
        weight=0.25,
    ),
    Criterion(
        name="anti_cheating_measures",
        description="The prompt addresses question uniqueness, randomization, or measures to prevent cheating",
        detection_hint="Look for: 'unique questions', 'randomize order', 'question pool', 'not easily searchable', 'original questions', 'proctoring considerations', 'plagiarism-resistant', 'varied versions'",
        weight=0.25,
    ),
    Criterion(
        name="format_and_structure_constraints",
        description="The prompt specifies structural requirements — number of questions, sections, point distribution, or time allocation",
        detection_hint="Look for: '20 questions', 'divided into 3 sections', '10 points each', 'total of 100 points', 'Section A: multiple choice', structural layout, question count, point values",
        weight=0.25,
    ),
    Criterion(
        name="content_exclusions",
        description="The prompt explicitly states topics, question types, or approaches to exclude",
        detection_hint="Look for: 'do not include', 'avoid questions about', 'exclude memorization-only', 'no gotcha questions', 'skip advanced topics', 'don't test on', content boundaries",
        weight=0.25,
    ),
]

EXAM_CRITERIA = {
    "task": EXAM_TASK_CRITERIA,
    "context": EXAM_CONTEXT_CRITERIA,
    "references": EXAM_REFERENCES_CRITERIA,
    "constraints": EXAM_CONSTRAINTS_CRITERIA,
}
