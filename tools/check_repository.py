"""Check portable paths, file size and local Markdown links without network access."""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
TEXT = {".md", ".py", ".js", ".jsx", ".mjs", ".json", ".jsonl", ".yaml", ".yml", ".toml", ".ps1", ".sql", ".html"}


def check() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    errors = []
    for name in result.stdout.decode("utf-8").split("\0"):
        path = ROOT / name
        if not name or not path.is_file():
            continue
        if path.stat().st_size > 5 * 1024 * 1024:
            errors.append(f"{name}: arquivo maior que 5 MiB; use armazenamento de dados.")
        if path.suffix.lower() not in TEXT:
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"(?i)[a-z]:[\\/]+users[\\/]+|/(?:Users|home)/[^/\s]+/", text):
            errors.append(f"{name}: caminho pessoal absoluto.")
        if path.suffix.lower() == ".md":
            for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
                link = link.split(' "')[0].strip("<>")
                parsed = urlsplit(link)
                if parsed.scheme or not parsed.path:
                    continue
                target = (path.parent / unquote(parsed.path)).resolve()
                if not target.exists():
                    errors.append(f"{name}: link local ausente: {link}")
    return errors


if __name__ == "__main__":
    failures = check()
    for failure in failures:
        print(failure)
    raise SystemExit(bool(failures))
