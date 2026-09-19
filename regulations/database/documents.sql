-- 逻辑枚举：
-- source_type = markdown | text | pdf | word | excel | powerpoint | html
-- status = pending | indexing | ready | failed | deleting | deleted

-- 变更批次：26-09-19_0
-- 变更来源：improve-regulations
-- 落地状态：已实现
-- 实现优先级：P0
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    source_uri TEXT NOT NULL UNIQUE,
    title TEXT NULL,
    source_type TEXT NOT NULL CHECK (
        source_type IN ('markdown', 'text', 'pdf', 'word', 'excel', 'powerpoint', 'html')
    ),
    content TEXT NOT NULL,
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
