import pytest

from lager.artikel import UnbekannterArtikel, ZuWenigBestand
from lager.bestand import Lager


@pytest.fixture
def lager(tmp_path):
    return Lager(tmp_path / "lager.json")


def test_anlegen_und_bestand(lager):
    lager.anlegen("A1", "Schraube", 10)
    assert lager.bestand("A1") == 10


def test_einlagern(lager):
    lager.anlegen("A1", "Schraube", 10)
    assert lager.einlagern("A1", 5).menge == 15


def test_auslagern(lager):
    lager.anlegen("A1", "Schraube", 10)
    assert lager.auslagern("A1", 4).menge == 6


def test_auslagern_zu_viel(lager):
    lager.anlegen("A1", "Schraube", 2)
    with pytest.raises(ZuWenigBestand):
        lager.auslagern("A1", 3)


def test_unbekannter_artikel(lager):
    with pytest.raises(UnbekannterArtikel):
        lager.bestand("gibtsnicht")


def test_wird_gesichert(tmp_path):
    pfad = tmp_path / "lager.json"
    Lager(pfad).anlegen("A1", "Schraube", 7)
    assert Lager(pfad).bestand("A1") == 7


def test_liste_ist_sortiert(lager):
    lager.anlegen("B", "zwei")
    lager.anlegen("A", "eins")
    assert [a.nummer for a in lager.liste()] == ["A", "B"]
