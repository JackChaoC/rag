from rag.services.documents.types.document import DocumentStatus, Team
from rag.services.documents.document_service import DocumentService


class ListDocumentsUseCase:
    def __init__(self, documentService: DocumentService) -> None:
        self.documentService = documentService

    async def execute(self, q=None, team=None, status=None, project=None, operator=None):
        filters = {}
        for name, value in (("q", q), ("project", project), ("operator", operator)):
            if value and value.strip():
                filters[name] = value.strip()
        if team is not None:
            filters["team"] = Team(team)
        if status is not None:
            filters["status"] = DocumentStatus(status)
        return [
            self.documentService.summarize(document)
            for document in await self.documentService.list(**filters)
        ]
