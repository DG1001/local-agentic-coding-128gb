"""Verdeckte Bewertung t2-refactor."""

from decimal import Decimal

import pytest

import wandler
from wandler.basis import eintragen
from wandler.einheiten import (
    STANDARD,
    Register,
    UnbekannteEinheit,
    UnpassendeBasis,
    WandlerFehler,
)


# --------------------------------------------------- Register selbst
def test_neues_register_ist_leer():
    assert Register().einheiten() == []


def test_register_rechnet_um():
    r = Register()
    r.registriere("m", "laenge", "1")
    r.registriere("km", "laenge", "1000")
    assert r.wandle("2", "km", "m") == Decimal("2000")


def test_register_kennt_fehlerklassen():
    r = Register()
    r.registriere("m", "laenge", "1")
    r.registriere("kg", "masse", "1")
    with pytest.raises(UnbekannteEinheit):
        r.wandle("1", "m", "gibtsnicht")
    with pytest.raises(UnpassendeBasis):
        r.wandle("1", "m", "kg")
    with pytest.raises(WandlerFehler):
        r.registriere("x", "laenge", "0")


def test_einheiten_sind_sortiert():
    r = Register()
    for name in ("z", "a", "m"):
        r.registriere(name, "laenge", "1")
    assert r.einheiten() == ["a", "m", "z"]


# --------------------------------------------------- Unabhaengigkeit
def test_zwei_register_stoeren_sich_nicht():
    a, b = Register(), Register()
    a.registriere("elle", "laenge", "0.6")
    assert "elle" in a.einheiten()
    assert "elle" not in b.einheiten()


def test_eigenes_register_beruehrt_standard_nicht():
    r = Register()
    r.registriere("meile", "laenge", "1609.344")
    assert "meile" not in STANDARD.einheiten()
    assert "meile" not in wandler.einheiten()


def test_standard_beruehrt_eigenes_register_nicht():
    r = Register()
    vorher = list(r.einheiten())
    wandler.registriere("furlong", "laenge", "201.168")
    assert r.einheiten() == vorher


# --------------------------------------------------- kopie
def test_kopie_hat_denselben_inhalt():
    a = Register()
    a.registriere("m", "laenge", "1")
    a.registriere("km", "laenge", "1000")
    b = a.kopie()
    assert b.einheiten() == a.einheiten()
    assert b.wandle("1", "km", "m") == Decimal("1000")


def test_kopie_ist_danach_unabhaengig():
    a = Register()
    a.registriere("m", "laenge", "1")
    b = a.kopie()
    b.registriere("elle", "laenge", "0.6")
    assert "elle" not in a.einheiten()
    a.registriere("spanne", "laenge", "0.2")
    assert "spanne" not in b.einheiten()


# --------------------------------------------------- STANDARD
def test_standard_ist_gefuellt():
    namen = STANDARD.einheiten()
    for erwartet in ("mm", "cm", "m", "km", "g", "kg", "s", "h"):
        assert erwartet in namen


def test_standard_ist_ein_register():
    assert isinstance(STANDARD, Register)


# --------------------------------------------------- Rueckwaertskompatibel
def test_modulfunktionen_arbeiten_auf_standard():
    assert wandler.wandle("1", "km", "m") == Decimal("1000")
    assert wandler.wandle("90", "min", "h") == Decimal("1.5")


def test_modul_registriere_landet_in_standard():
    wandler.registriere("meile2", "laenge", "1609.344")
    assert "meile2" in STANDARD.einheiten()
    assert wandler.wandle("1", "meile2", "m") == Decimal("1609.344")


def test_modul_einheiten_spiegelt_standard():
    assert wandler.einheiten() == STANDARD.einheiten()


def test_modulfehler_bleiben():
    with pytest.raises(UnbekannteEinheit):
        wandler.wandle("1", "km", "gibtsnicht")
    with pytest.raises(UnpassendeBasis):
        wandler.wandle("1", "km", "kg")


# --------------------------------------------------- basis.eintragen
def test_eintragen_nimmt_register_entgegen():
    r = Register()
    eintragen(r)
    assert "km" in r.einheiten()
    assert r.wandle("1", "km", "m") == Decimal("1000")


def test_leeren_ist_weg():
    import wandler.einheiten as modul

    assert not hasattr(modul, "leeren")
