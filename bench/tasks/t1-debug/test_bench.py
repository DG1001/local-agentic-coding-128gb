"""Verdeckte Bewertung t1-debug."""

from datetime import date
from decimal import Decimal

import pytest

from kasse.buch import Eintrag, aufteilen, im_zeitraum, runde_cent, saldo


# --------------------------------------------------- Fehler 1: Zeitraum
def test_zeitraum_schliesst_enddatum_ein():
    e = [Eintrag(date(2026, 1, 31), "einnahme", Decimal("5.00"))]
    assert im_zeitraum(e, date(2026, 1, 1), date(2026, 1, 31)) == e


def test_zeitraum_schliesst_startdatum_ein():
    e = [Eintrag(date(2026, 1, 1), "einnahme", Decimal("5.00"))]
    assert im_zeitraum(e, date(2026, 1, 1), date(2026, 1, 31)) == e


def test_zeitraum_laesst_aussen_vor_weg():
    e = [
        Eintrag(date(2025, 12, 31), "einnahme", Decimal("5.00")),
        Eintrag(date(2026, 2, 1), "einnahme", Decimal("5.00")),
    ]
    assert im_zeitraum(e, date(2026, 1, 1), date(2026, 1, 31)) == []


# --------------------------------------------------- Fehler 2: Korrektur
def test_korrektur_zaehlt_positiv():
    e = [Eintrag(date(2026, 1, 1), "korrektur", Decimal("7.50"))]
    assert saldo(e) == Decimal("7.50")


def test_saldo_mit_allen_arten():
    e = [
        Eintrag(date(2026, 1, 1), "einnahme", Decimal("100.00")),
        Eintrag(date(2026, 1, 2), "ausgabe", Decimal("30.00")),
        Eintrag(date(2026, 1, 3), "korrektur", Decimal("5.25")),
    ]
    assert saldo(e) == Decimal("75.25")


# --------------------------------------------------- Fehler 3: Rundung
def test_rundet_halbe_auf():
    assert runde_cent(Decimal("2.675")) == Decimal("2.68")


def test_rundet_weitere_halbe_auf():
    assert runde_cent(Decimal("0.125")) == Decimal("0.13")
    assert runde_cent(Decimal("1.005")) == Decimal("1.01")


def test_rundet_normal_weiterhin_richtig():
    assert runde_cent(Decimal("1.234")) == Decimal("1.23")
    assert runde_cent(Decimal("1.236")) == Decimal("1.24")


# --------------------------------------------------- Fehler 4: Aufteilen
def test_aufteilen_summe_stimmt():
    teile = aufteilen(Decimal("10.00"), 3)
    assert sum(teile) == Decimal("10.00")
    assert len(teile) == 3


def test_aufteilen_hoechstens_ein_cent_unterschied():
    teile = aufteilen(Decimal("10.00"), 3)
    assert max(teile) - min(teile) <= Decimal("0.01")


def test_aufteilen_groessere_zuerst():
    assert aufteilen(Decimal("10.00"), 3) == [
        Decimal("3.34"),
        Decimal("3.33"),
        Decimal("3.33"),
    ]


def test_aufteilen_glatt_bleibt_glatt():
    assert aufteilen(Decimal("9.00"), 3) == [Decimal("3.00")] * 3


def test_aufteilen_ein_anteil():
    assert aufteilen(Decimal("7.77"), 1) == [Decimal("7.77")]


def test_aufteilen_lehnt_null_ab():
    with pytest.raises(ValueError):
        aufteilen(Decimal("1.00"), 0)


# --------------------------------------------------- Regression
def test_bestehende_zusicherungen_gelten_weiter():
    with pytest.raises(ValueError):
        Eintrag(date(2026, 1, 1), "quatsch", Decimal("1.00"))
    with pytest.raises(ValueError):
        Eintrag(date(2026, 1, 1), "einnahme", Decimal("-1.00"))
