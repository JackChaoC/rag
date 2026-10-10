-- 逻辑枚举：
-- source_type = markdown | text | pdf | word | excel | powerpoint | html
-- status = pending | indexing | ready | failed | deleting | deleted

-- 变更批次：26-09-30_0
-- 变更来源：implement-regulations
-- 落地状态：已实现
CREATE TYPE "Team" AS ENUM ('wallet', 'member', 'devops', 'data', 'event');
CREATE TABLE files (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    size_bytes BIGINT NULL, -- Legacy sizes are unknown until the file is read.
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE documents (
    id UUID PRIMARY KEY,
    file_id UUID NOT NULL REFERENCES files(id),
    title TEXT NOT NULL CHECK (length(btrim(title)) > 0),
    team "Team" NULL,
    project TEXT NULL,
    description TEXT NULL,
    operator TEXT NULL,
    source_type TEXT NOT NULL CHECK (
        source_type IN ('markdown', 'text', 'pdf', 'word', 'excel', 'powerpoint', 'html')
    ),
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    current_version INTEGER NOT NULL DEFAULT 1 CHECK (current_version >= 1),
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'indexing', 'ready', 'failed', 'deleting', 'deleted')
    ),
    last_error TEXT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
