# lager

Kleine Lagerverwaltung. Der Bestand liegt als JSON-Datei.

    from pathlib import Path
    from lager.bestand import Lager

    l = Lager(Path("lager.json"))
    l.anlegen("A1", "Schraube", 100)
    l.auslagern("A1", 10)

Kommandozeile:

    python -m lager.cli anlegen A1 Schraube --menge 100
    python -m lager.cli einlagern A1 50
    python -m lager.cli auslagern A1 10
    python -m lager.cli liste

Tests:

    python -m pytest
