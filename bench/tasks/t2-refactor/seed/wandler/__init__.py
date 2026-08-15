"""wandler — Umrechnung zwischen Einheiten."""

from .basis import eintragen
from .einheiten import (
    Register,
    UnbekannteEinheit,
    UnpassendeBasis,
    WandlerFehler,
    einheiten,
    registriere,
    wandle,
)

# Standard-Register initialisieren und mitgelieferte Einheiten eintragen
_STANDARD: Register = Register()
eintragen(_STANDARD)

# Exporterliches Standard-Register verfügbar machen
STANDARD = _STANDARD

__all__ = [
    "WandlerFehler",
    "UnbekannteEinheit",
    "UnpassendeBasis",
    "registriere",
    "wandle",
    "einheiten",
    "STANDARD",
]
