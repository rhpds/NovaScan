#!/usr/bin/env python3
"""K8s manifest parsing edge cases."""

from novascan.parsing import parse_cpu, parse_mem_gb


class TestParseCpu:
    def test_millicores(self):
        assert parse_cpu("500m") == 0.5

    def test_whole_cores(self):
        assert parse_cpu("2") == 2.0

    def test_fractional(self):
        assert parse_cpu("1.5") == 1.5

    def test_zero(self):
        assert parse_cpu("0") == 0.0


class TestParseQuantityGb:
    def test_gi(self):
        assert parse_mem_gb("16Gi") == 16.0

    def test_mi(self):
        assert abs(parse_mem_gb("512Mi") - 0.5) < 0.01

    def test_ti(self):
        assert parse_mem_gb("1Ti") == 1024.0

    def test_bare_number(self):
        assert parse_mem_gb("0") == 0.0

    def test_empty_string(self):
        assert parse_mem_gb("") == 0.0

    def test_g_unit(self):
        assert parse_mem_gb("2G") == 2.0
