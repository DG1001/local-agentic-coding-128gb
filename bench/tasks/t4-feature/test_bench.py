"""Verdeckte Bewertung t4-feature."""

import json

import pytest

from lager.artikel import UnbekannteReservierung, ZuWenigBestand
from lager.bestand import Lager
from lager.speicher import FORMAT_VERSION


@pytest.fixture
def lager(tmp_path):
    l = Lager(tmp_path / "lager.json")
    l.anlegen("A1", "Schraube", 100)
    return l


# --------------------------------------------------- reservieren
def test_reservieren_senkt_verfuegbar_nicht_bestand(lager):
    assert lager.reservieren("A1", 30, "auftrag-1") == 70
    assert lager.verfuegbar("A1") == 70
    assert lager.bestand("A1") == 100
    assert lager.reserviert("A1") == 30


def test_reservieren_addiert_bei_gleichem_auftrag(lager):
    lager.reservieren("A1", 10, "auftrag-1")
    lager.reservieren("A1", 15, "auftrag-1")
    assert lager.reservierungen("A1") == {"auftrag-1": 25}
    assert lager.verfuegbar("A1") == 75


def test_reservieren_mehrere_auftraege(lager):
    lager.reservieren("A1", 10, "a")
    lager.reservieren("A1", 20, "b")
    assert lager.reservierungen("A1") == {"a": 10, "b": 20}
    assert lager.reserviert("A1") == 30


def test_reservieren_ueber_verfuegbar(lager):
    lager.reservieren("A1", 90, "a")
    with pytest.raises(ZuWenigBestand):
        lager.reservieren("A1", 20, "b")


def test_reservieren_lehnt_null_ab(lager):
    with pytest.raises(ValueError):
        lager.reservieren("A1", 0, "a")


def test_reservierungen_sind_eine_kopie(lager):
    lager.reservieren("A1", 10, "a")
    d = lager.reservierungen("A1")
    d["a"] = 999
    d["b"] = 5
    assert lager.reservierungen("A1") == {"a": 10}


def test_ohne_reservierung_ist_verfuegbar_gleich_bestand(lager):
    assert lager.verfuegbar("A1") == lager.bestand("A1")
    assert lager.reserviert("A1") == 0
    assert lager.reservierungen("A1") == {}


# --------------------------------------------------- freigeben
def test_freigeben_gibt_frei_ohne_ware_zu_bewegen(lager):
    lager.reservieren("A1", 40, "a")
    assert lager.freigeben("A1", "a") == 100
    assert lager.bestand("A1") == 100
    assert lager.reserviert("A1") == 0


def test_freigeben_beruehrt_andere_auftraege_nicht(lager):
    lager.reservieren("A1", 10, "a")
    lager.reservieren("A1", 20, "b")
    lager.freigeben("A1", "a")
    assert lager.reservierungen("A1") == {"b": 20}


def test_freigeben_ohne_reservierung(lager):
    with pytest.raises(UnbekannteReservierung):
        lager.freigeben("A1", "gibtsnicht")


# --------------------------------------------------- entnehmen
def test_entnehmen_bucht_aus(lager):
    lager.reservieren("A1", 25, "a")
    assert lager.entnehmen("A1", "a") == 75
    assert lager.bestand("A1") == 75
    assert lager.reserviert("A1") == 0
    assert lager.verfuegbar("A1") == 75


def test_entnehmen_ohne_reservierung(lager):
    with pytest.raises(UnbekannteReservierung):
        lager.entnehmen("A1", "gibtsnicht")


def test_entnehmen_laesst_andere_stehen(lager):
    lager.reservieren("A1", 10, "a")
    lager.reservieren("A1", 20, "b")
    lager.entnehmen("A1", "a")
    assert lager.bestand("A1") == 90
    assert lager.reservierungen("A1") == {"b": 20}
    assert lager.verfuegbar("A1") == 70


# --------------------------------------------------- auslagern respektiert
def test_auslagern_greift_reservierte_ware_nicht_an(lager):
    lager.reservieren("A1", 95, "a")
    with pytest.raises(ZuWenigBestand):
        lager.auslagern("A1", 10)


def test_auslagern_bis_verfuegbar_geht(lager):
    lager.reservieren("A1", 95, "a")
    assert lager.auslagern("A1", 5).menge == 95
    assert lager.verfuegbar("A1") == 0


# --------------------------------------------------- Ablage
def test_reservierungen_ueberleben_neuladen(tmp_path):
    pfad = tmp_path / "lager.json"
    a = Lager(pfad)
    a.anlegen("A1", "Schraube", 100)
    a.reservieren("A1", 30, "auftrag-7")

    b = Lager(pfad)
    assert b.reservierungen("A1") == {"auftrag-7": 30}
    assert b.verfuegbar("A1") == 70
    assert b.bestand("A1") == 100


def test_format_version_ist_zwei():
    assert FORMAT_VERSION == 2


def test_alte_datei_version_1_laedt_weiter(tmp_path):
    pfad = tmp_path / "alt.json"
    pfad.write_text(
        json.dumps(
            {
                "version": 1,
                "artikel": [{"nummer": "A1", "name": "Schraube", "menge": 42}],
            }
        ),
        encoding="utf-8",
    )
    l = Lager(pfad)
    assert l.bestand("A1") == 42
    assert l.reserviert("A1") == 0
    assert l.verfuegbar("A1") == 42


def test_alte_datei_wird_beim_sichern_hochgezogen(tmp_path):
    pfad = tmp_path / "alt.json"
    pfad.write_text(
        json.dumps(
            {
                "version": 1,
                "artikel": [{"nummer": "A1", "name": "Schraube", "menge": 42}],
            }
        ),
        encoding="utf-8",
    )
    l = Lager(pfad)
    l.reservieren("A1", 2, "a")
    roh = json.loads(pfad.read_text(encoding="utf-8"))
    assert roh["version"] == 2


# --------------------------------------------------- CLI
def test_cli_liste_zeigt_fuenf_spalten(tmp_path, capsys):
    from lager.cli import main

    pfad = tmp_path / "l.json"
    main(["--datei", str(pfad), "anlegen", "A1", "Schraube", "--menge", "100"])
    main(["--datei", str(pfad), "reservieren", "A1", "30", "auftrag-1"])
    capsys.readouterr()
    main(["--datei", str(pfad), "liste"])
    zeile = capsys.readouterr().out.strip().split("\n")[0]
    assert zeile.split("\t") == ["A1", "Schraube", "100", "30", "70"]


def test_cli_freigeben_und_entnehmen(tmp_path, capsys):
    from lager.cli import main

    pfad = tmp_path / "l.json"
    main(["--datei", str(pfad), "anlegen", "A1", "Schraube", "--menge", "100"])
    main(["--datei", str(pfad), "reservieren", "A1", "30", "a"])
    assert main(["--datei", str(pfad), "freigeben", "A1", "a"]) == 0
    main(["--datei", str(pfad), "reservieren", "A1", "10", "b"])
    assert main(["--datei", str(pfad), "entnehmen", "A1", "b"]) == 0
    capsys.readouterr()
    main(["--datei", str(pfad), "liste"])
    zeile = capsys.readouterr().out.strip().split("\n")[0]
    assert zeile.split("\t") == ["A1", "Schraube", "90", "0", "90"]
