from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import String, cast, or_, select, text, update

from rag.resources.postgresql.models import DocumentRecord
from rag.services.documents.types.document import Document


class DocumentRepository:
    def __init__(self, sessions, lockEngine):
        self.sessions = sessions
        self.lockEngine = lockEngine

    async def healthcheck(self) -> bool:
        async with self.sessions() as session:
            return bool(await session.scalar(text("SELECT TRUE")))

    @asynccontextmanager
    async def lock(self, documentId: UUID):
        # Transaction-scoped advisory lock also coordinates API and worker processes.
        key = int.from_bytes(documentId.bytes[:8], "big", signed=True)
        async with self.lockEngine.begin() as connection:
            await connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": key}
            )
            yield

    async def get(self, documentId):
        async with self.sessions() as session:
            record = await session.get(DocumentRecord, documentId)
            return _document(record) if record else None

    async def get_by_file_id(self, file_id):
        async with self.sessions() as session:
            record = await session.scalar(
                select(DocumentRecord).where(DocumentRecord.file_id == file_id)
            )
            return _document(record) if record else None

    async def list(self, q=None, team=None, status=None, project=None, operator=None):
        statement = select(DocumentRecord)
        if q:
            columns = [DocumentRecord.title, DocumentRecord.description,
                       DocumentRecord.project, DocumentRecord.operator,
                       cast(DocumentRecord.team, String), cast(DocumentRecord.id, String)]
            statement = statement.where(or_(
                *(column.icontains(q, autoescape=True) for column in columns)
            ))
        for name, value in (("team", team), ("status", status),
                            ("project", project), ("operator", operator)):
            if value is not None:
                statement = statement.where(getattr(DocumentRecord, name) == value)
        statement = statement.order_by(DocumentRecord.created_at, DocumentRecord.id)
        async with self.sessions() as session:
            records = await session.scalars(statement)
            return [_document(record) for record in records]

    async def create(self, document):
        async with self.sessions.begin() as session:
            session.add(DocumentRecord(id=document.id, **_values(document)))

    async def save(self, document):
        async with self.sessions.begin() as session:
            await session.execute(
                update(DocumentRecord)
                .where(DocumentRecord.id == document.id)
                .values(**_values(document))
            )

    async def set_status(self, documentId, status, *, error=None, expected=None):
        conditions = [DocumentRecord.id == documentId]
        if expected:
            conditions.append(DocumentRecord.status.in_(expected))
        async with self.sessions.begin() as session:
            result = await session.execute(
                update(DocumentRecord)
                .where(*conditions)
                .values(status=status, last_error=error)
            )
            return result.rowcount == 1


def _values(document):
    return dict(
        file_id=document.file_id,
        team=document.team, project=document.project,
        description=document.description, operator=document.operator,
        title=document.title,
        source_type=document.source_type,
        file_path=document.file_path,
        content_hash=document.content_hash,
        current_version=document.current_version,
        status=document.status,
        last_error=document.last_error,
        metadata_json=document.metadata,
    )


def _document(record):
    return Document(
        id=record.id,
        file_id=record.file_id,
        team=record.team, project=record.project,
        description=record.description, operator=record.operator,
        source_type=record.source_type,
        file_path=record.file_path,
        content_hash=record.content_hash,
        title=record.title,
        current_version=record.current_version,
        status=record.status,
        last_error=record.last_error,
        metadata=dict(record.metadata_json),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
