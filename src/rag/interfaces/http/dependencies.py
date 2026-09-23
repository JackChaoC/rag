from typing import Annotated, cast

from fastapi import Depends, Request

from rag.container import Container
from rag.use_cases.check_health import CheckHealth
from rag.use_cases.delete_document import DeleteDocument
from rag.use_cases.get_document_chunk import GetDocumentChunk
from rag.use_cases.ingest_document import IngestDocument
from rag.use_cases.list_documents import ListDocuments
from rag.use_cases.reindex_document import ReindexDocument
from rag.use_cases.search_knowledge import SearchKnowledge


def get_container(request: Request) -> Container:
    return cast(Container, request.app.state.container)


ContainerDep = Annotated[Container, Depends(get_container)]


def get_ingest_document(container: ContainerDep) -> IngestDocument:
    return container.ingest


def get_reindex_document(container: ContainerDep) -> ReindexDocument:
    return container.reindex


def get_delete_document(container: ContainerDep) -> DeleteDocument:
    return container.delete


def get_list_documents(container: ContainerDep) -> ListDocuments:
    return container.list_documents


def get_document_chunk(container: ContainerDep) -> GetDocumentChunk:
    return container.get_chunk


def get_search_knowledge(container: ContainerDep) -> SearchKnowledge:
    return container.search


def get_check_health(container: ContainerDep) -> CheckHealth:
    return container.health


IngestDocumentDep = Annotated[IngestDocument, Depends(get_ingest_document)]
ReindexDocumentDep = Annotated[ReindexDocument, Depends(get_reindex_document)]
DeleteDocumentDep = Annotated[DeleteDocument, Depends(get_delete_document)]
ListDocumentsDep = Annotated[ListDocuments, Depends(get_list_documents)]
GetDocumentChunkDep = Annotated[GetDocumentChunk, Depends(get_document_chunk)]
SearchKnowledgeDep = Annotated[SearchKnowledge, Depends(get_search_knowledge)]
CheckHealthDep = Annotated[CheckHealth, Depends(get_check_health)]
