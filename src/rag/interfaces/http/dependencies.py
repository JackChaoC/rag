from typing import Annotated

from dependency_injector.wiring import Provide
from fastapi import Depends

from rag.container import Container
from rag.use_cases.check_health import CheckHealth
from rag.use_cases.delete_document import DeleteDocument
from rag.use_cases.get_document_chunk import GetDocumentChunk
from rag.use_cases.ingest_document import IngestDocument
from rag.use_cases.list_documents import ListDocuments
from rag.use_cases.reindex_document import ReindexDocument
from rag.use_cases.search_knowledge import SearchKnowledge

IngestDocumentDep = Annotated[
    IngestDocument, Depends(Provide[Container.ingest_document])
]
ReindexDocumentDep = Annotated[
    ReindexDocument, Depends(Provide[Container.reindex_document])
]
DeleteDocumentDep = Annotated[
    DeleteDocument, Depends(Provide[Container.delete_document])
]
ListDocumentsDep = Annotated[ListDocuments, Depends(Provide[Container.list_documents])]
GetDocumentChunkDep = Annotated[
    GetDocumentChunk, Depends(Provide[Container.get_document_chunk])
]
SearchKnowledgeDep = Annotated[
    SearchKnowledge, Depends(Provide[Container.search_knowledge])
]
CheckHealthDep = Annotated[CheckHealth, Depends(Provide[Container.check_health])]
