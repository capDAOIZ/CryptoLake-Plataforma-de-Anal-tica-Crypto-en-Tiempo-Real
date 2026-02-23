"""Tests unitarios para el modulo de quality."""

import pytest

pyspark = pytest.importorskip("pyspark")

from src.quality.validators import CheckResult, CheckStatus


def test_check_result_to_dict():
    """CheckResult se serializa correctamente."""
    result = CheckResult(
        check_name="test_check",
        layer="bronze",
        table_name="test_table",
        status=CheckStatus.PASSED,
        metric_value=100.0,
        threshold=50.0,
        message="All good",
    )
    payload = result.to_dict()
    assert payload["status"] == "passed"
    assert payload["metric_value"] == 100.0
    assert "checked_at" in payload


def test_check_status_values():
    """CheckStatus tiene los valores esperados."""
    assert CheckStatus.PASSED.value == "passed"
    assert CheckStatus.FAILED.value == "failed"
    assert CheckStatus.WARNING.value == "warning"
    assert CheckStatus.ERROR.value == "error"
