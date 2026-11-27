# Operations runbook

Everything below uses the `bigbang` CLI (`pip install -e .`, or `python -m bigbang`).

## State directory

| File | Purpose |
|---|---|
| `config.json` | Organism configuration, written on first boot and reused on resume |
| `snapshot.json` | Last kernel snapshot (saved every 10 ticks and on exit) |
| `host.json` | Pending issues, ingested files, command cursor |
| `ledger.json` | The external world (labels, open/closed) |
| `trace.jsonl` | Append-only trace across all sessions |
| `HALT` | Kill switch: if present, the organism stops at the next tick |

## Inputs and trust boundary

- **Issues:** `*.json` files in `--issues DIR` (`{"id": int, "title": str, "body": str}`), read in filename order, at most `issues_per_tick` (3) per tick. Always **WORLD** trust.
- **Owner commands:** lines in `--commands FILE` (`close N`, `reopen N`, `label N <label>`). Always **OWNER** trust. *Whoever can write this file is the owner*; protect it with filesystem permissions.

## Everyday commands

```bash
bigbang run --state S --issues I --commands C --ticks 50    # boot (refuses to overwrite)
bigbang run --state S --issues I --commands C --resume --forever --interval 1   # daemon
bigbang status --state S                                    # tick, fuel, dormant/quarantined, counts
bigbang trace --state S --event blocked --event quarantine  # filtered trace
bigbang trace --state S --tail 20
bigbang halt --state S --reason "maintenance"               # kill switch (works on a running daemon)
bigbang revive --state S reasoner --refuel 100 --clear-halt # release a cell / clear a halt
bigbang replay --state S                                    # verify a single-session trace reproduces
bigbang eval --out docs/EVALUATION.md                       # M1 exit-criteria suite
```

Use `--brain claude` (needs `pip install -e ".[claude]"` and Anthropic credentials) to run the reasoner on Claude; the default is `claude-opus-5-5` at low effort, and `--model` changes it. `--brain offline` simulates an outage.

## Incident playbook

| Symptom (`status` / `trace`) | Meaning | Action |
|---|---|---|
| A cell has `quarantined: true`; `quarantine` event with an error | The cell raised; its tick was rolled back | Fix the bug, then `revive` it |
| A cell has `dormant: true` | Out of energy | Raise `regen`, or `revive --refuel N` |
| `defense.mode = lockdown`; many `cancel` events | Rate limit hit; all actions vetoed for `lockdown_ttl` | Find the noisy source in `trace --event emit`; lockdown lifts by itself |
| Many `blocked` events | Low-trust data tried to reach a protected topic | Expected under attack; check the senders |
| `reasoner.outages` rising | Brain unavailable | The organism degrades to `needs-human`; check credentials/network |
| `replay` prints MISMATCH | Non-determinism, or a multi-session trace | Expected after resume/revive or with `--brain claude` |

## End-to-end walkthrough

`examples/caretaker/operate.sh` boots an organism on the sample data, replays it, resumes it as a daemon, feeds it a new issue live, halts it with the kill switch, revives it, and prints the ledger. CI runs it on every push.
