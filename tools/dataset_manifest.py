"""Create or verify a private artifact inventory; never uploads any data."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(root: Path, provenance: dict) -> dict:
    root = root.resolve(strict=True)
    files = []
    for path in sorted(root.rglob("*")):
        if (
            path.is_symlink()
            or not path.is_file()
            or any(p in {".git", "__pycache__", "node_modules"} for p in path.relative_to(root).parts)
        ):
            continue
        files.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {"manifest_version": 1, "provenance": provenance, "files": files}


def verify(root: Path, manifest: dict) -> None:
    root = root.resolve(strict=True)
    if manifest.get("manifest_version") != 1 or not isinstance(manifest.get("files"), list):
        raise ValueError("Formato de manifesto desconhecido.")
    seen = set()
    for entry in manifest["files"]:
        name = PurePosixPath(entry["path"])
        if name.is_absolute() or ".." in name.parts or "\\" in str(name) or ":" in str(name) or str(name) in seen:
            raise ValueError("Caminho inválido ou duplicado no manifesto.")
        seen.add(str(name))
        path = root.joinpath(*name.parts).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f"Arquivo ausente ou fora do conjunto: {name}")
        if path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            raise ValueError(f"Integridade divergente: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify"))
    parser.add_argument("root", type=Path)
    parser.add_argument("manifest", type=Path, help="Arquivo fora da pasta inventariada; criação recusa sobrescrita.")
    parser.add_argument(
        "--provenance", type=Path, help="JSON com fonte, modelo, versão, prompt e data quando conhecidos."
    )
    args = parser.parse_args()
    if args.command == "verify":
        verify(args.root, json.loads(args.manifest.read_text(encoding="utf-8")))
        print("Integridade verificada.")
        return
    if args.manifest.resolve().is_relative_to(args.root.resolve()):
        parser.error("Salve o manifesto fora da pasta inventariada.")
    provenance = (
        json.loads(args.provenance.read_text(encoding="utf-8"))
        if args.provenance
        else {
            "status": "legacy-unrecorded",
            "note": "Proveniência não informada; recuperar registros originais antes de publicar.",
        }
    )
    manifest = inventory(args.root, provenance)
    with args.manifest.open("x", encoding="utf-8") as destination:
        json.dump(manifest, destination, ensure_ascii=False, indent=2)
        destination.write("\n")
    print(f"{len(manifest['files'])} arquivos inventariados.")


if __name__ == "__main__":
    main()
