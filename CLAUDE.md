# bigBangEnv — notes for coding agents

- Read `docs/VISION.md` (principles P1–P5) and `docs/ROADMAP.md` before changing anything. Don't build a milestone before the previous one meets its exit criteria.
- Kernel laws live in `src/bigbang/kernel.py`. Never let a cell construct a `Signal`, raise its own trust, or reach the kernel except through `Context`.
- Every new kernel law needs a test in `tests/` and a row in `docs/ARCHITECTURE.md`.
- Hard-to-reverse design choices get an ADR in `docs/decisions/` (next number, same format).
- Biological terms must map to the glossary in `docs/VISION.md`; add the engineering definition first.
- Run `python3 -m pytest -q` before committing.
