# wandler

Rechnet Werte zwischen Einheiten um.

## Standard-Register

Es gibt ein modulweites Standard-Register, das beim Import automatisch befüllt wird:

```python
import wandler
# STANDARD enthält die mitgelieferten Einheiten (km, m, kg, g, s, min, h, d, etc.)
wandler.wandle("1", "km", "m")  # gibt 1000 aus
wandler.einheiten()  # gibt sortierte Liste aller registrierten Einheiten aus
```

Das Standard-Register ist unter `wandler.STANDARD` erreichbar.

## Eigenes Register erstellen

Um Isolation zwischen verschiedenen Teilsystemen zu garantieren, kann ein eigenes `Register`-Objekt erstellt werden:

```python
from wandler.einheiten import Register

r = Register()  # leer
r.registriere("km", "laenge", "1000")
r.wandle(1, "km", "m")  # umrechnet im eigenen Kontext
```

Zwei Register sind vollständig unabhängig. Was im einen eingetragen wurde, taucht im anderen nicht auf.

## Kopie eines Registers

Ein Register kann kopiert werden:

```python
kopie = r.kopie()  # neues Register mit gleichem Inhalt
kopie.registriere("neu", "basis", "wert")  # Änderung der Kopie wirkt sich nicht auf das Original aus
```

## Einheiten hinzufügen (neue Signatur)

Die Funktion `basis.eintragen` erwartet nun ein Register als Parameter:

```python
from wandler.basis import eintragen
from wandler.einheiten import Register

reg = Register()
eintragen(reg)  # füllt das Register mit den mitgelieferten Einheiten
```

## Zurückfallende Kompatibilität

Die bisherige Nutzung von `wandler.registriere`, `wandler.wandle` und `wandler.einheiten` funktioniert weiterhin auf dem `STANDARD`-Register und ist unverändert nutzbar.

## Kommandozeile

Die CLI arbeitet weiterhin auf `STANDARD`.

    python -m wandler.cli 1 km m
    python -m wandler.cli --liste

## Tests

    python -m pytest
