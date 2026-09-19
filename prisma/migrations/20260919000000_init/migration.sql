CREATE TYPE "SourceType" AS ENUM ('markdown', 'text', 'pdf', 'word', 'excel', 'powerpoint', 'html');
CREATE TYPE "DocumentStatus" AS ENUM ('pending', 'indexing', 'ready', 'failed', 'deleting', 'deleted');

CREATE TABLE "documents" (
    "id" UUID NOT NULL,
    "source_uri" TEXT NOT NULL,
    "title" TEXT,
    "source_type" "SourceType" NOT NULL,
    "content" TEXT NOT NULL,
    "content_hash" TEXT NOT NULL,
    "current_version" INTEGER NOT NULL DEFAULT 1 CHECK ("current_version" >= 1),
    "status" "DocumentStatus" NOT NULL,
    "last_error" TEXT,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "documents_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "documents_metadata_object" CHECK (jsonb_typeof("metadata") = 'object')
);

CREATE TABLE "chunks" (
    "id" UUID NOT NULL,
    "document_id" UUID NOT NULL,
    "version" INTEGER NOT NULL CHECK ("version" >= 1),
    "chunk_index" INTEGER NOT NULL CHECK ("chunk_index" >= 0),
    "content" TEXT NOT NULL,
    "start_line" INTEGER CHECK ("start_line" IS NULL OR "start_line" >= 1),
    "end_line" INTEGER CHECK ("end_line" IS NULL OR "end_line" >= 1),
    "token_count" INTEGER CHECK ("token_count" IS NULL OR "token_count" >= 0),
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "active" BOOLEAN NOT NULL DEFAULT FALSE,
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "chunks_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "chunks_document_id_fkey" FOREIGN KEY ("document_id") REFERENCES "documents"("id") ON DELETE RESTRICT,
    CONSTRAINT "chunks_line_range" CHECK ("start_line" IS NULL OR "end_line" IS NULL OR "start_line" <= "end_line"),
    CONSTRAINT "chunks_metadata_object" CHECK (jsonb_typeof("metadata") = 'object')
);

CREATE UNIQUE INDEX "documents_source_uri_key" ON "documents"("source_uri");
CREATE UNIQUE INDEX "chunks_document_id_version_chunk_index_key" ON "chunks"("document_id", "version", "chunk_index");
CREATE INDEX "chunks_document_id_active_idx" ON "chunks"("document_id", "active");
CREATE INDEX "chunks_document_id_version_idx" ON "chunks"("document_id", "version");
