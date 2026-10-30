"""CLI for the local application, external plans and progress backup/restore."""

import argparse
import sqlite3
import sys
from pathlib import Path

from estudo.app import Application
from estudo.config import Settings
from estudo.db.backup import copy_database
from estudo.initialization import initialize_once
from estudo.services import plans


def main(argv=None):
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Iniciar o servidor local.")
    serve.add_argument("--port", type=int, default=settings.port)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--init-plan", type=Path, help="Instalar este plano somente se não existir progresso.")
    init = commands.add_parser("init", help="Inicializar um plano somente se não existir progresso.")
    init.add_argument("--plan", type=Path, default=settings.plan_file)
    plan = commands.add_parser("plan", help="Importar plano preservando o progresso e criando backup.")
    plan.add_argument("plan_file", type=Path)
    plan.add_argument("database", type=Path)
    for name in ("backup", "restore"):
        command = commands.add_parser(name)
        command.add_argument("source", type=Path)
        command.add_argument("destination", type=Path)
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"--host", "--port", "--init-plan"}:
        argv.insert(0, "serve")
    args = parser.parse_args(argv)
    app = Application(settings)
    try:
        if args.command == "init":
            if args.plan is None:
                parser.error("Informe --plan ou defina ESTUDO_PLAN_FILE.")
            initialize_once(app, args.plan)
        elif args.command == "plan":
            plans.install(args.database, args.plan_file)
        elif args.command in {"backup", "restore"}:
            copy_database(args.source, args.destination)
            print(f"Banco copiado para {args.destination}")
        else:
            if not 1 <= args.port <= 65535:
                parser.error("A porta deve estar entre 1 e 65535.")
            if args.init_plan:
                initialize_once(app, args.init_plan)
            app.initialize()
            server = app.http_server((args.host, args.port))
            print(f"Sistema de estudo disponível em http://127.0.0.1:{server.server_port}", flush=True)
            try:
                server.serve_forever(poll_interval=0.5)
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
    except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
