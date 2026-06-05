#!/usr/bin/env python3
"""K8s manifest parsing edge cases."""

from novascan.detectors.k8s_manifests import _parse_cpu, _parse_quantity_gb


class TestParseCpu:
    def test_millicores(self):
        assert _parse_cpu("500m") == 0.5

    def test_whole_cores(self):
        assert _parse_cpu("2") == 2.0

    def test_fractional(self):
        assert _parse_cpu("1.5") == 1.5

    def test_zero(self):
        assert _parse_cpu("0") == 0.0


class TestParseQuantityGb:
    def test_gi(self):
        assert _parse_quantity_gb("16Gi") == 16.0

    def test_mi(self):
        assert abs(_parse_quantity_gb("512Mi") - 0.5) < 0.01

    def test_ti(self):
        assert _parse_quantity_gb("1Ti") == 1024.0

    def test_bare_number(self):
        assert _parse_quantity_gb("0") == 0.0

    def test_empty_string(self):
        assert _parse_quantity_gb("") == 0.0

    def test_g_unit(self):
        assert _parse_quantity_gb("2G") == 2.0
