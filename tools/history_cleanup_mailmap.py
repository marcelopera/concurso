"""Create a private mailmap from an explicit, owner-reviewed identity list."""

import argparse
import json
import os
import re
import stat
import subprocess
from pathlib import Path

from history_cleanup_common import reject_path_inside_git_repository

EMAIL = re.compile(r"^[^\s<>@]+@[^\s<>@]+$")
MAILMAP_EMAIL = re.compile(r"<([^<>]+)>")


def git(repository: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def require_private_file(path: Path, repository: Path) -> Path:
    resolved = path.resolve(strict=True)
    reject_path_inside_git_repository(resolved, repository, "A lista de identidades")
    file_stat = resolved.stat()
    if not stat.S_ISREG(file_stat.st_mode) or (os.name == "posix" and file_stat.st_mode & 0o077):
        raise ValueError("A lista precisa ser regular e, em POSIX, ter permissão 0600.")
    return resolved


def raw_identity_pairs(repository: Path) -> set[tuple[str, str]]:
    output = subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "log",
            "--all",
            "-z",
            "--format=tformat:%an%x00%ae%x00%cn%x00%ce%x00",
        ],
        capture_output=True,
        check=True,
    ).stdout
    fields = [field for field in output.split(b"\0") if field]
    if len(fields) % 4:
        raise ValueError("Não foi possível interpretar com segurança as identidades do histórico.")
    pairs = set()
    for index in range(0, len(fields), 4):
        try:
            author_name, author_email, committer_name, committer_email = (
                field.decode("utf-8") for field in fields[index : index + 4]
            )
        except UnicodeDecodeError as error:
            raise ValueError("O histórico contém identidade fora de UTF-8; nenhuma lista foi criada.") from error
        pairs.add((author_name, author_email))
        pairs.add((committer_name, committer_email))
    taggers = subprocess.run(
        ["git", "-C", str(repository), "for-each-ref", "--format=%(taggername)%00%(taggeremail)"],
        capture_output=True,
        check=True,
    ).stdout
    for line in taggers.splitlines():
        identity = line.split(b"\0")
        if len(identity) == 2 and all(identity):
            try:
                tagger_name, tagger_email = (field.decode("utf-8") for field in identity)
            except UnicodeDecodeError as error:
                raise ValueError("O histórico contém identidade de tag fora de UTF-8.") from error
            pairs.add((tagger_name, tagger_email.strip().strip("<>")))
    return pairs


def mailmap_pairs(path: Path, repository: Path) -> tuple[tuple[str, str], set[tuple[str, str]]]:
    mailmap = require_private_file(path, repository)
    canonical_identities = set()
    source_identities = set()
    for line in mailmap.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        matches = list(MAILMAP_EMAIL.finditer(line))
        if len(matches) != 2:
            raise ValueError("O mailmap contém uma linha que não corresponde ao formato exato gerado pela ferramenta.")
        canonical_name = line[: matches[0].start()].strip()
        source_name = line[matches[0].end() : matches[1].start()].strip()
        canonical_email, source_email = (match.group(1) for match in matches)
        if (
            not canonical_name
            or not source_name
            or not EMAIL.fullmatch(canonical_email)
            or not EMAIL.fullmatch(source_email)
        ):
            raise ValueError("O mailmap contém uma identidade em formato inválido.")
        canonical_identities.add((canonical_name, canonical_email))
        source_identities.add((source_name, source_email))
    if len(canonical_identities) != 1 or not source_identities:
        raise ValueError("O mailmap precisa mapear identidades explícitas para um único destino canônico.")
    if len(source_identities) != len(mailmap.read_text(encoding="utf-8").splitlines()):
        raise ValueError("O mailmap contém identidades duplicadas ou linhas inválidas.")
    return canonical_identities.pop(), source_identities


def validate_applied_mailmap(repository: Path, path: Path) -> dict[str, int | bool]:
    canonical, sources = mailmap_pairs(path, repository)
    after_pairs = raw_identity_pairs(repository)
    remaining_sources = len(sources & after_pairs)
    canonical_present = canonical in after_pairs
    return {
        "mapped_identity_count": len(sources),
        "source_identities_remaining": remaining_sources,
        "canonical_identity_present": canonical_present,
        "passed": remaining_sources == 0 and canonical_present,
    }


def load_identities(path: Path) -> list[dict[str, str]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or document.get("version") != 1
        or not isinstance(document.get("identities"), list)
    ):
        raise ValueError("Formato da lista privada de identidades desconhecido.")
    identities = document["identities"]
    seen = set()
    for identity in identities:
        if not isinstance(identity, dict) or set(identity) != {"name", "email"}:
            raise ValueError("Cada identidade deve conter apenas name e email.")
        name = identity["name"]
        email = identity["email"]
        if (
            not isinstance(name, str)
            or not name.strip()
            or any(char in name for char in "\r\n<>\0")
            or not isinstance(email, str)
            or not EMAIL.fullmatch(email)
        ):
            raise ValueError("A lista contém uma identidade em formato inválido.")
        pair = (name, email)
        if pair in seen:
            raise ValueError("A lista contém uma identidade duplicada.")
        seen.add(pair)
    if not identities:
        raise ValueError("A lista privada precisa identificar ao menos uma identidade do proprietário.")
    return identities


def create_mailmap(
    repository: Path,
    identities_file: Path,
    output: Path,
    canonical_name: str,
    canonical_email: str,
) -> int:
    repository = repository.resolve(strict=True)
    git(repository, "rev-parse", "--git-dir")
    identities_file = require_private_file(identities_file, repository)
    output = reject_path_inside_git_repository(output, repository, "O mailmap")
    if any(char in canonical_name for char in "\r\n<>\0") or not canonical_name.strip():
        raise ValueError("Nome canônico inválido.")
    if not EMAIL.fullmatch(canonical_email):
        raise ValueError("E-mail canônico inválido.")
    identities = load_identities(identities_file)
    known_pairs = raw_identity_pairs(repository)
    if any((identity["name"], identity["email"]) not in known_pairs for identity in identities):
        raise ValueError("Uma identidade declarada não aparece como autora ou committer no histórico.")
    if any(identity["email"].casefold() == canonical_email.casefold() for identity in identities):
        raise ValueError("Remova da lista a identidade que já é canônica.")

    lines = [
        f"{canonical_name} <{canonical_email}> {identity['name']} <{identity['email']}>\n" for identity in identities
    ]
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as mailmap:
        mailmap.writelines(lines)
    expected = f"{canonical_name} <{canonical_email}>"
    for identity in identities:
        result = subprocess.run(
            [
                "git",
                "-c",
                f"mailmap.file={output}",
                "-C",
                str(repository),
                "check-mailmap",
                f"{identity['name']} <{identity['email']}>",
            ],
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
        )
        if result.stdout.strip() != expected:
            raise ValueError("A validação do mailmap falhou para uma identidade exata.")
    return len(identities)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("identities", type=Path, help="JSON privado externo ao repositório, com permissão 0600.")
    parser.add_argument("output", type=Path, help="Mailmap temporário privado, criado com permissão 0600.")
    parser.add_argument("--canonical-name", required=True)
    parser.add_argument("--canonical-email", required=True)
    args = parser.parse_args()
    try:
        count = create_mailmap(
            args.repository,
            args.identities,
            args.output,
            args.canonical_name,
            args.canonical_email,
        )
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(f"Mailmap privado criado e validado para {count} identidades explicitamente informadas.")


if __name__ == "__main__":
    main()
