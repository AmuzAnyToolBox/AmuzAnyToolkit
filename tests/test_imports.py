"""Regression checks: imports must work without server.py changing sys.path."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def test_backend_imports_in_a_fresh_python_process():
    result = subprocess.run(
        [sys.executable, '-c',
         'from tools.ascii.backend import main, characters, videos, video_render, remote; '
         'from server import app; assert app is main.app'],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr

def test_compatibility_launcher_as_a_module_and_as_a_script():
    for args, cwd in [
        (['-m', 'tools.ascii.run', '--help'], ROOT),
        ([str(ROOT / 'tools/ascii/run.py'), '--help'], ROOT.parent),
        ([str(ROOT / 'run.py'), '--help'], ROOT.parent),
    ]:
        result = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, result.stderr
        assert '--port' in result.stdout
