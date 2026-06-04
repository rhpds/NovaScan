#!/usr/bin/env python3
"""Stage 2: Scanner Detectors — framework, model, concurrency detection."""

import pytest
from pathlib import Path

from checksum.detectors import llm_imports, model_names, concurrency
from checksum.catalog import BUILTIN_CATALOG, MAAS_MODELS, lookup_models


# ─── Framework Detection ───


class TestFrameworkDetection:

    def test_detects_openai_import(self, tmp_path):
        f = tmp_path / "app.py"
        f.write_text("import openai\nclient = openai.OpenAI()")
        result = llm_imports.detect([f])
        assert "openai" in result

    def test_detects_transformers(self, tmp_path):
        f = tmp_path / "model.py"
        f.write_text("from transformers import AutoTokenizer")
        result = llm_imports.detect([f])
        assert "transformers" in result

    def test_detects_vllm(self, tmp_path):
        f = tmp_path / "serve.py"
        f.write_text("from vllm import LLM, SamplingParams")
        result = llm_imports.detect([f])
        assert "vllm" in result

    def test_ignores_non_llm_imports(self, tmp_path):
        f = tmp_path / "util.py"
        f.write_text("import os\nimport sys\nimport json")
        result = llm_imports.detect([f])
        assert result == []


# ─── Model Name Detection ───


class TestModelNameDetection:

    def test_detects_model_in_python(self, tmp_path):
        f = tmp_path / "config.py"
        f.write_text('MODEL = "granite-2b-cpu"')
        result = model_names.detect([f])
        names = [m["name"] for m in result]
        assert any("granite-2b-cpu" in n for n in names)

    def test_detects_model_in_yaml(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text('model: "deepseek-r1-distill-qwen-14b"')
        result = model_names.detect([f])
        names = [m["name"] for m in result]
        assert any("deepseek-r1-distill-qwen-14b" in n for n in names)

    def test_detects_huggingface_path(self, tmp_path):
        f = tmp_path / "model.py"
        f.write_text('model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"')
        result = model_names.detect([f])
        names = [m["name"] for m in result]
        assert any("TinyLlama" in n for n in names)


# ─── Concurrency Detection ───


class TestConcurrencyDetection:

    def test_detects_threadpool(self, tmp_path):
        f = tmp_path / "worker.py"
        f.write_text("from concurrent.futures import ThreadPoolExecutor\npool = ThreadPoolExecutor(max_workers=5)")
        result = concurrency.detect([f])
        assert result["max_concurrent"] >= 5
        assert "threadpool" in result["patterns"]

    def test_detects_batch_size(self, tmp_path):
        f = tmp_path / "trainer.py"
        f.write_text("batch_size = 32")
        result = concurrency.detect([f])
        assert "batch_size" in result["patterns"]


# ─── Catalog ───


class TestCatalog:

    def test_maas_models_count(self):
        assert len(MAAS_MODELS) >= 10

    def test_builtin_catalog_has_params(self):
        for name, info in BUILTIN_CATALOG.items():
            assert "params_b" in info, f"{name} missing params_b"
            assert "hardware" in info, f"{name} missing hardware"
            assert "memory_gb" in info, f"{name} missing memory_gb"

    def test_lookup_enriches_maas_model(self):
        raw = [{"name": "granite-2b-cpu", "files": ["test.py:1"]}]
        enriched = lookup_models(raw)
        assert len(enriched) == 1
        assert enriched[0]["source"] == "maas"
        assert enriched[0]["params_b"] == 2

    def test_lookup_unknown_model_guesses(self):
        raw = [{"name": "some-custom-7b-model", "files": ["test.py:1"]}]
        enriched = lookup_models(raw)
        assert len(enriched) == 1
        assert enriched[0]["params_b"] == 7
