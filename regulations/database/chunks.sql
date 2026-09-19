-- 变更批次：26-09-19_0
-- 变更来源：improve-regulations
-- 落地状态：已实现
-- 实现优先级：P0
CREATE TABLE chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    version INTEGER NOT NULL CHECK (version >= 1),
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    start_line INTEGER NULL CHECK (start_line IS NULL OR start_line >= 1),
    end_line INTEGER NULL CHECK (end_line IS NULL OR end_line >= 1),
    token_count INTEGER NULL CHECK (token_count IS NULL OR token_count >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chunks_document_version_index_key
        UNIQUE (document_id, version, chunk_index),
    CONSTRAINT chunks_line_range_check
        CHECK (start_line IS NULL OR end_line IS NULL OR start_line <= end_line)
);

CREATE INDEX chunks_document_active_idx
    ON chunks (document_id, active);

CREATE INDEX chunks_document_version_idx
    ON chunks (document_id, version);
