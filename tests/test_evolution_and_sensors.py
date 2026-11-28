"""Tests for ADR-0017: Genome evolution and live POSIX/Linux domain sensors."""

import json

from bigbang.apps.caretaker import Host
from bigbang.apps.sensors import collect_host_snapshot, emit_probe_files, snapshot_to_signals
from bigbang.body import Genome, build_body
from bigbang.evolution import evaluate_genome, evolve_generation, mutate_genome


def test_genome_mutation_preserves_safety_invariants():
    base = Genome(identity="body-evo", role="triage", forbidden_verbs=("delete", "drop"))
    for v in range(1, 6):
        child = mutate_genome(base, generation=1, variant=v, seed=99)
        assert child.forbidden_verbs == base.forbidden_verbs
        assert child.allowed_labels == base.allowed_labels
        assert 2 <= child.myelin_min_support <= 8
        assert 2 <= child.myelin_min_span <= 8
        assert 2 <= child.myelin_shadow_needed <= 5


def test_evolution_selects_valid_fittest_genome_with_zero_violations():
    seed_genome = Genome(identity="body-evo", role="triage", myelin_min_support=7, myelin_min_span=7)
    extra = [
        ({"id": 200 + i, "title": f"Database timeout shard {i}", "body": f"crash code {i * 19}"}, "bug")
        for i in range(1, 9)
    ]
    champ, history = evolve_generation(seed_genome, generations=2, population_size=3, seed=7, extra_workload=extra)
    assert champ.forbidden_verbs == seed_genome.forbidden_verbs
    champ_score = evaluate_genome(champ, extra_workload=extra)
    assert champ_score.safety_violations == 0
    assert champ_score.accuracy >= 0.9
    assert len(history) == 1 + (2 * 3)


def test_domain_sensors_convert_anomalies_into_reagents_and_issues(tmp_path):
    snap = collect_host_snapshot()
    assert snap["disk_used_pct"] >= 0.0
    assert snap["cpu_count"] >= 1

    # Simulated stressed host triggers paired Chemistry symptom + context reagents + load issue
    stressed = {
        "host": "vm-300",
        "cpu_count": 4,
        "load_1m": 8.5,
        "load_ratio": 2.125,
        "disk_used_pct": 91.5,
        "mem_used_pct": 92.0,
        "uptime_s": 1200.0,
    }
    sigs = snapshot_to_signals(stressed, seq=1)
    assert any(s.get("topic") == "world.reagent" for s in sigs)
    assert any("high load" in s.get("title", "").lower() or "high cpu" in s.get("title", "").lower() for s in sigs)

    written = emit_probe_files(tmp_path / "issues", seq=1, snapshot=stressed)
    assert len(written) == len(sigs)

    # Feed emitted probe files through Host into a real 5-organ Body
    k, ledger, genome, organs = build_body({"role": "sentinel"})
    host = Host(issues_dir=tmp_path / "issues", issues_per_tick=10)
    for _ in range(10):
        host.poll(k)
        k.step()
    assert len(ledger.data["issues"]) >= 3
    for rec in ledger.data["issues"].values():
        assert rec["labels"] == ["bug"]
