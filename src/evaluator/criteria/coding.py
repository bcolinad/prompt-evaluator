"""Coding task evaluation criteria."""

from __future__ import annotations

from src.evaluator.criteria.base import Criterion

CODING_TASK_CRITERIA = [
    Criterion(
        name="programming_language_specified",
        description="The prompt specifies which programming language, framework, or technology stack to use",
        detection_hint="Look for: 'in Python', 'using TypeScript', 'React component', 'Node.js', 'SQL query', 'Rust', 'Go', 'Java', 'C++', specific framework names, library references",
        weight=0.25,
    ),
    Criterion(
        name="requirements_clarity",
        description="The prompt clearly describes what the code should do — its functional requirements, inputs, outputs, and behavior",
        detection_hint="Look for: 'function that takes X and returns Y', 'endpoint that accepts', 'script that reads', 'class that manages', input/output specifications, expected behavior descriptions, user stories",
        weight=0.30,
    ),
    Criterion(
        name="architecture_guidance",
        description="The prompt provides guidance on code structure, design patterns, or architectural approach",
        detection_hint="Look for: 'use MVC pattern', 'implement as a class', 'create a REST API', 'use dependency injection', 'follow repository pattern', 'microservice', 'monolith', 'event-driven', module structure hints",
        weight=0.25,
    ),
    Criterion(
        name="code_quality_standards",
        description="The prompt specifies coding standards, style guidelines, or quality expectations",
        detection_hint="Look for: 'follow PEP 8', 'use type hints', 'add docstrings', 'write clean code', 'SOLID principles', 'DRY', 'include comments', 'production-ready', 'well-documented', 'idiomatic'",
        weight=0.20,
    ),
]

CODING_CONTEXT_CRITERIA = [
    Criterion(
        name="project_context_provided",
        description="The prompt describes the project or application the code will be part of",
        detection_hint="Look for: 'for a web app', 'part of a data pipeline', 'in our e-commerce platform', 'for a CLI tool', 'mobile app', project descriptions, application context",
        weight=0.25,
    ),
    Criterion(
        name="technical_constraints_specified",
        description="The prompt specifies technical constraints such as runtime environment, dependencies, or compatibility requirements",
        detection_hint="Look for: 'Python 3.11+', 'must run on AWS Lambda', 'compatible with PostgreSQL', 'no external dependencies', 'browser-compatible', version requirements, platform constraints",
        weight=0.25,
    ),
    Criterion(
        name="target_developer_audience",
        description="The prompt indicates the skill level or role of the developer who will use or maintain the code",
        detection_hint="Look for: 'for junior developers', 'senior-level code', 'beginner-friendly', 'for the team', 'maintainable by non-experts', 'production team', skill level references",
        weight=0.25,
    ),
    Criterion(
        name="existing_codebase_context",
        description="The prompt references existing code, APIs, or systems that the new code must integrate with",
        detection_hint="Look for: 'integrate with our existing', 'extend the current', 'compatible with the existing API', 'add to the module', code snippets, import references, existing function/class names",
        weight=0.25,
    ),
]

CODING_REFERENCES_CRITERIA = [
    Criterion(
        name="code_examples_provided",
        description="The prompt includes code examples, snippets, or pseudocode showing the expected approach or output format",
        detection_hint="Look for: code blocks, 'like this example', pseudocode, sample function signatures, expected output examples, 'similar to this code', interface definitions",
        weight=0.40,
    ),
    Criterion(
        name="api_documentation_referenced",
        description="The prompt references API documentation, library docs, or technical specifications",
        detection_hint="Look for: 'per the API docs', 'according to the specification', 'following the OpenAPI schema', 'as documented in', URL references to documentation, RFC references",
        weight=0.30,
    ),
    Criterion(
        name="test_expectations_defined",
        description="The prompt specifies test cases, expected outputs, or testing requirements",
        detection_hint="Look for: 'should pass these tests', 'expected output for input X is Y', 'include unit tests', 'test cases', 'edge cases to handle', 'given-when-then', assertion examples",
        weight=0.30,
    ),
]

CODING_CONSTRAINTS_CRITERIA = [
    Criterion(
        name="error_handling_requirements",
        description="The prompt specifies how errors, edge cases, and invalid inputs should be handled",
        detection_hint="Look for: 'handle errors gracefully', 'raise ValueError for', 'return None on failure', 'try/except', 'validate input', 'edge cases', 'graceful degradation', error response formats",
        weight=0.25,
    ),
    Criterion(
        name="security_considerations",
        description="The prompt addresses security concerns such as input validation, authentication, or data sanitization",
        detection_hint="Look for: 'sanitize input', 'prevent SQL injection', 'validate user input', 'authentication required', 'CORS policy', 'rate limiting', 'encrypt', 'secure', OWASP references",
        weight=0.25,
    ),
    Criterion(
        name="performance_requirements",
        description="The prompt specifies performance expectations such as time complexity, memory limits, or throughput targets",
        detection_hint="Look for: 'O(n) time complexity', 'handle 1M records', 'response under 200ms', 'memory efficient', 'optimize for speed', 'batch processing', 'async', 'concurrent', performance benchmarks",
        weight=0.25,
    ),
    Criterion(
        name="scope_exclusions",
        description="The prompt explicitly states what to exclude, avoid, or not implement",
        detection_hint="Look for: 'do not implement', 'exclude authentication', 'no database logic', 'avoid using', 'don't add logging', 'skip the UI', 'out of scope', 'leave out'",
        weight=0.25,
    ),
]

CODING_CRITERIA = {
    "task": CODING_TASK_CRITERIA,
    "context": CODING_CONTEXT_CRITERIA,
    "references": CODING_REFERENCES_CRITERIA,
    "constraints": CODING_CONSTRAINTS_CRITERIA,
}
