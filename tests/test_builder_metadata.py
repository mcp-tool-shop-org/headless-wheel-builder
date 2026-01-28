"""Tests for wheel metadata extraction."""

import pytest

from headless_wheel_builder.core.builder_metadata import (
    extract_wheel_metadata,
    parse_wheel_filename,
    validate_wheel_filename,
    get_wheel_compatibility,
    is_universal_wheel,
    is_manylinux_wheel,
)


class TestParseWheelFilename:
    """Test wheel filename parsing."""

    def test_parse_standard_wheel(self):
        """Test parsing standard wheel filename."""
        result = parse_wheel_filename("package-1.0-py3-none-any.whl")
        assert result["name"] == "package"
        assert result["version"] == "1.0"
        assert result["python_tag"] == "py3"
        assert result["abi_tag"] == "none"
        assert result["platform_tag"] == "any"

    def test_parse_wheel_with_underscores(self):
        """Test parsing wheel with underscores in name."""
        result = parse_wheel_filename("my_package-2.0-py3-none-any.whl")
        assert result["name"] == "my-package"  # Underscores converted to hyphens
        assert result["version"] == "2.0"

    def test_parse_manylinux_wheel(self):
        """Test parsing manylinux wheel."""
        result = parse_wheel_filename(
            "package-1.0-cp310-cp310-manylinux_2_28_x86_64.whl"
        )
        assert result["name"] == "package"
        assert result["python_tag"] == "cp310"
        assert result["abi_tag"] == "cp310"
        assert result["platform_tag"] == "manylinux_2_28_x86_64"

    def test_parse_wheel_with_build_tag(self):
        """Test parsing wheel with build tag."""
        result = parse_wheel_filename("package-1.0-1-py3-none-any.whl")
        assert result["name"] == "package"
        assert result["version"] == "1.0"
        assert result["python_tag"] == "py3"

    def test_parse_invalid_wheel_filename(self):
        """Test that invalid filename raises error."""
        with pytest.raises(ValueError, match="Invalid wheel filename"):
            parse_wheel_filename("invalid-filename.whl")

    def test_parse_non_wheel_file(self):
        """Test that non-wheel raises error."""
        with pytest.raises(ValueError):
            parse_wheel_filename("package-1.0.tar.gz")


class TestValidateWheelFilename:
    """Test wheel filename validation."""

    def test_validate_valid_wheel(self):
        """Test that valid wheel passes validation."""
        assert validate_wheel_filename("package-1.0-py3-none-any.whl")

    def test_validate_manylinux_wheel(self):
        """Test that manylinux wheel passes validation."""
        assert validate_wheel_filename("package-1.0-cp310-cp310-manylinux_2_28_x86_64.whl")

    def test_validate_missing_extension(self):
        """Test that missing .whl extension fails."""
        assert not validate_wheel_filename("package-1.0-py3-none-any")

    def test_validate_wrong_extension(self):
        """Test that wrong extension fails."""
        assert not validate_wheel_filename("package-1.0-py3-none-any.tar.gz")

    def test_validate_incomplete_filename(self):
        """Test that incomplete filename fails."""
        assert not validate_wheel_filename("package-1.0.whl")


class TestGetWheelCompatibility:
    """Test compatibility information extraction."""

    def test_get_compatibility_standard_wheel(self):
        """Test getting compatibility for standard wheel."""
        compat = get_wheel_compatibility("package-1.0-py3-none-any.whl")
        assert compat["python_version"] == "py3"
        assert compat["abi"] == "none"
        assert compat["platform"] == "any"

    def test_get_compatibility_manylinux_wheel(self):
        """Test getting compatibility for manylinux wheel."""
        compat = get_wheel_compatibility("package-1.0-cp310-cp310-manylinux_2_28_x86_64.whl")
        assert compat["python_version"] == "cp310"
        assert compat["abi"] == "cp310"
        assert compat["platform"] == "manylinux_2_28_x86_64"


class TestIsUniversalWheel:
    """Test universal wheel detection."""

    def test_detect_universal_wheel_py3(self):
        """Test detection of py3-none-any wheel."""
        assert is_universal_wheel("package-1.0-py3-none-any.whl")

    def test_detect_universal_wheel_py2_py3(self):
        """Test detection of py2.py3-none-any wheel."""
        assert is_universal_wheel("package-1.0-py2.py3-none-any.whl")

    def test_non_universal_manylinux(self):
        """Test that manylinux wheel is not universal."""
        assert not is_universal_wheel("package-1.0-cp310-cp310-manylinux_2_28_x86_64.whl")

    def test_non_universal_with_abi(self):
        """Test that wheel with ABI is not universal."""
        assert not is_universal_wheel("package-1.0-cp310-cp310-linux_x86_64.whl")

    def test_invalid_wheel_filename(self):
        """Test that invalid filename returns False."""
        assert not is_universal_wheel("invalid.whl")


class TestIsManylinuxWheel:
    """Test manylinux wheel detection."""

    def test_detect_manylinux2014_wheel(self):
        """Test detection of manylinux2014 wheel."""
        assert is_manylinux_wheel("package-1.0-cp310-cp310-manylinux2014_x86_64.whl")

    def test_detect_manylinux_2_28_wheel(self):
        """Test detection of manylinux_2_28 wheel."""
        assert is_manylinux_wheel("package-1.0-cp310-cp310-manylinux_2_28_x86_64.whl")

    def test_detect_musllinux_wheel(self):
        """Test detection of musllinux wheel."""
        assert is_manylinux_wheel("package-1.0-cp310-cp310-musllinux_1_2_x86_64.whl")

    def test_non_manylinux_wheel(self):
        """Test that universal wheel is not manylinux."""
        assert not is_manylinux_wheel("package-1.0-py3-none-any.whl")

    def test_invalid_wheel_filename(self):
        """Test that invalid filename returns False."""
        assert not is_manylinux_wheel("invalid.whl")


class TestCaseInsensitivity:
    """Test case insensitivity handling."""

    def test_manylinux_case_insensitive(self):
        """Test that manylinux detection is case insensitive."""
        # Even though not standard, ensure lowercase matching works
        assert is_manylinux_wheel("package-1.0-cp310-cp310-MANYLINUX_2_28_x86_64.whl")
