"""Record a local model's answers for every evaluation issue, for free replay.

Every question is asked exactly as the reasoner would ask it, so the
`local_model_*` evaluation scenarios can replay the answers in CI without
the model file. Re-running only asks questions not yet recorded.

Run:  python scripts/record_answers.py [--model qwen2.5-1.5b]
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from bigbang.apps.caretaker import LABELS, MAX_BODY, MAX_TITLE
from bigbang.brains import CachedBrain, LocalBrain
from bigbang.evaluation import ANSWERS_PATH, evaluation_issues

# Makes the calls do nothing where claude-progress is not installed.
_bytecode, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # no __pycache__ in the plugin
try:
    sys.path.insert(0, os.environ["CLAUDE_PROGRESS_DIR"]); from claude_progress import claude_progress  # noqa: E702
except Exception:
    def claude_progress(*args): pass
finally:
    sys.dont_write_bytecode = _bytecode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5-1.5b")
    args = parser.parse_args()

    brain = CachedBrain(LocalBrain(args.model), ANSWERS_PATH)
    issues = evaluation_issues()
    start = time.time()
    for n, issue in enumerate(issues, start=1):
        brain.classify(issue["title"][:MAX_TITLE], issue.get("body", "")[:MAX_BODY], LABELS)
        claude_progress("-n", "record-answers", f"{n}/{len(issues)}")
    claude_progress("-n", "record-answers", "done")
    print(f"{len(issues)} issues, {brain.misses} newly recorded, {brain.hits} already cached, "
          f"{time.time() - start:.0f}s -> {ANSWERS_PATH}")


if __name__ == "__main__":
    main()
