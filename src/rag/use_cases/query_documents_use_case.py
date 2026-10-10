from rag.services.documents.document_service import DocumentService
from rag.services.documents.types.document import DocumentStatus, Team
from rag.services.documents.types.document_page import DocumentPage


class QueryDocumentsUseCase:
    def __init__(self, documentService: DocumentService):
        self.documentService = documentService

    async def execute(self, page=1, title=None, document_id=None, team=None,
                      project=None, operator=None, status=None):
        if page < 1:
            raise ValueError("page must be at least 1")
        filters = {}
        for name, value in (("title", title), ("document_id", document_id),
                            ("project", project), ("operator", operator)):
            if value and value.strip():
                filters[name] = value.strip()
        if team is not None:
            filters["team"] = Team(team)
        if status is not None:
            filters["status"] = DocumentStatus(status)
        documents, total = await self.documentService.query(page=page, **filters)
        return DocumentPage(
            items=[self.documentService.summarize(d) for d in documents],
            total=total, page=page,
        )
