#!/usr/bin/env python3
"""Tests for MAAS rate limit warnings and lab capacity."""

from novascan.planner import recommend_tier, _check_warnings


class TestMaasWarnings:

    def test_warns_on_high_rpm(self):
        estimate = {"maas_rpm_estimate": 10, "gpu_count": 0}
        warnings = _check_warnings(estimate, seats=20)
        assert any("rate limit" in w.lower() for w in warnings)

    def test_no_warning_under_limit(self):
        estimate = {"maas_rpm_estimate": 5, "gpu_count": 0}
        warnings = _check_warnings(estimate, seats=5)
        assert not any("rate limit" in w.lower() for w in warnings)

    def test_warns_on_gpu_sharing(self):
        estimate = {"maas_rpm_estimate": 5, "gpu_count": 1}
        warnings = _check_warnings(estimate, seats=15)
        assert any("gpu sharing" in w.lower() for w in warnings)

    def test_no_gpu_warning_few_seats(self):
        estimate = {"maas_rpm_estimate": 5, "gpu_count": 1}
        warnings = _check_warnings(estimate, seats=5)
        assert not any("gpu sharing" in w.lower() for w in warnings)


class TestLabCapacity:

    def test_plan_includes_lab_for_multi_seat(self):
        results = {
            "repo": "/tmp/test",
            "files_scanned": 10,
            "frameworks_detected": ["openai"],
            "models_detected": [
                {"name": "granite-2b-cpu", "params_b": 2, "hardware": ["cpu"], "source": "maas"},
            ],
            "k8s_resources": {},
            "concurrency": {"max_concurrent": 1, "patterns": []},
            "infrastructure": {},
            "resource_estimate": {
                "cpu_cores": 8, "memory_gb": 16, "storage_gb": 20,
                "gpu_count": 0, "maas_rpm_estimate": 10, "local_inference": False,
            },
        }
        plan = recommend_tier(results, seats=30)
        assert "lab_capacity" in plan
        assert plan["lab_capacity"]["seats"] == 30
        assert plan["lab_capacity"]["total_cpu"] > 8

    def test_no_lab_for_single_seat(self):
        results = {
            "repo": "/tmp/test",
            "files_scanned": 1,
            "frameworks_detected": [],
            "models_detected": [],
            "k8s_resources": {},
            "concurrency": {"max_concurrent": 1, "patterns": []},
            "infrastructure": {},
            "resource_estimate": {
                "cpu_cores": 4, "memory_gb": 8, "storage_gb": 20,
                "gpu_count": 0, "maas_rpm_estimate": 10, "local_inference": False,
            },
        }
        plan = recommend_tier(results, seats=1)
        assert "lab_capacity" not in plan
