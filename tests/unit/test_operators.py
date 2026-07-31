"""Unit tests for the comparison operators used in policy conditions."""

import pytest

from app.core.operators import compare


@pytest.mark.unit
class TestNumericOperators:
    @pytest.mark.parametrize(
        "operator,rule_value,matching_value,non_matching_value",
        [
            (">", 100, 101, 100),
            ("<", 100, 99, 100),
            (">=", 100, 100, 99),
            ("<=", 100, 100, 101),
            ("==", 5, 5, 6),
            ("!=", 5, 6, 5),
        ],
    )
    def test_numeric_comparisons(self, operator, rule_value, matching_value, non_matching_value):
        assert compare(matching_value, operator, rule_value) is True
        assert compare(non_matching_value, operator, rule_value) is False

    def test_string_rule_value_is_coerced_to_number(self):
        assert compare(120, ">", "100") is True
        assert compare(80, ">", "100") is False

    def test_uncoercible_string_rule_value_raises_type_error(self):
        with pytest.raises(TypeError):
            compare(10, ">", "not-a-number")


@pytest.mark.unit
class TestStringOperators:
    def test_contains(self):
        assert compare("documents/confidential.pdf", "contains", "confidential") is True
        assert compare("documents/public.pdf", "contains", "confidential") is False

    def test_contains_coerces_to_string(self):
        assert compare(12345, "contains", "23") is True

    def test_startswith(self):
        assert compare("https://example.com", "startswith", "https") is True
        assert compare("http://example.com", "startswith", "https") is False

    def test_endswith(self):
        assert compare("file.tar.gz", "endswith", ".gz") is True
        assert compare("file.tar.bz2", "endswith", ".gz") is False


@pytest.mark.unit
class TestInvalidOperator:
    def test_unsupported_operator_raises(self):
        with pytest.raises(ValueError, match="Unsupported operator"):
            compare(1, "regex_matches", 1)

    def test_none_operator_raises(self):
        with pytest.raises(ValueError):
            compare(1, None, 1)


@pytest.mark.unit
class TestMixedTypes:
    def test_bool_equality(self):
        assert compare(True, "==", True) is True
        assert compare(True, "==", False) is False

    def test_int_vs_bool_comparison_does_not_crash(self):
        # Python allows bool/int comparisons; ensure no exception
        compare(1, ">=", False)
