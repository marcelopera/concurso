"""Versioned resources shared by producers and consumers of the catalog."""

from importlib.resources import files


def resource_file(group: str, name: str):
    """Read assets from an installed wheel without relying on repository paths."""
    if group not in {"schemas", "catalog"} or "/" in name or "\\" in name or name in {".", ".."}:
        raise ValueError("Recurso de contrato inválido.")
    return files(f"concurso_contracts.{group}").joinpath(name)
