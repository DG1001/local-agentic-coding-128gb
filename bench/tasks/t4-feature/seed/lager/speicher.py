"""Ablage des Lagerbestands als JSON-Datei."""

import json
from pathlib import Path


from .artikel import Artikel

Reservierungsschluessel = tuple[str, str]  # (artikel_nummer, auftrag)

FORMAT_VERSION = 2


def laden(pfad: Path) -> tuple[dict[str, Artikel], dict[Reservierungsschluessel, int]]:
    """Liest den Bestand. Fehlt die Datei, ist das Lager leer.
    Rueckgabe: (artikeln, reservierungen)
    reservierungen ist ein Dict (artikel_nummer, auftrag) -> menge.
    """
    if not pfad.exists():
        return {}, {}
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    version = roh.get("version", 1)
    artikel = {}
    for eintrag in roh.get("artikel", []):
        a = Artikel(
            nummer=eintrag["nummer"],
            name=eintrag["name"],
            menge=eintrag["menge"],
        )
        artikel[a.nummer] = a
    reservierungen: dict[Reservierungsschluessel, int] = {}
    if version >= 2:
        for r in roh.get("reservierungen", []):
            key = (r["nummer"], r["auftrag"])
            reservierungen[key] = r["menge"]
    return artikel, reservierungen


def sichern(pfad: Path, artikel: dict[str, Artikel], reservierungen: dict[Reservierungsschluessel, int]) -> None:
    """Schreibt den Bestand mit Reservierungen."""
    roh = {
        "version": FORMAT_VERSION,
        "artikel": [
            {"nummer": a.nummer, "name": a.name, "menge": a.menge}
            for a in artikel.values()
        ],
        "reservierungen": [
            {"nummer": n, "auftrag": a, "menge": m}
            for (n, a), m in reservierungen.items()
        ],
    }
    pfad.write_text(json.dumps(roh, ensure_ascii=False, indent=2), encoding="utf-8")
