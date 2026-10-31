"""Verify the packaged runtime, external plans and progress across container restarts."""

import argparse
import json
import subprocess
import time
from http.client import HTTPException
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()


def request(url, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(
        url + path,
        data=data,
        method="PUT" if body is not None else "GET",
        headers={"Host": "127.0.0.1:8765", "Content-Type": "application/json"},
    )
    with urlopen(req, timeout=5) as response:
        return json.load(response)


def wait_ready(url):
    for _ in range(30):
        try:
            result = request(url, "/api/health")
            if not result["ok"] or result["content_occurrences"] != 20:
                raise RuntimeError("O catálogo demonstrativo não ficou disponível.")
            return
        except (URLError, ConnectionError, TimeoutError, HTTPException):
            time.sleep(1)
    raise RuntimeError("O contêiner não ficou saudável a tempo.")


def check_runtime(image, with_plan=False):
    command = [
        "docker",
        "run",
        "-d",
        "-p",
        "127.0.0.1:0:8765",
        "--read-only",
        "--tmpfs",
        "/tmp",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
    ]
    if with_plan:
        plans = Path(__file__).resolve().parents[1] / "plans"
        command += ["--mount", f"type=bind,source={plans},target=/app/plans,readonly"]
    command.append(image)
    if with_plan:
        command += [
            "python",
            "-m",
            "estudo",
            "serve",
            "--host",
            "0.0.0.0",
            "--init-plan",
            "/app/plans/apofp-2026/roadmap.json",
        ]
    container = run(*command)
    try:
        url = "http://" + run("docker", "port", container, "8765/tcp")
        wait_ready(url)
        with urlopen(url + "/", timeout=5) as response:
            if b"<!doctype html>" not in response.read().lower():
                raise RuntimeError("Frontend ausente na imagem.")
        bootstrap = request(url, "/api/bootstrap")
        if with_plan:
            if not bootstrap["totals"]["lessons"]:
                raise RuntimeError("Plano externo não foi importado.")
            activity = bootstrap["roadmap"]["days"][0]["activities"][0]["id"]
            request(url, "/api/roadmap/activities/" + activity, {"completed": True, "note": "smoke"})
            run("docker", "restart", container)
            url = "http://" + run("docker", "port", container, "8765/tcp")
            wait_ready(url)
            progress = request(url, "/api/bootstrap")["roadmap"]["days"][0]["activities"][0]
            if not progress["completed_at"] or progress["note"] != "smoke":
                raise RuntimeError("Progresso perdido após reiniciar o contêiner.")
        elif bootstrap["roadmap"] is not None:
            raise RuntimeError("A imagem incorporou um plano de estudo.")
    finally:
        print(run("docker", "logs", container))
        run("docker", "rm", "-f", "-v", container)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="concurso:test")
    image = parser.parse_args().image
    run(
        "docker",
        "run",
        "--rm",
        image,
        "python",
        "-c",
        "from pathlib import Path; import importlib.util; "
        "assert not list(Path('/app').rglob('*.pdf')), 'PDF na imagem'; "
        "assert not Path('/app/plans').exists(), 'Planos incorporados na imagem'; "
        "assert importlib.util.find_spec('concurso_pipeline') is None, 'Pipeline no runtime'",
    )
    check_runtime(image)
    check_runtime(image, with_plan=True)
    print("Imagem inicia sem PDFs/pipeline/planos; plano externo e progresso após reinício verificados.")


if __name__ == "__main__":
    main()
