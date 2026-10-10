from typing import Annotated

from dependency_injector.wiring import Provide
from fastapi import Depends

from rag.containers import ApplicationContainer
from rag.use_cases.check_health_use_case import CheckHealthUseCase
from rag.use_cases.delete_document_use_case import DeleteDocumentUseCase
from rag.use_cases.get_chunk_detail_use_case import GetChunkDetailUseCase
from rag.use_cases.list_document_chunks_use_case import ListDocumentChunksUseCase
from rag.use_cases.list_documents_use_case import ListDocumentsUseCase
from rag.use_cases.query_knowledge_use_case import QueryKnowledgeUseCase
from rag.use_cases.reindex_document_use_case import ReindexDocumentUseCase
from rag.use_cases.upload_file_use_case import UploadFileUseCase
from rag.use_cases.ingest_document_use_case import IngestDocumentUseCase
from rag.use_cases.get_file_use_case import GetFileUseCase
from rag.use_cases.query_documents_use_case import QueryDocumentsUseCase

ListDocumentChunksDep = Annotated[
    ListDocumentChunksUseCase,
    Depends(Provide[ApplicationContainer.use_cases.listDocumentChunksUseCase]),
]

UploadFileDep = Annotated[
    UploadFileUseCase,
    Depends(Provide[ApplicationContainer.use_cases.uploadFileUseCase]),
]
ReindexDocumentDep = Annotated[
    ReindexDocumentUseCase,
    Depends(Provide[ApplicationContainer.use_cases.reindexDocumentUseCase]),
]
DeleteDocumentDep = Annotated[
    DeleteDocumentUseCase,
    Depends(Provide[ApplicationContainer.use_cases.deleteDocumentUseCase]),
]
ListDocumentsDep = Annotated[
    ListDocumentsUseCase,
    Depends(Provide[ApplicationContainer.use_cases.listDocumentsUseCase]),
]
GetDocumentChunkDep = Annotated[
    GetChunkDetailUseCase,
    Depends(Provide[ApplicationContainer.use_cases.getChunkDetailUseCase]),
]
SearchKnowledgeDep = Annotated[
    QueryKnowledgeUseCase,
    Depends(Provide[ApplicationContainer.use_cases.queryKnowledgeUseCase]),
]
CheckHealthDep = Annotated[
    CheckHealthUseCase,
    Depends(Provide[ApplicationContainer.use_cases.checkHealthUseCase]),
]

IngestDocumentDep = Annotated[
    IngestDocumentUseCase, Depends(Provide[ApplicationContainer.use_cases.ingestDocumentUseCase]),
]
GetFileDep = Annotated[
    GetFileUseCase, Depends(Provide[ApplicationContainer.use_cases.getFileUseCase]),
]


QueryDocumentsDep = Annotated[
    QueryDocumentsUseCase, Depends(Provide[ApplicationContainer.use_cases.queryDocumentsUseCase]),
]
