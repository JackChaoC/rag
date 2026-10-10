from uuid import uuid4

import httpx
import pytest

from rag.api.http.app import create_app


async def test_upload_preview_download_and_ingest_are_separate(appContainer):
    app = create_app(appContainer)
    content = b'# Original\n<script>alert(1)</script>\n'
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        upload = await client.post('/v1/files', files={'file': ('guide.md', content, 'text/markdown')})
        assert upload.status_code == 201
        file = upload.json()
        assert file['size_bytes'] == len(content)
        assert await appContainer.services.documentService().list() == []
        appContainer.resources.rabbitmqResource().publish.assert_not_awaited()
        preview = await client.get(file['url'])
        download = await client.get(file['url'] + '?download=true')
        assert preview.content == download.content == content
        assert preview.headers['content-type'].startswith('text/plain')
        assert preview.headers['content-disposition'].startswith('inline;')
        assert download.headers['content-disposition'].startswith('attachment;')
        assert 'guide.md' in download.headers['content-disposition']
        assert preview.headers['x-content-type-options'] == 'nosniff'
        response = await client.post('/v1/documents', json={'file_url': file['url'], 'title': ' Guide ', 'team': 'member', 'project': 'account', 'description': 'A guide', 'operator': 'Jack'})
        assert response.status_code == 202
        document = response.json()
        assert document['title'] == 'Guide'
        assert document['file_url'] == file['url']
        assert document['team'] == 'member'
        assert document['operator'] == 'Jack'
        assert 'source_uri' not in document
        appContainer.resources.rabbitmqResource().publish.assert_awaited_once()
        assert (await client.get('/v1/documents')).json() == [document]
        missing = await client.get(f'/v1/files/{uuid4()}')
        assert missing.status_code == 404


@pytest.mark.parametrize('patch', [{'title': ''}, {'title': '  '}, {'team': 'other'}, {'source_uri': 'old'}, {'file_url': 'http://127.0.0.1/private'}, {'file_url': '/v1/files/../../secret'}, {'file_url': f'/v1/files/{uuid4()}'}])
async def test_ingest_rejects_invalid_input(appContainer, patch):
    file = await appContainer.use_cases.uploadFileUseCase().execute(b'# Doc', 'doc.md')
    app = create_app(appContainer)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        result = await client.post('/v1/documents', json={'title': 'Doc', 'file_url': file.url, **patch})
    assert result.status_code in {404, 422}
    appContainer.resources.rabbitmqResource().publish.assert_not_awaited()


async def test_file_validation_and_pdf_preview(appContainer):
    app = create_app(appContainer)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
        for filename, content in [('bad.html', b'<html>'), ('empty.md', b'')]:
            response = await client.post('/v1/files', files={'file': (filename, content)})
            assert response.status_code == 422
        response = await client.post('/v1/files', files={'file': ('sample.pdf', b'%PDF-1.4')})
        pdf = await client.get(response.json()['url'])
        assert pdf.headers['content-type'] == 'application/pdf'
        assert pdf.content == b'%PDF-1.4'
