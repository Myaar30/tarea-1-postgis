"""Único punto de entrada, sin dependencias Python en el host."""
import pathlib
import shutil
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent
docker = shutil.which('docker')
if not docker:
    candidate = pathlib.Path('C:/Program Files/Docker/Docker/resources/bin/docker.exe')
    docker = str(candidate) if candidate.exists() else 'docker'
subprocess.run([docker, 'compose', 'up', '-d', '--wait'], cwd=root, check=True)
subprocess.run([docker, 'compose', 'exec', '-T', 'db', 'python3',
                '/trabajo/scripts/pipeline.py', *sys.argv[1:]], cwd=root, check=True)
