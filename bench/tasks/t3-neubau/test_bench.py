"""Verdeckte Bewertung t3-neubau."""

import pytest

from abfrage.fehler import AbfrageFehler, SpaltenFehler, SyntaxFehler
from abfrage.motor import fuehre_aus
from abfrage.tabelle import Tabelle

CSV = """name, alter, ort
Anna, 34, Frankfurt
Bert, 28, Bad Vilbel
Clara, 41, Frankfurt
Dora, 28, Hanau"""


def t():
    return Tabelle.aus_csv(CSV)


# --------------------------------------------------- Tabelle
def test_aus_csv_liest_kopf_und_zeilen():
    tab = t()
    assert tab.spalten == ["name", "alter", "ort"]
    assert len(tab.zeilen) == 4
    assert tab.zeilen[0] == {"name": "Anna", "alter": "34", "ort": "Frankfurt"}


def test_aus_csv_schneidet_leerraum_ab():
    tab = Tabelle.aus_csv("a ,  b\n 1 , 2 ")
    assert tab.spalten == ["a", "b"]
    assert tab.zeilen[0] == {"a": "1", "b": "2"}


def test_aus_csv_leere_eingabe():
    tab = Tabelle.aus_csv("")
    assert tab.spalten == []
    assert tab.zeilen == []


def test_als_csv_ist_umkehrbar():
    assert Tabelle.aus_csv(t().als_csv()) == t()


def test_als_csv_ohne_abschliessenden_umbruch():
    assert not t().als_csv().endswith("\n")


def test_gleichheit():
    assert t() == Tabelle.aus_csv(CSV)
    assert t() != Tabelle.aus_csv("name\nAnna")


# --------------------------------------------------- leer / unveraendert
def test_leere_abfrage_gibt_alles():
    assert fuehre_aus(t(), "") == t()


def test_quelle_bleibt_unveraendert():
    tab = t()
    fuehre_aus(tab, "wo alter > 30 grenze 1")
    assert tab == t()


# --------------------------------------------------- waehle
def test_waehle_spalten():
    e = fuehre_aus(t(), "waehle name, ort")
    assert e.spalten == ["name", "ort"]
    assert e.zeilen[0] == {"name": "Anna", "ort": "Frankfurt"}


def test_waehle_stern():
    assert fuehre_aus(t(), "waehle *") == t()


def test_waehle_unbekannte_spalte():
    with pytest.raises(SpaltenFehler):
        fuehre_aus(t(), "waehle gibtsnicht")


# --------------------------------------------------- wo
def test_wo_numerisch():
    e = fuehre_aus(t(), "wo alter > 30")
    assert [z["name"] for z in e.zeilen] == ["Anna", "Clara"]


def test_wo_gleich_zeichenkette():
    e = fuehre_aus(t(), "wo ort = Frankfurt")
    assert [z["name"] for z in e.zeilen] == ["Anna", "Clara"]


def test_wo_ungleich():
    e = fuehre_aus(t(), "wo ort != Frankfurt")
    assert [z["name"] for z in e.zeilen] == ["Bert", "Dora"]


def test_wo_kleiner_gleich():
    e = fuehre_aus(t(), "wo alter <= 28")
    assert [z["name"] for z in e.zeilen] == ["Bert", "Dora"]


def test_wo_wert_in_anfuehrungszeichen():
    e = fuehre_aus(t(), 'wo ort = "Bad Vilbel"')
    assert [z["name"] for z in e.zeilen] == ["Bert"]


def test_wo_unbekannte_spalte():
    with pytest.raises(SpaltenFehler):
        fuehre_aus(t(), "wo gibtsnicht = 1")


def test_wo_ohne_wert():
    with pytest.raises(SyntaxFehler):
        fuehre_aus(t(), "wo alter >")


# --------------------------------------------------- sortiere
def test_sortiere_numerisch():
    e = fuehre_aus(t(), "sortiere alter")
    assert [z["alter"] for z in e.zeilen] == ["28", "28", "34", "41"]


def test_sortiere_absteigend():
    e = fuehre_aus(t(), "sortiere alter ab")
    assert [z["alter"] for z in e.zeilen] == ["41", "34", "28", "28"]


def test_sortiere_alphabetisch():
    e = fuehre_aus(t(), "sortiere ort")
    assert [z["ort"] for z in e.zeilen][0] == "Bad Vilbel"


def test_sortieren_ist_stabil():
    e = fuehre_aus(t(), "sortiere alter")
    namen = [z["name"] for z in e.zeilen if z["alter"] == "28"]
    assert namen == ["Bert", "Dora"]


def test_sortiere_unbekannte_spalte():
    with pytest.raises(SpaltenFehler):
        fuehre_aus(t(), "sortiere gibtsnicht")


# --------------------------------------------------- grenze
def test_grenze():
    assert len(fuehre_aus(t(), "grenze 2").zeilen) == 2


def test_grenze_groesser_als_tabelle():
    assert len(fuehre_aus(t(), "grenze 99").zeilen) == 4


def test_grenze_keine_zahl():
    with pytest.raises(SyntaxFehler):
        fuehre_aus(t(), "grenze viele")


# --------------------------------------------------- Reihenfolge
def test_reihenfolge_filtern_sortieren_begrenzen_waehlen():
    e = fuehre_aus(t(), "waehle name, alter wo alter > 27 sortiere alter ab grenze 2")
    assert e.spalten == ["name", "alter"]
    assert [z["name"] for z in e.zeilen] == ["Clara", "Anna"]


def test_begrenzen_wirkt_nach_sortieren():
    e = fuehre_aus(t(), "sortiere alter grenze 1")
    assert e.zeilen[0]["alter"] == "28"


# --------------------------------------------------- zaehle
def test_zaehle_alles():
    e = fuehre_aus(t(), "zaehle")
    assert e.spalten == ["anzahl"]
    assert e.zeilen == [{"anzahl": "4"}]


def test_zaehle_nach_filter():
    e = fuehre_aus(t(), 'wo ort = "Bad Vilbel" zaehle')
    assert e.zeilen == [{"anzahl": "1"}]


def test_zaehle_nach_grenze():
    e = fuehre_aus(t(), "grenze 2 zaehle")
    assert e.zeilen == [{"anzahl": "2"}]


# --------------------------------------------------- Syntax
def test_unbekanntes_schluesselwort():
    with pytest.raises(SyntaxFehler):
        fuehre_aus(t(), "huepfe alter")


def test_fehlerklassen_haengen_zusammen():
    assert issubclass(SyntaxFehler, AbfrageFehler)
    assert issubclass(SpaltenFehler, AbfrageFehler)
