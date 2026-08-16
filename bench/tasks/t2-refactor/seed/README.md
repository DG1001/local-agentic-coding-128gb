# wandler

Rechnet Werte zwischen Einheiten um.

    import wandler
    wandler.wandle("1", "km", "m")

Eigene Einheiten:

    wandler.registriere("meile", "laenge", "1609.344")

Kommandozeile:

    python -m wandler.cli 1 km m
    python -m wandler.cli --liste

Tests:

    python -m pytest
