import pytest
import json

from lager.artikel import UnbekannterArtikel, ZuWenigBestand, UnbekannteReservierung
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


# Neue Tests fuer Reservierungen

def test_reservieren(lager):
    lager.anlegen("A1", "Schraube", 10)
    neu = lager.reservieren("A1", 5, "auftrag-42")
    assert neu == 5  # verfuegbar = 10 - 5
    assert lager.reserviert("A1") == 5


def test_reservieren_zu_wenig(lager):
    lager.anlegen("A1", "Schraube", 3)
    with pytest.raises(ZuWenigBestand):
        lager.reservieren("A1", 5, "auftrag-42")


def test_reservieren_positiv_menge(lager):
    lager.anlegen("A1", "Schraube", 10)
    with pytest.raises(ValueError):
        lager.reservieren("A1", 0, "auftrag-42")
    with pytest.raises(ValueError):
        lager.reservieren("A1", -1, "auftrag-42")


def test_reservieren_doppelte_auftrag_addiert(lager):
    """Derselbe Auftrag mehrfach denselben Artikel: Mengen addieren sich."""
    lager.anlegen("A1", "Schraube", 10)
    lager.reservieren("A1", 3, "auftrag-42")
    assert lager.reserviert("A1") == 3
    neu = lager.reservieren("A1", 2, "auftrag-42")
    assert neu == 5  # 5 reserved, 5 available
    assert lager.reserviert("A1") == 5


def test_freigeben(lager):
    lager.anlegen("A1", "Schraube", 10)
    lager.reservieren("A1", 5, "auftrag-42")
    # Nach freigeben ist wieder voller Bestand verfuegbar
    assert lager.freigeben("A1", "auftrag-42") == 10  # wieder 10 verfuegbar (bestand - 0 reserviert)
    assert lager.reserviert("A1") == 0


def test_freigeben_unkannte_reservierung(lager):
    lager.anlegen("A1", "Schraube", 10)
    with pytest.raises(UnbekannteReservierung):
        lager.freigeben("A1", "anderer-auftrag")


def test_entnehmen(lager):
    lager.anlegen("A1", "Schraube", 10)
    lager.reservieren("A1", 5, "auftrag-42")
    neu_bestand = lager.entnehmen("A1", "auftrag-42")
    assert neu_bestand == 5  # 10 - 5 = 5
    assert lager.reserviert("A1") == 0


def test_entnehmen_unkannte_reservierung(lager):
    lager.anlegen("A1", "Schraube", 10)
    with pytest.raises(UnbekannteReservierung):
        lager.entnehmen("A1", "anderer-auftrag")


def test_reserviert_liefert_summe(lager):
    lager.anlegen("A1", "Schraube", 10)
    lager.reservieren("A1", 3, "auftrag-42")
    lager.reservieren("A1", 2, "auftrag-43")
    assert lager.reserviert("A1") == 5


def test_verfuegbar_ist_best_minus_reserviert(lager):
    lager.anlegen("A1", "Schraube", 10)
    lager.reservieren("A1", 4, "auftrag-42")
    assert lager.verfuegbar("A1") == 6


def test_reservierungen_liefert_kopie(lager):
    lager.anlegen("A1", "Schraube", 10)
    lager.reservieren("A1", 3, "auftrag-42")
    res = lager.reservierungen("A1")
    res["auftrag-99"] = 99  # Aenderung sollte nicht wirken
    assert lager.reserviert("A1") == 3  # Unveraendert


def test_laden_alter_format_1(lager, tmp_path):
    """Alte Format-1 Dateien sollen ladbar sein, haben aber keine Reservierungen."""
    pfad = tmp_path / "alt_lager.json"
    # Format 1 Datei schreiben (ohne version und reservierungen Felder)
    pfad.write_text('{"artikel": [{"nummer": "A1", "name": "Schraube", "menge": 10}]}')
    l = Lager(pfad)
    assert l.bestand("A1") == 10
    assert l.reserviert("A1") == 0
    assert l.verfuegbar("A1") == 10


def test_neues_format_sichert_reservierungen(lager, tmp_path):
    """Neues Format sollte Reservierungen sichern und laden."""
    pfad = tmp_path / "lager.json"
    lager.anlegen("A1", "Schraube", 10)
    lager.reservieren("A1", 4, "auftrag-42")
    # Datei prüfen
    text = pfad.read_text(encoding="utf-8")
    roh = json.loads(text)
    assert roh["version"] == 2
    assert len(roh.get("reservierungen", [])) == 1
    assert roh["reservierungen"][0]["auftrag"] == "auftrag-42"
    assert roh["reservierungen"][0]["menge"] == 4
