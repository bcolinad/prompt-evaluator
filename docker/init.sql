-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector extension for embedding similarity search
CREATE EXTENSION IF NOT EXISTS "vector";

-- ── Chainlit Data Layer Tables ──────────────────────────

CREATE TABLE IF NOT EXISTS "User" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identifier TEXT NOT NULL UNIQUE,
    metadata JSONB NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "Thread" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT,
    "userId" UUID REFERENCES "User"(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    tags TEXT[],
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "deletedAt" TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS "Step" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "threadId" UUID REFERENCES "Thread"(id) ON DELETE CASCADE,
    "parentId" UUID REFERENCES "Step"(id) ON DELETE SET NULL,
    input TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    name TEXT,
    output TEXT,
    type TEXT NOT NULL DEFAULT 'run',
    "startTime" TIMESTAMPTZ,
    "endTime" TIMESTAMPTZ,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "showInput" TEXT DEFAULT 'json',
    "isError" BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS "Element" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "threadId" UUID REFERENCES "Thread"(id) ON DELETE CASCADE,
    "stepId" UUID REFERENCES "Step"(id) ON DELETE CASCADE,
    metadata JSONB NOT NULL DEFAULT '{}',
    mime TEXT,
    name TEXT,
    "objectKey" TEXT,
    url TEXT,
    "chainlitKey" TEXT,
    display TEXT,
    size TEXT,
    language TEXT,
    page INTEGER,
    props JSONB NOT NULL DEFAULT '{}',
    "autoPlay" BOOLEAN,
    "playerConfig" JSONB
);

CREATE TABLE IF NOT EXISTS "Feedback" (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    "stepId" UUID REFERENCES "Step"(id) ON DELETE CASCADE,
    name TEXT,
    value DOUBLE PRECISION,
    comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_thread_user ON "Thread"("userId");
CREATE INDEX IF NOT EXISTS idx_thread_updated ON "Thread"("updatedAt" DESC);
CREATE INDEX IF NOT EXISTS idx_step_thread ON "Step"("threadId");
CREATE INDEX IF NOT EXISTS idx_step_parent ON "Step"("parentId");
CREATE INDEX IF NOT EXISTS idx_element_thread ON "Element"("threadId");
CREATE INDEX IF NOT EXISTS idx_element_step ON "Element"("stepId");
CREATE INDEX IF NOT EXISTS idx_feedback_step ON "Feedback"("stepId");

-- ── Application Tables ──────────────────────────────────

-- Evaluations history
CREATE TABLE IF NOT EXISTS evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255),
    mode VARCHAR(50) NOT NULL CHECK (mode IN ('prompt', 'system_prompt')),
    input_text TEXT NOT NULL,
    expected_outcome TEXT,
    overall_score INTEGER NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    grade VARCHAR(20) NOT NULL,
    task_score INTEGER CHECK (task_score BETWEEN 0 AND 100),
    context_score INTEGER CHECK (context_score BETWEEN 0 AND 100),
    references_score INTEGER CHECK (references_score BETWEEN 0 AND 100),
    constraints_score INTEGER CHECK (constraints_score BETWEEN 0 AND 100),
    analysis JSONB NOT NULL DEFAULT '{}',
    improvements JSONB NOT NULL DEFAULT '[]',
    rewritten_prompt TEXT,
    config_snapshot JSONB,
    eval_phase VARCHAR(20),
    llm_output TEXT,
    output_evaluation JSONB,
    langsmith_run_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Custom evaluation configs
CREATE TABLE IF NOT EXISTS eval_configs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    config JSONB NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_evaluations_session ON evaluations(session_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_thread ON evaluations(thread_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_created ON evaluations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_evaluations_grade ON evaluations(grade);
CREATE INDEX IF NOT EXISTS idx_eval_configs_default ON eval_configs(is_default) WHERE is_default = TRUE;

-- Conversation embeddings for self-learning similarity search
CREATE TABLE IF NOT EXISTS conversation_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    thread_id VARCHAR(255),
    evaluation_id VARCHAR(255),
    input_text TEXT NOT NULL,
    rewritten_prompt TEXT,
    overall_score INTEGER NOT NULL,
    grade VARCHAR(20) NOT NULL,
    output_score DOUBLE PRECISION,
    improvements_summary TEXT,
    embedding vector(768) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_embeddings_user ON conversation_embeddings(user_id);
CREATE INDEX IF NOT EXISTS idx_conv_embeddings_thread ON conversation_embeddings(thread_id);
CREATE INDEX IF NOT EXISTS idx_conv_embeddings_eval ON conversation_embeddings(evaluation_id);
CREATE INDEX IF NOT EXISTS idx_conv_embeddings_vector ON conversation_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Insert default evaluation config
INSERT INTO eval_configs (name, description, config, is_default) VALUES (
    'default',
    'Default T.C.R.E.I. evaluation configuration',
    '{
        "dimensions": {
            "task": {"weight": 0.30, "sub_criteria": ["clear_action_verb", "specific_deliverable", "persona_defined", "output_format_specified"]},
            "context": {"weight": 0.25, "sub_criteria": ["background_provided", "audience_defined", "goals_stated", "domain_specificity"]},
            "references": {"weight": 0.20, "sub_criteria": ["examples_included", "structured_references", "reference_labeling"]},
            "constraints": {"weight": 0.25, "sub_criteria": ["scope_boundaries", "format_constraints", "length_limits", "exclusions_defined"]}
        },
        "grading_scale": {"excellent": 85, "good": 65, "needs_work": 40, "weak": 0}
    }',
    TRUE
) ON CONFLICT (name) DO NOTHING;
