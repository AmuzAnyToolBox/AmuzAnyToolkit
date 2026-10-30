"""One origin for every tool, retaining the ASCII API and its lifespan."""
from pathlib import Path
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from tools.ascii.backend.main import app
from tools.downloader.api import router as downloader_router
from tools.upscaler.api import router as upscaler_router

ROOT = Path(__file__).resolve().parent
ASCII = ROOT / 'tools' / 'ascii'

app.title = 'AmuzAnyToolkit'
app.include_router(downloader_router)
app.include_router(upscaler_router)
app.mount('/ui-kit', StaticFiles(directory=ROOT / 'ui-kit', html=True), name='ui-kit')
dist = ASCII / 'frontend' / 'dist'
if dist.is_dir():
    app.mount('/ascii', StaticFiles(directory=dist, html=True), name='ascii')
else:
    @app.get('/ascii/', response_class=HTMLResponse)
    def missing_build():
        return HTMLResponse('<html lang="ru"><meta charset="utf-8"><title>Сборка ASCII</title>'
                            '<h1>Соберите AmuzASCII</h1><p>В корне репозитория выполните '
                            '<code>npm --prefix tools/ascii/frontend ci</code>, затем '
                            '<code>npm run build</code> и перезапустите сервер.</p>'
                            '<a href="/">Вернуться в хаб</a></html>', status_code=503)
app.mount('/', StaticFiles(directory=ROOT / 'frontend', html=True), name='hub')
