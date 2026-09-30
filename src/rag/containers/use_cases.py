from dependency_injector import containers, providers

from rag.use_cases.check_health_use_case import CheckHealthUseCase
from rag.use_cases.delete_document_index_use_case import DeleteDocumentIndexUseCase
from rag.use_cases.delete_document_use_case import DeleteDocumentUseCase
from rag.use_cases.finalize_index_failure_use_case import FinalizeIndexFailureUseCase
from rag.use_cases.get_chunk_detail_use_case import GetChunkDetailUseCase
from rag.use_cases.index_document_use_case import IndexDocumentUseCase
from rag.use_cases.list_document_chunks_use_case import ListDocumentChunksUseCase
from rag.use_cases.list_documents_use_case import ListDocumentsUseCase
from rag.use_cases.query_knowledge_use_case import QueryKnowledgeUseCase
from rag.use_cases.rebuild_index_use_case import RebuildIndexUseCase
from rag.use_cases.reindex_document_use_case import ReindexDocumentUseCase
from rag.use_cases.upload_file_use_case import UploadFileUseCase


class UseCases(containers.DeclarativeContainer):
    services = providers.DependenciesContainer()

    uploadFileUseCase = providers.Factory(
        UploadFileUseCase,
        fileService=services.fileService,
        documentService=services.documentService,
        indexTaskService=services.indexTaskService,
    )
    reindexDocumentUseCase = providers.Factory(
        ReindexDocumentUseCase,
        fileService=services.fileService,
        documentService=services.documentService,
        vectorService=services.vectorService,
        indexTaskService=services.indexTaskService,
    )
    deleteDocumentUseCase = providers.Factory(
        DeleteDocumentUseCase,
        documentService=services.documentService,
        indexTaskService=services.indexTaskService,
    )
    listDocumentsUseCase = providers.Factory(
        ListDocumentsUseCase,
        documentService=services.documentService,
    )
    listDocumentChunksUseCase = providers.Factory(
        ListDocumentChunksUseCase,
        chunkLookupService=services.chunkLookupService,
    )
    getChunkDetailUseCase = providers.Factory(
        GetChunkDetailUseCase,
        chunkLookupService=services.chunkLookupService,
    )
    queryKnowledgeUseCase = providers.Factory(
        QueryKnowledgeUseCase,
        vectorQueryService=services.vectorQueryService,
    )
    checkHealthUseCase = providers.Factory(
        CheckHealthUseCase,
        healthService=services.healthService,
    )
    indexDocumentUseCase = providers.Factory(
        IndexDocumentUseCase,
        documentService=services.documentService,
        fileService=services.fileService,
        readerService=services.readerService,
        splitterService=services.splitterService,
        embeddingService=services.embeddingService,
        vectorService=services.vectorService,
    )
    deleteDocumentIndexUseCase = providers.Factory(
        DeleteDocumentIndexUseCase,
        documentService=services.documentService,
        fileService=services.fileService,
        vectorService=services.vectorService,
    )
    finalizeIndexFailureUseCase = providers.Factory(
        FinalizeIndexFailureUseCase,
        documentService=services.documentService,
        vectorService=services.vectorService,
    )
    rebuildIndexUseCase = providers.Factory(
        RebuildIndexUseCase,
        documentService=services.documentService,
        indexTaskService=services.indexTaskService,
    )
