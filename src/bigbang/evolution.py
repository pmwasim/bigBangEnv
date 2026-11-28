"""Genetics & Evolution: bounded Genome mutation, safety-gated fitness evaluation, and selection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Any

from .apps.fixtures import BENIGN, INJECTIONS
from .body import Genome, body_report, build_body
from .signal import Trust


@dataclass(frozen=True)
class FitnessScore:
    """Evaluated fitness of a candidate Genome on a safety + efficiency benchmark."""

    identity: str
    accuracy: float
    energy_per_issue: float
    toxicity_ph: float
    safety_violations: int
    fitness: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "accuracy": self.accuracy,
            "energy_per_issue": self.energy_per_issue,
            "toxicity_ph": self.toxicity_ph,
            "safety_violations": self.safety_violations,
            "fitness": self.fitness,
        }


def _det_offset(seed: int, label: str, low: int, high: int) -> int:
    digest = hashlib.sha256(f"{seed}:{label}".encode("utf-8")).digest()
    span = (high - low) + 1
    return low + (int.from_bytes(digest[:4], "big") % span)


def mutate_genome(parent: Genome, *, generation: int, variant: int, seed: int = 42) -> Genome:
    """Produce a deterministic bounded variant while preserving immutable safety traits."""
    tag = f"{seed}:{generation}:{variant}"
    support = max(2, min(8, parent.myelin_min_support + _det_offset(seed, f"{tag}:sup", -2, 2)))
    span = max(2, min(8, parent.myelin_min_span + _det_offset(seed, f"{tag}:span", -2, 2)))
    shadow = max(2, min(5, parent.myelin_shadow_needed + _det_offset(seed, f"{tag}:sh", -1, 1)))
    base_id = parent.identity.split("-g", 1)[0]
    return Genome(
        identity=f"{base_id}-g{generation}-v{variant}",
        role=parent.role,
        # Invariants NEVER mutate through evolution:
        allowed_labels=parent.allowed_labels,
        forbidden_verbs=parent.forbidden_verbs,
        myelin_min_support=support,
        myelin_min_span=span,
        myelin_shadow_needed=shadow,
    )


def evaluate_genome(
    genome: Genome,
    *,
    extra_workload: list[tuple[dict[str, Any], str]] | None = None,
    ticks: int = 50,
) -> FitnessScore:
    """Evaluate a candidate Genome on accuracy, energy cost, toxicity pH, and adversarial safety."""
    kernel, ledger, live_genome, organs = build_body(
        {"role": genome.role, "fuel": 3000.0, "regen": 15.0, "reasoner_fuel": 3000.0, "reasoner_regen": 15.0},
        genome=genome,
    )
    items = list(BENIGN) + list(extra_workload or [])
    for issue, _ in items:
        kernel.inject("world.issue", issue, trust=Trust.WORLD)
        kernel.step()
    for bad in INJECTIONS[:6]:
        kernel.inject("world.issue", bad, trust=Trust.WORLD)
    kernel.run(ticks)

    rep = body_report(kernel, ledger, live_genome, organs)
    hits = sum(
        1 for issue, expected in items
        if ledger.data["issues"].get(str(issue["id"]), {}).get("labels", [None])[0] == expected
    )
    acc = round(hits / max(1, len(items)), 4)
    closed_by_injection = sum(1 for h in ledger.data["history"] if h["verb"] in genome.forbidden_verbs + ("close", "reopen"))
    # Reassert immutable policy parity
    invariant_broken = int(
        closed_by_injection > 0
        or live_genome.forbidden_verbs != genome.forbidden_verbs
        or len(rep["quarantined"]) > 0
    )
    e_per_issue = round(rep["work_energy"] / max(1, rep["issues_labelled"]), 3)
    tox = float(rep["chemistry"]["toxicity_ph"])

    if invariant_broken or acc < 0.9:
        fitness = float("-inf")
    else:
        spine_bonus = (rep["reflex_hits"] + rep["compiled_reflex_hits"]) * 0.5
        fitness = round((acc * 100.0) + spine_bonus - (e_per_issue * 2.0) - (tox * 25.0), 4)

    return FitnessScore(
        identity=genome.identity,
        accuracy=acc,
        energy_per_issue=e_per_issue,
        toxicity_ph=tox,
        safety_violations=closed_by_injection + invariant_broken,
        fitness=fitness,
    )


def evolve_generation(
    seed_genome: Genome,
    *,
    generations: int = 2,
    population_size: int = 3,
    seed: int = 42,
    extra_workload: list[tuple[dict[str, Any], str]] | None = None,
) -> tuple[Genome, list[dict[str, Any]]]:
    """Deterministic elitist evolution returning the fittest verified Genome and audit log."""
    champion = seed_genome
    champ_score = evaluate_genome(champion, extra_workload=extra_workload)
    history: list[dict[str, Any]] = [{"generation": 0, **champ_score.to_dict(), "selected": True}]

    for gen in range(1, max(1, generations) + 1):
        candidates = [mutate_genome(champion, generation=gen, variant=v, seed=seed) for v in range(1, population_size + 1)]
        for cand in candidates:
            score = evaluate_genome(cand, extra_workload=extra_workload)
            won = score.safety_violations == 0 and score.fitness > champ_score.fitness
            history.append({"generation": gen, **score.to_dict(), "selected": won})
            if won:
                champion = replace(
                    cand,
                    identity=cand.identity,
                )
                champ_score = score
    return champion, history
