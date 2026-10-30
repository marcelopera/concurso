"""Local server and safe SQLite backup/restore commands."""

import argparse
import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path


def copy_database(source: Path, destination: Path) -> None:
    source, destination = source.resolve(), destination.resolve()
    if not source.is_file():
        raise ValueError(f"Banco de origem não encontrado: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise ValueError(f"O destino já existe: {destination}") from None
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as src:
            if src.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("O banco de origem não passou na verificação de integridade.")
            with closing(sqlite3.connect(destination)) as dst:
                src.backup(dst)
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main():
    if len(sys.argv) == 1 or sys.argv[1].startswith("-"):
        import server

        server.main()
        return
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command")
    plan = commands.add_parser("plan", help="Importar um plano JSON preservando o progresso e criando backup.")
    plan.add_argument("plan_file", type=Path)
    plan.add_argument("database", type=Path)
    for name in ("backup", "restore"):
        command = commands.add_parser(name)
        command.add_argument("source", type=Path)
        command.add_argument("destination", type=Path)
    args, rest = parser.parse_known_args()
    if args.command:
        if rest:
            parser.error("argumentos não reconhecidos: " + " ".join(rest))
        try:
            if args.command == "plan":
                import roadmap

                roadmap.install(args.database, args.plan_file)
                return
            copy_database(args.source, args.destination)
        except (OSError, ValueError, sqlite3.Error) as exc:
            parser.exit(1, f"{exc}\n")
        print(f"Banco copiado para {args.destination}")


if __name__ == "__main__":
    main()
