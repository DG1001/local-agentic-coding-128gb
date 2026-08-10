"""Kommandozeile von wandler."""

import argparse
import sys

from . import einheiten as alle_einheiten
from . import wandle
from .einheiten import WandlerFehler


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="wandler", description="rechnet Einheiten um")
    p.add_argument("wert", nargs="?", help="umzurechnender Wert")
    p.add_argument("von", nargs="?", help="Ausgangseinheit")
    p.add_argument("nach", nargs="?", help="Zieleinheit")
    p.add_argument("--liste", action="store_true", help="bekannte Einheiten zeigen")
    args = p.parse_args(argv)

    if args.liste:
        print(" ".join(alle_einheiten()))
        return 0

    if not (args.wert and args.von and args.nach):
        p.error("wert, von und nach werden gebraucht")

    try:
        print(wandle(args.wert, args.von, args.nach))
    except WandlerFehler as fehler:
        print(f"Fehler: {fehler}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
