"""Ablage des Lagerbestands als JSON-Datei."""

import json
from pathlib import Path

from .artikel import Artikel

FORMAT_VERSION = 1


def laden(pfad: Path) -> dict[str, Artikel]:
    """Liest den Bestand. Fehlt die Datei, ist das Lager leer."""
    if not pfad.exists():
        return {}
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    artikel = {}
    for eintrag in roh.get("artikel", []):
        a = Artikel(
            nummer=eintrag["nummer"],
            name=eintrag["name"],
            menge=eintrag["menge"],
        )
        artikel[a.nummer] = a
    return artikel


def sichern(pfad: Path, artikel: dict[str, Artikel]) -> None:
    """Schreibt den Bestand."""
    roh = {
        "version": FORMAT_VERSION,
        "artikel": [
            {"nummer": a.nummer, "name": a.name, "menge": a.menge}
            for a in artikel.values()
        ],
    }
    pfad.write_text(json.dumps(roh, ensure_ascii=False, indent=2), encoding="utf-8")
