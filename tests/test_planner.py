"""Tests for the CheckSum capacity planner."""

from checksum.planner import recommend_tier


def test_empty_scan_recommends_pilot():
    results = {
        "repo": "/tmp/empty",
        "files_scanned": 0,
        "frameworks_detected": [],
        "models_detected": [],
        "k8s_resources": {},
        "concurrency": {"max_concurrent": 1, "patterns": []},
        "resource_estimate": {
            "cpu_cores": 4,
            "memory_gb": 8,
            "storage_gb": 20,
            "gpu_count": 0,
            "maas_rpm_estimate": 10,
            "local_inference": False,
        },
    }
    plan = recommend_tier(results)
    assert plan["recommended_tier"] == "pilot"


def test_maas_models_recommend_partner():
    results = {
        "repo": "/tmp/demo",
        "files_scanned": 10,
        "frameworks_detected": ["openai"],
        "models_detected": [
            {"name": "granite-2b-cpu", "params_b": 2, "hardware": ["cpu"], "source": "maas"},
        ],
        "k8s_resources": {"manifest_count": 3},
        "concurrency": {"max_concurrent": 5, "patterns": ["threadpool"]},
        "resource_estimate": {
            "cpu_cores": 12,
            "memory_gb": 24,
            "storage_gb": 50,
            "gpu_count": 0,
            "maas_rpm_estimate": 50,
            "local_inference": False,
        },
    }
    plan = recommend_tier(results)
    assert plan["recommended_tier"] == "partner"


def test_local_inference_recommends_dedicated():
    results = {
        "repo": "/tmp/demo",
        "files_scanned": 20,
        "frameworks_detected": ["vllm", "transformers"],
        "models_detected": [
            {"name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "params_b": 1.1, "hardware": ["cpu"], "source": "local"},
        ],
        "k8s_resources": {"manifest_count": 5},
        "concurrency": {"max_concurrent": 10, "patterns": ["threadpool", "asyncio_gather"]},
        "resource_estimate": {
            "cpu_cores": 24,
            "memory_gb": 48,
            "storage_gb": 80,
            "gpu_count": 0,
            "maas_rpm_estimate": 100,
            "local_inference": True,
        },
    }
    plan = recommend_tier(results)
    assert plan["recommended_tier"] == "dedicated"
    assert plan["agnosticv_overrides"].get("intel_rh_inference_local_cpu_backend") is True
