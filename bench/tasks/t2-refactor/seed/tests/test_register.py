from decimal import Decimal

from wandler.einheiten import Register
from wandler.einheiten import WandlerFehler, UnbekannteEinheit, UnpassendeBasis


def test_neues_register_ist_leer():
    """Ein frisch erzeugtes Register ist leer."""
    r = Register()
    assert r.einheiten() == []


def test_zwei_register_fully_unabhängig():
    """Zwei Register sind vollstandig unabhängig voneinander."""
    r1 = Register()
    r2 = Register()

    r1.registriere("km", "laenge", Decimal("1000"))
    r2.registriere("kg", "masse", Decimal("1"))

    # r1 darf kg nicht enthalten
    assert "kg" not in r1.einheiten()
    # r2 darf km nicht enthalten
    assert "km" not in r2.einheiten()

    # Werte in eigenen Register umrechnen (je eigene Einheiten mit Basis-Faktor 1)
    # Wir fügen die Basis-Einheit selbst mit faktor=1 hinzu
    r1.registriere("laenge", "laenge", Decimal("1"))
    r2.registriere("masse", "masse", Decimal("1"))

    # jetzt sollte wandle funktionieren
    assert r1.wandle(Decimal("1"), "km", "laenge") == Decimal("1000")
    assert r2.wandle(Decimal("1"), "kg", "masse") == Decimal("1")


def test_kopie_ist_unabhaengig():
    """kopie() liefert ein neues Register mit demselben Inhalt,
    das sich danach unabhaengig weiterentwickelt."""
    r = Register()
    r.registriere("km", "laenge", Decimal("1000"))

    kopie = r.kopie()

    # Korperselbiger Anfangsinhalt
    assert kopie.einheiten() == r.einheiten()

    # spaeterer Eintrag in der Kopie beeinflusst das Original nicht
    kopie.registriere("nm", "laenge", Decimal("0.000001"))

    assert "nm" not in r.einheiten()
    assert "nm" in kopie.einheiten()


def test_fehlerklassen_bleiben_erhalten():
    """Die bestehenden Fehlerklassen werden von Register-Methoden geworfen."""
    r = Register()

    # unbekannte Einheit
    try:
        r.wandle(1, "km", "gibtsnicht")
        assert False, "Exception erwarten"
    except UnbekannteEinheit:
        pass

    # unbekannte Einheit im wandle (m nicht registriert)
    r.registriere("km", "laenge", Decimal("1000"))
    try:
        r.wandle(1, "km", "m")
        assert False, "Exception erwarten (m nicht registriert)"
    except UnbekannteEinheit:
        pass

    # unpassende Basis
    r.registriere("kg", "masse", Decimal("1"))
    try:
        r.wandle(1, "km", "kg")
        assert False, "Exception erwarten"
    except UnpassendeBasis:
        pass


def test_standard_register_befuellt_ist():
    """STANDARD-Register enthält die mitgelieferten Einheiten."""
    from wandler import STANDARD

    namen = STANDARD.einheiten()
    assert "km" in namen
    assert "m" in namen
    assert "kg" in namen
    assert "g" in namen
    assert "s" in namen


def test_standard_funcs_arbeiten():
    """Vorhandene Modulfunktionen arbeiten auf STANDARD."""
    from wandler import wandle, registriere, einheiten

    # registriere/fuegt zum STANDARD hinzu
    registriere("meile", "laenge", "1609.344")
    assert "meile" in einheiten()

    # wandle arbeitet auf STANDARD
    assert wandle("1", "km", "m") == Decimal("1000")
