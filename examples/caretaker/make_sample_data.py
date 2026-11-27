"""Write the evaluation fixtures out as sample issue files and an owner command file.

Run:  python examples/caretaker/make_sample_data.py
"""

import json
from pathlib import Path

from bigbang.apps.fixtures import BENIGN, INJECTIONS, OWNER_COMMANDS

here = Path(__file__).parent
issues_dir = here / "issues"
issues_dir.mkdir(exist_ok=True)
for n, issue in enumerate([i for i, _ in BENIGN] + INJECTIONS, start=1):
    (issues_dir / f"{n:04d}.json").write_text(json.dumps(issue, indent=2) + "\n")
(here / "commands.txt").write_text("\n".join(OWNER_COMMANDS) + "\n")
print(f"wrote {n} issues to {issues_dir} and {len(OWNER_COMMANDS)} commands")
