"""Tests for Phase 1.4: Docker image determinism."""

import pytest

from headless_wheel_builder.exceptions import IsolationError
from headless_wheel_builder.security_validation import ensure_deterministic_image


class TestDockerImageDeterminism:
    """Test Docker image selection for determinism."""

    IMAGES = {
        "manylinux2014_x86_64": "quay.io/pypa/manylinux2014_x86_64",
        "manylinux_2_28_x86_64": "quay.io/pypa/manylinux_2_28_x86_64",
        "manylinux_2_34_x86_64": "quay.io/pypa/manylinux_2_34_x86_64",
        "musllinux_1_2_x86_64": "quay.io/pypa/musllinux_1_2_x86_64",
        "manylinux2014_aarch64": "quay.io/pypa/manylinux2014_aarch64",
        "manylinux_2_28_aarch64": "quay.io/pypa/manylinux_2_28_aarch64",
    }

    def test_deterministic_image_selection_by_key(self):
        """Test that image selection by key is deterministic."""
        # Same key should always return same image
        result1 = ensure_deterministic_image("manylinux_2_28_x86_64", self.IMAGES)
        result2 = ensure_deterministic_image("manylinux_2_28_x86_64", self.IMAGES)

        assert result1 == result2
        assert result1 == "quay.io/pypa/manylinux_2_28_x86_64"

    def test_deterministic_image_selection_multiple_calls(self):
        """Test determinism across multiple calls."""
        key = "manylinux_2_34_x86_64"
        results = [ensure_deterministic_image(key, self.IMAGES) for _ in range(10)]

        # All results should be identical
        assert all(r == results[0] for r in results)
        assert results[0] == "quay.io/pypa/manylinux_2_34_x86_64"

    def test_full_url_recognition(self):
        """Test that full URLs are recognized and returned deterministically."""
        full_url = "quay.io/pypa/manylinux_2_28_x86_64"

        # Should recognize full URL and return it
        result1 = ensure_deterministic_image(full_url, self.IMAGES)
        result2 = ensure_deterministic_image(full_url, self.IMAGES)

        assert result1 == full_url
        assert result2 == full_url
        assert result1 == result2

    def test_unknown_key_rejected(self):
        """Test that unknown keys are rejected with clear error."""
        with pytest.raises(IsolationError, match="Unknown image key"):
            ensure_deterministic_image("unknown_key", self.IMAGES)

    def test_unsupported_url_rejected(self):
        """Test that unsupported URLs are rejected."""
        with pytest.raises(IsolationError, match="Unknown or unsupported"):
            ensure_deterministic_image("quay.io/unknown/unknown_image", self.IMAGES)

    def test_all_known_keys_supported(self):
        """Test that all keys in IMAGES dict are supported."""
        for key in self.IMAGES:
            result = ensure_deterministic_image(key, self.IMAGES)
            assert result == self.IMAGES[key]

    def test_determinism_with_large_image_registry(self):
        """Test determinism with a large registry of images."""
        large_registry = {
            f"image_{i}": f"quay.io/pypa/image_{i}"
            for i in range(100)
        }

        # Should return consistent results
        for key in list(large_registry.keys())[:10]:
            result1 = ensure_deterministic_image(key, large_registry)
            result2 = ensure_deterministic_image(key, large_registry)
            assert result1 == result2 == large_registry[key]

    def test_architecture_specific_images_deterministic(self):
        """Test determinism for architecture-specific images."""
        arch_images = {
            "manylinux_2_28_x86_64": "quay.io/pypa/manylinux_2_28_x86_64",
            "manylinux_2_28_aarch64": "quay.io/pypa/manylinux_2_28_aarch64",
            "manylinux_2_28_i686": "quay.io/pypa/manylinux_2_28_i686",
        }

        # Each arch should consistently return its image
        for arch_key, expected_image in arch_images.items():
            result1 = ensure_deterministic_image(arch_key, arch_images)
            result2 = ensure_deterministic_image(arch_key, arch_images)
            result3 = ensure_deterministic_image(arch_key, arch_images)

            assert result1 == result2 == result3 == expected_image

    def test_canonical_url_preservation(self):
        """Test that canonical URLs are preserved exactly."""
        canonical = "quay.io/pypa/manylinux_2_28_x86_64:latest"
        images = {
            "manylinux_2_28": canonical
        }

        result = ensure_deterministic_image("manylinux_2_28", images)
        assert result == canonical

    def test_error_message_clarity(self):
        """Test that error messages are clear and helpful."""
        try:
            ensure_deterministic_image("bad_key", self.IMAGES)
            pytest.fail("Should have raised IsolationError")
        except IsolationError as e:
            error_msg = str(e)
            # Should mention the bad key
            assert "bad_key" in error_msg or "Unknown image key" in error_msg
            # Should provide available keys in error
            assert any(key in error_msg for key in self.IMAGES)
