"""Integration checks for the monorepo's shared origin and built ASCII assets."""
import re
from fastapi.testclient import TestClient
from server import app, dist

def test_hub_and_ui_kit():
    with TestClient(app) as client:
        assert 'AmuzAnyToolkit' in client.get('/').text
        assert 'AmuzMorse' in client.get('/tools.js').text
        assert 'AmuzFetch' in client.get('/tools.js').text
        assert 'AmuzUpscale' in client.get('/tools.js').text
        assert "url:'/ascii/'" in client.get('/tools.js').text
        for path in ['/upscaler.js', '/upscaler.css', '/downloader.js', '/downloader.css', '/morse-layout.css', '/ui-kit/', '/ui-kit/tokens.css', '/ui-kit/components.css', '/ui-kit/scrollbars.css', '/ui-kit/themes.js', '/ui-kit/appearance.js', '/ui-kit/appearance.css', '/ui-kit/appearance-state.js']:
            assert client.get(path).status_code == 200, path

def test_ascii_api_and_built_assets_share_the_same_server():
    assert dist.is_dir(), 'Run npm run build before integration tests'
    with TestClient(app) as client:
        assert client.get('/api/health').status_code == 200
        assert client.get('/api/demo').headers['content-type'].startswith('image/')
        response = client.get('/ascii/')
        assert response.status_code == 200
        assert 'AmuzASCII' in response.text
        paths = re.findall(r'(?:src|href)="(/ascii/[^\"]+)"', response.text)
        assert paths
        for path in paths:
            assert client.get(path).status_code == 200, path
        assert client.get('/ascii/assets/favicon.svg').status_code == 200
