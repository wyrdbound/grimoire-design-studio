"""
Tests for the Name Service.

This module tests the name generation functionality using wyrdbound-rng.
"""

import pytest

from grimoire_studio.services import NameService


class TestNameService:
    """Test the NameService class."""

    def test_initialization_without_seed(self):
        """Test NameService initialization without seed."""
        service = NameService()
        assert service is not None
        assert service.name_list == "generic-fantasy"
        assert service.segmenter == "fantasy"

    def test_initialization_with_seed(self):
        """Test NameService initialization with seed."""
        service = NameService(seed=42)
        assert service is not None

    def test_initialization_with_custom_list(self):
        """Test initialization with different name list."""
        service = NameService(name_list="generic-fantasy-male")
        assert service.name_list == "generic-fantasy-male"

    def test_initialization_with_japanese_segmenter(self):
        """Test initialization with Japanese segmenter."""
        service = NameService(name_list="japanese-sengoku", segmenter="japanese")
        assert service.segmenter == "japanese"

    def test_generate_character_name(self):
        """Test generating a character name."""
        service = NameService()
        name = service.generate_name(name_type="character", style="fantasy")

        assert name is not None
        assert len(name) > 0
        assert isinstance(name, str)

    def test_generate_with_max_length(self):
        """Test generating a name with max length constraint."""
        service = NameService()
        name = service.generate_name(max_length=8)

        assert name is not None
        assert len(name) <= 8

    def test_generate_with_algorithm(self):
        """Test generating with different algorithms."""
        service = NameService()

        # Simple algorithm
        name1 = service.generate_name(algorithm="simple")
        assert name1 is not None

        # Bayesian algorithm
        name2 = service.generate_name(algorithm="bayesian")
        assert name2 is not None

        # Very simple algorithm
        name3 = service.generate_name(algorithm="very_simple")
        assert name3 is not None

    def test_generate_multiple_names(self):
        """Test generating multiple names."""
        service = NameService()
        names = service.generate_names(count=5)

        assert len(names) == 5
        assert all(isinstance(name, str) for name in names)
        assert all(len(name) > 0 for name in names)

    def test_generate_zero_names(self):
        """Test generating zero names raises error."""
        service = NameService()

        with pytest.raises(ValueError, match="Count must be at least 1"):
            service.generate_names(name_type="character", style="fantasy", count=0)

    def test_generate_one_name(self):
        """Test generating one name."""
        service = NameService()
        names = service.generate_names(name_type="character", style="fantasy", count=1)

        assert len(names) == 1
        assert isinstance(names[0], str)

    def test_seeded_generation_is_deterministic(self):
        """Test that seeded generation produces consistent results across multiple calls."""
        # Generate a sequence with a seeded service
        service = NameService(seed=42)
        names1 = [service.generate_name(name_type="character") for _ in range(3)]

        # Generate same sequence again with same seed
        service = NameService(seed=42)
        names2 = [service.generate_name(name_type="character") for _ in range(3)]

        assert names1 == names2

    def test_different_seeds_produce_different_names(self):
        """Test that different seeds produce different results."""
        service1 = NameService(seed=42)
        service2 = NameService(seed=99)

        names1 = service1.generate_names(count=5)
        names2 = service2.generate_names(count=5)

        # Very unlikely to be identical with different seeds
        assert names1 != names2

    def test_invalid_name_type(self):
        """Test generating with invalid name type - now ignored by wyrdbound-rng."""
        service = NameService()

        # name_type is now ignored, so this should still generate a name
        name = service.generate_name(name_type="invalid", style="fantasy")
        assert name is not None
        assert len(name) > 0

    def test_invalid_style(self):
        """Test generating with invalid style logs warning but doesn't raise."""
        service = NameService()

        # Invalid styles are tolerated (falls back to fantasy)
        name = service.generate_name(name_type="character", style="invalid")
        assert name is not None
        assert len(name) > 0

    def test_empty_name_type(self):
        """Test generating with empty name type - now ignored by wyrdbound-rng."""
        service = NameService()

        # name_type is now ignored, so this should still generate a name
        name = service.generate_name(name_type="", style="fantasy")
        assert name is not None
        assert len(name) > 0

    def test_empty_style(self):
        """Test generating with empty style logs warning but doesn't raise."""
        service = NameService()

        # Empty styles are tolerated (falls back to fantasy)
        name = service.generate_name(name_type="character", style="")
        assert name is not None
        assert len(name) > 0

    def test_negative_count(self):
        """Test generating with negative count."""
        service = NameService()

        with pytest.raises(ValueError, match="Count must be at least 1"):
            service.generate_names(count=-1)

    def test_supported_types(self):
        """Test that all supported types work - now name_type is ignored."""
        service = NameService()
        supported_types = ["character", "first", "last", "place"]

        for name_type in supported_types:
            name = service.generate_name(name_type=name_type, style="fantasy")
            assert name is not None
            assert len(name) > 0

    def test_supported_styles(self):
        """Test that different name lists work."""
        # Test fantasy name list
        service_fantasy = NameService(name_list="generic-fantasy")
        name_fantasy = service_fantasy.generate_name()
        assert name_fantasy is not None
        assert len(name_fantasy) > 0

        # Test Japanese name list
        service_japanese = NameService(
            name_list="japanese-sengoku-samurai", segmenter="japanese"
        )
        name_japanese = service_japanese.generate_name()
        assert name_japanese is not None
        assert len(name_japanese) > 0

    def test_name_diversity(self):
        """Test that generated names have some diversity."""
        service = NameService()
        names = service.generate_names(count=20)

        # Should have at least some unique names
        unique_names = set(names)
        assert len(unique_names) > 1  # Should have variety

    def test_first_names_have_no_spaces(self):
        """Test that generated names from wyrdbound-rng are single words."""
        service = NameService()
        names = service.generate_names(name_type="first", style="fantasy", count=10)

        # wyrdbound-rng generates single words by default
        assert all(" " not in name for name in names)

    def test_character_names_single_words(self):
        """Test that wyrdbound-rng generates single-word names (not 'first last')."""
        service = NameService()
        names = service.generate_names(name_type="character", style="fantasy", count=10)

        # wyrdbound-rng generates single words, not "first last" combinations
        assert all(" " not in name for name in names)

    def test_place_names_format(self):
        """Test that place names have expected format."""
        service = NameService()
        names = service.generate_names(name_type="place", style="fantasy", count=10)

        # Place names from wyrdbound-rng are single words
        assert all(isinstance(name, str) for name in names)
        assert all(len(name) > 0 for name in names)
        assert all(" " not in name for name in names)

    def test_consistent_results_same_seed(self):
        """Test that same seed produces consistent sequence."""
        service = NameService(seed=12345)

        # Generate sequence 1
        names1 = [service.generate_name() for _ in range(3)]

        # Reset with same seed
        service = NameService(seed=12345)

        # Generate sequence 2
        names2 = [service.generate_name() for _ in range(3)]

        assert names1 == names2

    def test_large_batch_generation(self):
        """Test generating a large batch of names."""
        service = NameService()
        names = service.generate_names(count=100)

        assert len(names) == 100
        assert all(isinstance(name, str) for name in names)
        assert all(len(name) > 0 for name in names)

    def test_invalid_segmenter(self):
        """Test initialization with invalid segmenter raises error."""
        with pytest.raises(ValueError, match="Unsupported segmenter"):
            NameService(segmenter="invalid")

    def test_available_name_lists(self):
        """Test getting list of available name lists."""
        service = NameService()
        name_lists = service.get_available_name_lists()

        assert isinstance(name_lists, list)
        assert len(name_lists) > 0
        assert "generic-fantasy" in name_lists
        assert "japanese-sengoku" in name_lists

    def test_name_exists_in_corpus(self):
        """Test checking if a name exists in corpus."""
        service = NameService()

        # Generate a name multiple times until we get one that exists
        # (or verify the API works correctly)
        name = service.generate_name()

        # The method should work regardless of result
        exists = service.name_exists_in_corpus(name)
        assert isinstance(exists, bool)

        # A made-up name should not exist
        fake_name = "Zxqwerty123456789"
        assert not service.name_exists_in_corpus(fake_name)
