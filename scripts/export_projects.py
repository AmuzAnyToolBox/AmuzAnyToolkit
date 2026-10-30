"""Export standalone tools from the monorepo; never copy environments or Git state."""
import argparse
import ast
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = {'AmuzASCII': 'ascii', 'AmuzMorse': 'morse', 'AmuzFetch': 'downloader', 'AmuzUpscale': 'upscaler'}


def export(destination):
    source_files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    source_files = sorted(set(p for p in source_files if p))
    for name, tool in PROJECTS.items():
        target = destination / name
        if target.exists():
            raise SystemExit(f'Refusing to overwrite {target}')
        target.mkdir(parents=True)
        for relative in source_files:
            common = relative.startswith('ui-kit/') or relative in {'.gitignore', 'run.py'}
            selected = relative.startswith(f'tools/{tool}/')
            # Fetch shares ASCII's checked networking, video validation and encoding code.
            dependency = tool == 'downloader' and relative.startswith('tools/ascii/backend/')
            frontend = tool != 'ascii' and relative.startswith('frontend/') and Path(relative).name in {
                'index.html', 'style.css', 'morse-layout.css', 'downloader.css', 'upscaler.css',
                'app.js' if tool == 'morse' else '', 'morse.js' if tool == 'morse' else '',
                'tools.js' if tool == 'morse' else '', 'upscale-view.js' if tool == 'upscaler' else '',
                'upscaler.js' if tool == 'upscaler' else 'downloader.js' if tool == 'downloader' else '',
            }
            if not (common or selected or dependency or frontend):
                continue
            if Path(relative).name == 'AGENTS.md' or relative.endswith(('.env', '.log')):
                continue
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, output)

        server = "from pathlib import Path\nfrom fastapi import FastAPI\nfrom fastapi.staticfiles import StaticFiles\nROOT=Path(__file__).resolve().parent\n"
        if tool == 'ascii':
            server += "from tools.ascii.backend.main import app\nfrom fastapi.responses import RedirectResponse\n@app.get('/')\ndef home(): return RedirectResponse('/ascii/')\napp.mount('/ascii',StaticFiles(directory=ROOT/'tools/ascii/frontend/dist',html=True))\n"
        else:
            server += f"app=FastAPI(title='{name}')\n"
            if tool in {'upscaler', 'downloader'}:
                server += f"from tools.{tool}.api import router\napp.include_router(router)\n"
            if tool == 'upscaler':
                original = (ROOT / 'tools/ascii/backend/main.py').read_text(encoding='utf-8')
                demo = next(n for n in ast.parse(original).body if isinstance(n, ast.FunctionDef) and n.name == 'demo_image')
                server += 'import io, math\nfrom PIL import Image,ImageDraw\nfrom fastapi.responses import Response\n'
                server += ast.get_source_segment(original, demo) + '\n'
                server += "@app.get('/api/demo')\ndef demo():\n    data=io.BytesIO()\n    demo_image().save(data,format='PNG')\n    return Response(data.getvalue(),media_type='image/png')\n"
        server += "app.mount('/ui-kit',StaticFiles(directory=ROOT/'ui-kit',html=True))\n"
        if tool != 'ascii':
            server += "app.mount('/',StaticFiles(directory=ROOT/'frontend',html=True))\n"
            page = target / 'frontend/index.html'
            page.write_text(page.read_text(encoding='utf-8').replace('AmuzAnyToolkit', name), encoding='utf-8')
            if tool == 'morse':
                app = target / 'frontend/app.js'
                code = app.read_text(encoding='utf-8')
                code = code.replace("import {mountUpscaler} from './upscaler.js';", '').replace("import {mountDownloader} from './downloader.js';", '')
                start = code.index('function route(){')
                code = code[:start] + "function route(){release();stopSound();clearTimeout(gapTimer);target=null;document.body.classList.add('morse-page');document.body.classList.toggle('morse-compact',compactMorse);morse();}window.addEventListener('hashchange',route);route();\n"
                app.write_text(code, encoding='utf-8')
            else:
                mount = 'mountUpscaler' if tool == 'upscaler' else 'mountDownloader'
                module = 'upscaler' if tool == 'upscaler' else 'downloader'
                (target/'frontend/app.js').write_text(f"import {{{mount}}} from './{module}.js';\nimport {{mountAppearance}} from '../ui-kit/appearance.js';\ndocument.body.classList.add('{ 'upscale' if tool == 'upscaler' else 'download'}-page');\nconst dispose={mount}(document.querySelector('#app'));\nmountAppearance(document.querySelector('#appearance-trigger'));\nwindow.addEventListener('pagehide',dispose,{{once:true}});\n", encoding='utf-8')
        (target / 'server.py').write_text(server, encoding='utf-8')
        requirements = 'fastapi>=0.115,<1\nuvicorn[standard]>=0.30,<1\n'
        if tool == 'upscaler':
            requirements += 'Pillow>=11,<13\npython-multipart>=0.0.20,<1\nnumpy>=2,<3\nopencv-contrib-python-headless>=4.12,<5\n'
        elif tool in {'ascii', 'downloader'}:
            requirements = (ROOT/'tools/ascii/requirements.txt').read_text(encoding='utf-8')
            if tool == 'downloader':
                requirements += '\nimageio-ffmpeg>=0.6,<1\n'
        (target / 'requirements.txt').write_text(requirements, encoding='utf-8')
        build = '\nnpm --prefix tools/ascii/frontend ci\nnpm --prefix tools/ascii/frontend run build\n' if tool == 'ascii' else '\n'
        description = {'ascii':'Студия ASCII-арта из фото и видео.', 'morse':'Тренажёр русской и английской азбуки Морзе: карточки, напевы, приём и передача пробелом.', 'downloader':'Загрузка видео по ссылке с YouTube и Instagram, выбор качества и формата.', 'upscaler':'Локальное увеличение фотографий FSRCNN ×2/×4, сравнение и экспорт PNG/JPEG/WebP.'}[tool]
        readme = f'# {name}\n\n{description}\n\nСамостоятельный проект семейства [AmuzAnyToolBox](https://github.com/AmuzAnyToolBox). Общий хаб: [AmuzAnyToolkit](https://github.com/AmuzAnyToolBox/AmuzAnyToolkit).\n\n## Установка и запуск (Windows / PowerShell)\n\nТребуется Python 3.11+' + (' и Node.js 22.12+.' if tool == 'ascii' else '.') + f'\n\n```powershell\ngit clone https://github.com/AmuzAnyToolBox/{name}.git\ncd {name}\npython -m venv .venv\n.venv/Scripts/python.exe -m pip install -r requirements.txt{build}.venv/Scripts/python.exe run.py\n```\n\nОткройте http://127.0.0.1:8010. На Linux/macOS используйте `.venv/bin/python`. Порт меняется аргументом `--port 8011`.\n\n## Исходники\n\nПроект экспортирован из общего репозитория скриптом `scripts/export_projects.py`. Общий UI kit включён в `ui-kit/`. Изменения не синхронизируются автоматически: переносите их через общий исходник и повторный экспорт в новую папку.\n'
        if tool == 'downloader':
            readme += '\n`tools/ascii/backend` содержит общие проверенные сетевые и видео-модули, от которых зависит загрузчик; интерфейс ASCII сюда не включён. Скачивание доступно для общедоступных ссылок без авторизации.\n'
        if tool == 'upscaler':
            readme += '\nФото: до 20 МБ / 12 Мп; результат до 64 Мп. Модели включены с лицензией в `tools/upscaler/models`. GPU и облачный API не нужны. FSRCNN улучшает контуры, но не гарантирует восстановление утраченных деталей. Готовые файлы временные — скачайте их до остановки сервера.\n'
        (target/'README.md').write_text(readme,encoding='utf-8')
        print(target)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination',type=Path)
    export(parser.parse_args().destination.resolve())
