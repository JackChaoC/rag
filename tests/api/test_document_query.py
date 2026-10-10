import httpx
from mcp import Client

from rag.api.mcp.server import create_mcp_server

from rag.api.http.app import create_app


async def test_document_query_combines_filters_and_matches_information(appContainer):
    for title, team, project, operator, description in [
        ('Account guide', 'member', 'account', 'Jack', 'Login flow 100%_complete'),
        ('Wallet guide', 'wallet', 'wallet', 'Chiu', 'Payment flow'),
    ]:
        file = await appContainer.use_cases.uploadFileUseCase().execute(b'# Test', 'test.md')
        await appContainer.use_cases.ingestDocumentUseCase().execute(
            file.url, title, team=team, project=project, operator=operator, description=description)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app(appContainer)), base_url='http://test') as client:
        docs = (await client.get('/v1/documents')).json()
        assert len(docs) == 2
        for query in ['ACCOUNT', 'Login', 'Jack', 'member', '100%_', docs[0]['document_id'][:8]]:
            response = await client.get('/v1/documents', params={'q': query})
            assert response.status_code == 200
            assert [d['title'] for d in response.json()] == ['Account guide']
        params = {'q': ' guide ', 'team': 'member', 'status': 'pending', 'project': 'account', 'operator': 'Jack'}
        assert len((await client.get('/v1/documents', params=params)).json()) == 1
        for change in [{'status': 'ready'}, {'team': 'wallet'}, {'project': 'acc'}, {'operator': 'jack'}]:
            assert (await client.get('/v1/documents', params={**params, **change})).json() == []
        assert len((await client.get('/v1/documents', params={'q': '  ', 'project': '  '})).json()) == 2
        assert (await client.get('/v1/documents', params={'q': 'not found'})).json() == []
        for params in [{'team': 'unknown'}, {'status': 'unknown'}]:
            response = await client.get('/v1/documents', params=params)
            assert response.status_code == 422
            assert response.json()['code'] == 'invalid_input'

    server = create_mcp_server(
        search_knowledge_provider=appContainer.use_cases.queryKnowledgeUseCase,
        get_document_chunk_provider=appContainer.use_cases.getChunkDetailUseCase,
        list_documents_provider=appContainer.use_cases.listDocumentsUseCase,
    )
    async with Client(server) as client:
        response = await client.call_tool("list_documents", {"q": "Login", "team": "member"})
        assert not response.is_error
        assert "Account guide" in str(response.structured_content)
        assert "Wallet guide" not in str(response.structured_content)
