#!/usr/bin/env python3
"""Throughput for one loaded model, by the method recorded in throughput.json.

    python3 tools/throughput.py <served-model-name> [base-url]

Two numbers, because they answer different questions:

  generation    short prompt, 800 output tokens, temperature 0, mean of two
                runs. What decoding costs once the model is warm.
  end_to_end    ~16,850 input tokens, 800 output, one run, measured as
                completion_tokens / total wall time. Prefill included, which
                is what a real turn actually pays.

Three details that are not optional:

  warm-up       two short requests, discarded. Without them the first
                measurement pays CUDA graph capture and JIT — Nemotron read
                62.8 instead of 78.7 tok/s, a 20 % error.
  prefix cache  the long prompt carries a fixed-width prefix naming the model,
                so a previous model's identical body cannot produce a cache
                hit. Fixed width, because a longer name would otherwise change
                the input length and with it the number being compared.
  filler        the body is tuned once to ~16,850 input tokens and then reused
                character-identically. It was written this way after an early
                mistake: the filler contained the model name 1,200 times, so
                every model got a different input length.
"""
import json
import sys
import time
import urllib.request

ZIEL_EINGABE = 16_850
AUSGABE = 800
BREITE = 24                     # feste Breite des Modellpraefixes

SATZ = ("Ein Absatz ohne Bedeutung, der nur Laenge erzeugt und fuer jedes "
        "Modell Zeichen fuer Zeichen derselbe ist. ")

# Ohne diesen Auftrag am Ende antwortet ein Modell auf Fuelltext mit zwei
# Saetzen. Der Wert misst dann fast nur den Prefill und faellt umso
# schlechter aus, je knapper das Modell antwortet -- Ornith kam so auf 116
# Ausgabetoken und 29,4 tok/s, obwohl sein Prefill mit rund 6.000 Token/s
# zu den schnellsten hier gehoert. Verglichen werden soll die Maschine,
# nicht die Redseligkeit.
AUFTRAG = ("\n\nSchreibe jetzt einen langen, zusammenhaengenden Fachtext ueber "
           "Zahnraeder: Bauformen, Werkstoffe, Fertigung, Verschleiss. "
           "Mindestens 900 Woerter, keine Aufzaehlungen.")


def frage(url, modell, inhalt, max_tokens):
    daten = json.dumps({
        'model': modell, 'temperature': 0, 'max_tokens': max_tokens,
        'messages': [{'role': 'user', 'content': inhalt}]}).encode()
    r = urllib.request.Request(url + '/chat/completions', daten,
                               {'Content-Type': 'application/json'})
    t0 = time.time()
    with urllib.request.urlopen(r, timeout=1800) as a:
        d = json.load(a)
    return d['usage'], time.time() - t0


def fuellung(url, modell, praefix):
    """So viele Saetze, dass die Eingabe bei ZIEL_EINGABE landet."""
    n = ZIEL_EINGABE // 20
    for _ in range(12):
        u, _ = frage(url, modell, praefix + SATZ * n + AUFTRAG, 1)
        ist = u['prompt_tokens']
        print(f'    Kalibrierung: {n} Saetze -> {ist} Token', flush=True)
        if abs(ist - ZIEL_EINGABE) <= 15:
            return SATZ * n, ist
        n = max(1, round(n * ZIEL_EINGABE / ist))
    return SATZ * n, ist


def main():
    modell = sys.argv[1]
    url = (sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8889') + '/v1'
    praefix = f'[{modell}]'.ljust(BREITE)[:BREITE] + '\n'

    print('  Aufwaermen (zwei Anfragen, verworfen) ...', flush=True)
    for _ in range(2):
        frage(url, modell, 'Sag hallo.', 16)

    werte = []
    for i in (1, 2):
        u, s = frage(url, modell, 'Schreibe einen laengeren Absatz ueber '
                                  'Zahnraeder.', AUSGABE)
        werte.append(u['completion_tokens'] / s)
        print(f'    Lauf {i}: {werte[-1]:5.1f} tok/s '
              f'({u["completion_tokens"]} Token in {s:.1f} s)', flush=True)
    generation = sum(werte) / len(werte)

    print('  Langer Prompt ...', flush=True)
    koerper, eingabe = fuellung(url, modell, praefix)
    u, s = frage(url, modell, praefix + koerper + AUFTRAG, AUSGABE)
    ende = u['completion_tokens'] / s

    print(f'    Ausgabe: {u["completion_tokens"]} Token in {s:.1f} s')
    print(f'\n  generation_tok_s      {generation:5.1f}')
    print(f'  end_to_end_tok_s      {ende:5.1f}')
    print(f'  end_to_end_input      {u["prompt_tokens"]}')
    print(json.dumps({'generation_tok_s': round(generation, 1),
                      'end_to_end_tok_s': round(ende, 1),
                      'end_to_end_input_tokens': u['prompt_tokens']}))


if __name__ == '__main__':
    main()
