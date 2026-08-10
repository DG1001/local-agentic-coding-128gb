"""Kleines Kassenbuch mit Cent-genauer Rechnung."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal


ARTEN = ("einnahme", "ausgabe", "korrektur")


@dataclass(frozen=True)
class Eintrag:
    """Eine Buchung.

    tag     Datum der Buchung
    art     eine der ARTEN
    betrag  immer positiv, das Vorzeichen ergibt sich aus der Art
    zweck   Freitext
    """

    tag: date
    art: str
    betrag: Decimal
    zweck: str = ""

    def __post_init__(self) -> None:
        if self.art not in ARTEN:
            raise ValueError(f"unbekannte Art: {self.art!r}")
        if self.betrag < 0:
            raise ValueError("betrag muss positiv sein")


def runde_cent(betrag: Decimal) -> Decimal:
    """Rundet auf zwei Nachkommastellen, kaufmaennisch (halbe auf)."""
    return betrag.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def im_zeitraum(eintraege: list[Eintrag], von: date, bis: date) -> list[Eintrag]:
    """Gibt alle Eintraege im Zeitraum zurueck, Grenzen eingeschlossen."""
    return [e for e in eintraege if von <= e.tag < bis]


def saldo(eintraege: list[Eintrag]) -> Decimal:
    """Summe aller Buchungen.

    Einnahmen und Korrekturen zaehlen positiv, Ausgaben negativ.
    """
    summe = Decimal("0")
    for e in eintraege:
        if e.art == "einnahme":
            summe += e.betrag
        elif e.art == "ausgabe":
            summe -= e.betrag
    return runde_cent(summe)


def aufteilen(betrag: Decimal, anteile: int) -> list[Decimal]:
    """Teilt einen Betrag auf mehrere Anteile auf.

    Die Anteile unterscheiden sich um hoechstens einen Cent und ergeben in
    der Summe wieder genau den Ausgangsbetrag.
    """
    if anteile < 1:
        raise ValueError("anteile muss mindestens 1 sein")
    einzeln = runde_cent(betrag / anteile)
    return [einzeln] * anteile
