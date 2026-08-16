"""Kommandozeile des Lagers."""

import argparse
import sys
from pathlib import Path

from .artikel import LagerFehler, UnbekannteReservierung
from .bestand import Lager


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="lager", description="kleine Lagerverwaltung")
    p.add_argument("--datei", type=Path, default=Path("lager.json"))
    unter = p.add_subparsers(dest="befehl", required=True)

    a = unter.add_parser("anlegen")
    a.add_argument("nummer")
    a.add_argument("name")
    a.add_argument("--menge", type=int, default=0)

    e = unter.add_parser("einlagern")
    e.add_argument("nummer")
    e.add_argument("menge", type=int)

    u = unter.add_parser("auslagern")
    u.add_argument("nummer")
    u.add_argument("menge", type=int)

    unter.add_parser("liste")

    # Neue Befehle
    r = unter.add_parser("reservieren")
    r.add_argument("nummer")
    r.add_argument("menge", type=int)
    r.add_argument("auftrag")

    f = unter.add_parser("freigeben")
    f.add_argument("nummer")
    f.add_argument("auftrag")

    ent = unter.add_parser("entnehmen")
    ent.add_argument("nummer")
    ent.add_argument("auftrag")

    args = p.parse_args(argv)
    lager = Lager(args.datei)

    try:
        if args.befehl == "anlegen":
            lager.anlegen(args.nummer, args.name, args.menge)
        elif args.befehl == "einlagern":
            lager.einlagern(args.nummer, args.menge)
        elif args.befehl == "auslagern":
            lager.auslagern(args.nummer, args.menge)
        elif args.befehl == "reservieren":
            result = lager.reservieren(args.nummer, args.menge, args.auftrag)
            print(result)
        elif args.befehl == "freigeben":
            result = lager.freigeben(args.nummer, args.auftrag)
            print(result)
        elif args.befehl == "entnehmen":
            result = lager.entnehmen(args.nummer, args.auftrag)
            print(result)
        elif args.befehl == "liste":
            for art in lager.liste():
                r = lager.reserviert(art.nummer)
                v = lager.verfuegbar(art.nummer)
                print(f"{art.nummer}\t{art.name}\t{art.menge}\t{r}\t{v}")
    except (LagerFehler, ValueError) as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
