# AGENTS-HANDOFF.md — passing work to the next session

Agent sessions end without warning: a context limit, a timeout, a restart. The next session starts with the repo and nothing else. A handoff note is the letter you leave so it can carry on without redoing your work or undoing your decisions.

A good test: **could a new agent pick this up if the note were all it had?**

## Where handoff notes live

| Situation | Where the note goes |
|---|---|
| Work has a PR (the normal case) | The `## Handoff` section at the end of the PR description. Update it in place each time you stop. |
| Work is on a branch with no PR yet | Open the PR now and put the note there. A pushed branch with a PR is the safest place for unfinished work. |
| A long-lived experiment lineage | `docs/experiments/<name>.md` on the `experiment/<name>` branch, newest entry at the top. |

Don't create standalone handoff files on `main`; they go stale. The PR is the record, and git history keeps it.

Before you stop, **commit and push** whatever you have, even if unfinished, so the note points at real code.

## Template

Copy this into the PR description and fill every line. Write "none" rather than leaving a line out.

```markdown
## Handoff

**State:** one sentence on where things stand (e.g. "Law implemented and tested; ARCHITECTURE.md row still missing").
**Branch / PR:** `branch-name`, PR #N, based on `main` at <short sha>.
**Done:**
- what is finished and verified
**Next:**
1. the very next concrete step
2. the step after that
**Blockers / open questions:** anything waiting on the owner, CI, or another PR.
**Decisions made (and why):** choices the next session must not silently reverse.
**Ruled out:** approaches tried and dropped, with the reason.
**Verification run:**
- `python3 -m pytest -q` → N passed
- `bigbang eval --out evaluation.md` → ok / failed (which scenario)
- CI on the last push → green / red / pending
```

## Picking up someone else's work

1. Read the PR's handoff note, then `AGENTS.md`.
2. `git fetch origin` and check out the branch. Rebase on the latest `main` only if the branch is yours to rewrite; otherwise merge `main` in.
3. Re-run the verification commands yourself. Treat the note's claims as true when written, not as true now.
4. Carry on from **Next**. When you stop, update the same handoff section rather than adding a second one.
