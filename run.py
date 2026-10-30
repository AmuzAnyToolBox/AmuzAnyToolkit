"""Single entry point for the hub, Morse trainer and ASCII studio."""
from pathlib import Path
import argparse
import os
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(description='AmuzAnyToolkit — hub + Morse + ASCII')
    parser.add_argument('--port', type=int, default=8010)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--reload', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    environment = root / '.venv'
    interpreter = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if interpreter.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        print(f'Using project Python: {interpreter}', flush=True)
        raise SystemExit(subprocess.call([str(interpreter), str(root / 'run.py'), *sys.argv[1:]]))
    try:
        import uvicorn
    except ModuleNotFoundError:
        raise SystemExit(
            f'Install dependencies using this interpreter:\n'
            f'"{sys.executable}" -m pip install -r "{root / "requirements.txt"}"'
        ) from None
    os.chdir(root)
    print(f'AmuzAnyToolkit: http://{args.host}:{args.port}', flush=True)
    uvicorn.run('server:app', host=args.host, port=args.port, reload=args.reload, app_dir=str(root))

if __name__ == '__main__':
    main()
