from decimal import Decimal

import pytest

import wandler
from wandler.einheiten import UnbekannteEinheit, UnpassendeBasis


def test_rechnet_laenge_um():
    assert wandler.wandle("1", "km", "m") == Decimal("1000")


def test_rechnet_zeit_um():
    assert wandler.wandle("90", "min", "h") == Decimal("1.5")


def test_unbekannte_einheit():
    with pytest.raises(UnbekannteEinheit):
        wandler.wandle("1", "km", "gibtsnicht")


def test_unpassende_basis():
    with pytest.raises(UnpassendeBasis):
        wandler.wandle("1", "km", "kg")


def test_liste_ist_sortiert():
    namen = wandler.einheiten()
    assert namen == sorted(namen)
    assert "km" in namen
