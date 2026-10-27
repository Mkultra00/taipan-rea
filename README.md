# TAIPAN! 1982 — deterministic web port

Real TAIPAN! engine (taipan.py, by Art Canfil / Jay Link lineage) running UNSMODIFIED
in the browser via vendored Pyodide v0.26.4 + native `window.prompt()` as synchronous
stdin. Zero inference calls, zero LLM, zero API keys, zero CDN calls — everything is
vendored into `web/pyodide/`.

## Run

```
cd web && python3 -m http.server 8600
open http://localhost:8600
```

## Determinism

- Engine: unmodified `taipan.py` (patches 1–3 + BATTLE_WON fix preserved)
- RNG: `random.randint` / `random.random` / `random.choice` only
- IO: synchronous `window.prompt()` ↔ `sys.stdin.readline()` (modal dance)
- Runtime: vendored Pyodide 0.26.4 (no network calls at runtime)

## Structure

```
web/
├── index.html      # Pyodide boot + prompt-fed stdin shim
├── taipan.py       # The engine, byte-identical to reference
└── pyodide/        # Pyodide v0.26.4 vendored runtime
```