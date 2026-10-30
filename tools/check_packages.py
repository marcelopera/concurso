"""Build and smoke-test wheels outside the checkout, without editable installs."""

import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ("packages/contracts", "packages/pipeline", "packages/estudo/backend")


def run(*command, cwd=ROOT, env=None):
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"{command}:\n{result.stdout}\n{result.stderr}")
    return result.stdout


def main():
    with tempfile.TemporaryDirectory(prefix="concurso-wheels-") as tmp:
        root = Path(tmp)
        wheels, target = root / "wheels", root / "installed"
        run(
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--no-build-isolation",
            "--no-deps",
            "--wheel-dir",
            str(wheels),
            *(str(ROOT / package) for package in PACKAGES),
        )
        run(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--no-deps",
            "--target",
            str(target),
            *(str(wheel) for wheel in sorted(wheels.glob("*.whl"))),
        )
        if sys.platform == "win32":
            import tzdata

            shutil.copytree(Path(tzdata.__file__).parent, target / "tzdata")
        # A venv without pip or system packages cannot see this checkout's editables.
        isolated = root / "venv"
        venv.EnvBuilder(with_pip=False).create(isolated)
        python = isolated / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        env = dict(os.environ, PYTHONPATH=str(target))
        for module in ("estudo", "estudo.mapping", "concurso_pipeline"):
            run(str(python), "-m", module, "--help", cwd=root, env=env)
        run(
            str(python),
            "-c",
            "from pathlib import Path; "
            "from concurso_contracts import resource_file; "
            "from concurso_contracts.catalog.criar_demo import criar; "
            "from estudo.app import Application; from estudo.config import Settings; "
            "from concurso_pipeline.config import resource_file as pipeline_resource; "
            "assert resource_file('schemas','extraction-question.schema.json').is_file(); "
            "assert pipeline_resource('catalog','esquema.sql').is_file(); "
            "app=Application(Settings.from_env()); app.initialize(); "
            "assert app.question_page('', '', '', 1)['total']==20; "
            "con=app.study_db(); assert con.execute('PRAGMA user_version').fetchone()[0]==1; con.close()",
            cwd=root,
            env=env,
        )
    print("Wheels independentes: CLIs, contratos, catálogo sintético e migrações verificados fora do checkout.")


if __name__ == "__main__":
    main()
