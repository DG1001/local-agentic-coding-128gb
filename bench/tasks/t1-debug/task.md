Im Projekt kasse sind Fehler gemeldet worden. Die vorhandenen Tests laufen alle
durch, trotzdem stimmen die Zahlen nicht. Finde die Ursachen und behebe sie.

Es sind mehrere Fehler, nicht nur einer. Verlass dich nicht darauf, dass die
bestehende Testsuite gruen ist.

Aus den Meldungen der Anwender:

1. "Ich lasse mir den Monat Januar anzeigen, von 01.01. bis 31.01., und die
   Buchung vom 31. fehlt in der Liste."

2. "Wir haben eine Korrekturbuchung erfasst, aber der Saldo hat sich dadurch
   ueberhaupt nicht veraendert."

3. "Beim Runden auf Cent kommt manchmal ein Cent zu wenig heraus. Bei 2,675
   Euro erwarte ich 2,68, angezeigt wird 2,67."

4. "Ich teile 10,00 Euro auf drei Personen auf und bekomme dreimal 3,33 Euro.
   Das sind zusammen 9,99 Euro, ein Cent fehlt."

Regeln fuer die Behebung:

- Das oeffentliche Verhalten soll dem entsprechen, was die Docstrings
  beschreiben. Die Docstrings sind die Vorgabe, nicht der Code.
- Signaturen und Namen bleiben unveraendert.
- Bei aufteilen gilt: die Anteile duerfen sich um hoechstens einen Cent
  unterscheiden, ihre Summe muss exakt dem Ausgangsbetrag entsprechen, und die
  groesseren Anteile stehen vorn.
- Die bestehenden Tests muessen weiterhin gruen sein.
- Schreibe fuer jeden behobenen Fehler einen Test, der ihn kuenftig abfaengt.
- Pruefe zum Schluss selbst, dass "python -m pytest" durchlaeuft.
  Nutze dafuer den vorhandenen Interpreter .venv/bin/python.
