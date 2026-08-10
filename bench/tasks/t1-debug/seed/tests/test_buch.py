from datetime import date
from decimal import Decimal

import pytest

from kasse.buch import Eintrag, aufteilen, im_zeitraum, runde_cent, saldo


def test_eintrag_prueft_art():
    with pytest.raises(ValueError):
        Eintrag(date(2026, 1, 1), "quatsch", Decimal("1.00"))


def test_saldo_einnahme_minus_ausgabe():
    e = [
        Eintrag(date(2026, 1, 1), "einnahme", Decimal("100.00")),
        Eintrag(date(2026, 1, 2), "ausgabe", Decimal("40.00")),
    ]
    assert saldo(e) == Decimal("60.00")


def test_zeitraum_filtert():
    e = [
        Eintrag(date(2026, 1, 1), "einnahme", Decimal("1.00")),
        Eintrag(date(2026, 2, 1), "einnahme", Decimal("1.00")),
    ]
    assert len(im_zeitraum(e, date(2026, 1, 1), date(2026, 1, 15))) == 1


def test_runde_cent():
    assert runde_cent(Decimal("1.234")) == Decimal("1.23")


def test_aufteilen_gleiche_teile():
    assert aufteilen(Decimal("9.00"), 3) == [Decimal("3.00")] * 3
