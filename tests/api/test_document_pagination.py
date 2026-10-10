from uuid import uuid4

import httpx

from rag.api.http.app import create_app
from rag.services.documents.types.document import Document, DocumentStatus, SourceType, Team


async def test_document_pages_filters_and_validation(appContainer):
    repository = appContainer.repositories.documentRepository()
    for index in range(47):
        await repository.create(Document(
            id=uuid4(), file_id=uuid4(), title=f"Guide {index:02}",
            file_path="test.md", source_type=SourceType.MARKDOWN, content_hash="hash",
            team=Team.MEMBER if index % 2 == 0 else Team.WALLET,
            project="Account 100%_complete", operator="Jack", description="Secret description",
            status=DocumentStatus.READY,
        ))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(appContainer)), base_url="http://test") as client:
        pages = [(await client.get('/v1/documents/query', params={'page': n})).json() for n in [1, 2, 3, 4]]
        assert [len(p['items']) for p in pages] == [20, 20, 7, 0]
        assert all(p['total'] == 47 and p['page_size'] == 20 for p in pages)
        ids = [d['document_id'] for p in pages for d in p['items']]
        assert len(set(ids)) == 47
        assert pages[1]['items'][0]['title'] == 'Guide 20'
        assert pages[2]['items'][0]['title'] == 'Guide 40'
        filtered = (await client.get('/v1/documents/query', params={
            'title': ' GUIDE ', 'team': 'member', 'project': '100%_',
            'operator': 'ja', 'status': 'ready', 'page': 2,
        })).json()
        assert filtered['total'] == 24 and len(filtered['items']) == 4
        exact = (await client.get('/v1/documents/query', params={'document_id': ids[0][:8]})).json()
        assert exact['total'] == 1 and exact['items'][0]['document_id'] == ids[0]
        for value in ['Secret', 'Account', 'missing']:
            result = (await client.get('/v1/documents/query', params={'title': value})).json()
            assert result['items'] == [] and result['total'] == 0
        for params in [{'page': 0}, {'page': -1}, {'page': 'bad'}, {'team': 'other'}, {'status': 'other'}]:
            assert (await client.get('/v1/documents/query', params=params)).status_code == 422
        assert len((await client.get('/v1/documents')).json()) == 47
