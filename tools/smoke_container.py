"""Verify a built image starts, serves the demo and contains no PDFs."""

import json
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()


def main():
    image = "concurso:test"
    run(
        "docker",
        "run",
        "--rm",
        image,
        "python",
        "-c",
        "from pathlib import Path; assert not list(Path('/app').rglob('*.pdf')), 'PDF na imagem'",
    )
    container = run("docker", "run", "-d", "-p", "127.0.0.1:8765:8765", image)
    try:
        for _ in range(30):
            try:
                with urlopen("http://127.0.0.1:8765/api/health", timeout=2) as response:
                    result = json.load(response)
                if not result["ok"] or result["content_occurrences"] != 20:
                    raise RuntimeError("O catálogo demonstrativo não ficou disponível.")
                with urlopen("http://127.0.0.1:8765/", timeout=2) as response:
                    if b"<!doctype html>" not in response.read().lower():
                        raise RuntimeError("Frontend ausente na imagem.")
                print("Imagem inicia com catálogo demonstrativo, migrações e frontend; sem PDFs.")
                return
            except URLError:
                time.sleep(1)
        raise RuntimeError("O contêiner não ficou saudável a tempo.")
    finally:
        print(run("docker", "logs", container))
        run("docker", "rm", "-f", container)


if __name__ == "__main__":
    main()
