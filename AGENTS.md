# AmuzAnyToolkit

One local monorepo. Run commands from this root. Preserve the original sibling glyph-studio checkout: it is the migration source and is not part of ordinary edits here.

- `frontend/`: buildless hub and Morse trainer. Morse alphabet/timing logic: `frontend/morse.js`; browser interaction: `frontend/app.js`.
- `tools/ascii/`: migrated full Vue/FastAPI ASCII studio. Read its `AGENTS.md` for ASCII behavior and invariants; root commands below supersede its old standalone paths and startup instructions.
- `tools/downloader/`: AmuzFetch APIs under `/api/downloader`; YouTube/Instagram metadata via CheckedYoutubeDL and bounded pinned downloads, output via imageio-ffmpeg. Routes must be included before the root static mount. Frontend: `frontend/downloader.js` at `#download`. Test with `tests/test_downloader.py`.
- `tools/upscaler/`: AmuzUpscale, CPU FSRCNN ×2/×4 with bundled licensed models; API `/api/upscaler` and buildless frontend `frontend/upscaler.js` at `#upscale`. Enforce 20 MB/12 MP input and 64 MP output. Preserve alpha and EXIF orientation; do not expose partial output or silently substitute Lanczos for AI. Tests: `tests/test_upscaler.py`.
- `ui-kit/`: shared themes, palette tokens, scrollbar implementation and component gallery. ASCII imports from this directory at build time; hub/Morse load it directly. Do not create disconnected duplicate theme definitions.
- `server.py`: reuses the ASCII FastAPI app and its router lifespans, then serves `/ascii/`, `/ui-kit/` and `/`. Keep `/api` routes unchanged. Python backend modules use package-relative imports; import them externally as `tools.ascii.backend.*`. Never add tools/ascii to sys.path or require a PyCharm Sources Root workaround.

Setup: `python -m venv .venv`, `.venv/Scripts/python.exe -m pip install -r requirements-dev.txt`, `npm.cmd --prefix tools/ascii/frontend ci`, `npm.cmd run build`. Run `.venv/Scripts/python.exe run.py` on port 8010.

Checks: `npm.cmd test`; `.venv/Scripts/python.exe -m pytest tests tools/ascii/backend -q`. Build before integration tests. Node >=22.12 and Python >=3.11. Docker setup lives only at root. Do not copy `.git`, virtual environments, IDE state or node_modules into tracked source. Do not commit, push or publish unless requested.
