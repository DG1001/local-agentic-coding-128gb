Das Projekt wandler haelt alle Einheiten in einem modulweiten Verzeichnis.
Das faellt uns auf die Fuesse: zwei Programmteile koennen keine eigenen
Einheitensaetze verwenden, ohne sich gegenseitig zu stoeren, und Tests muessen
leeren() aufrufen, um sich nicht zu beeinflussen.

Bau das auf ein Register-Objekt um. Die Namen und Signaturen unten sind
verbindlich, es gibt eine externe Testsuite.

NEUE SCHNITTSTELLE in wandler/einheiten.py:

    class Register:
        def __init__(self) -> None: ...
        def registriere(self, name: str, basis: str,
                        faktor: Decimal | str | int) -> None: ...
        def wandle(self, wert: Decimal | str | int,
                   von: str, nach: str) -> Decimal: ...
        def einheiten(self) -> list[str]: ...
        def kopie(self) -> "Register": ...

- Ein frisch erzeugtes Register() ist leer.
- Zwei Register sind vollstaendig unabhaengig voneinander. Was im einen
  eingetragen wird, darf im anderen nicht auftauchen.
- kopie() liefert ein neues Register mit demselben Inhalt, das sich danach
  unabhaengig weiterentwickelt.
- Die Fehlerklassen WandlerFehler, UnbekannteEinheit und UnpassendeBasis
  bleiben wie sie sind und werden weiterhin von den Methoden geworfen.

STANDARD-REGISTER:

    wandler.einheiten.STANDARD

ist ein Register, in dem die mitgelieferten Einheiten aus wandler/basis.py
bereits eingetragen sind.

RUECKWAERTSKOMPATIBILITAET:

Die bisherigen Modulfunktionen wandler.registriere, wandler.wandle und
wandler.einheiten bleiben erhalten und arbeiten auf STANDARD weiter. Bestehender
Code, der sie benutzt, muss unveraendert weiterlaufen. Die bestehenden Tests
sind dafuer der Massstab und muessen gruen bleiben.

WEITER:

- leeren() faellt ersatzlos weg. Wer Isolation braucht, nimmt ein eigenes
  Register.
- basis.eintragen bekommt das Register, in das eingetragen werden soll, als
  Parameter:  def eintragen(register: Register) -> None
- Die CLI arbeitet weiterhin auf STANDARD.
- Passe die README an.
- Schreibe eigene Tests fuer die neue Schnittstelle, insbesondere fuer die
  Unabhaengigkeit zweier Register.
- Pruefe zum Schluss selbst, dass "python -m pytest" durchlaeuft.
  Nutze dafuer den vorhandenen Interpreter .venv/bin/python.
