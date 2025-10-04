"""Name generation service for GRIMOIRE flows.

This module provides the NameService class which integrates with wyrdbound-rng
to handle name generation operations in GRIMOIRE flows.
"""

from __future__ import annotations

import random

from grimoire_logging import get_logger
from wyrdbound_rng import FantasyNameSegmenter, Generator, JapaneseNameSegmenter

logger = get_logger(__name__)


# Map of built-in name lists from wyrdbound-rng
_BUILTIN_NAME_LISTS = {
    "generic-fantasy": "generic-fantasy",
    "generic-fantasy-male": "generic-fantasy-male",
    "generic-fantasy-female": "generic-fantasy-female",
    "japanese-sengoku": "japanese-sengoku",
    "japanese-sengoku-clan": "japanese-sengoku-clan",
    "japanese-sengoku-daimyo": "japanese-sengoku-daimyo",
    "japanese-sengoku-religious": "japanese-sengoku-religious",
    "japanese-sengoku-rogue": "japanese-sengoku-rogue",
    "japanese-sengoku-samurai": "japanese-sengoku-samurai",
    "japanese-sengoku-women": "japanese-sengoku-women",
    "japanese-swordsmen": "japanese-swordsmen",
    "warhammer40k-space-marine-names": "warhammer40k-space-marine-names",
}

# Supported segmenters
_SEGMENTERS = {
    "fantasy": FantasyNameSegmenter,
    "japanese": JapaneseNameSegmenter,
}


class NameService:
    """Service for name generation operations.

    This service integrates with wyrdbound-rng to provide name generation
    functionality for GRIMOIRE flows. It supports various name types and
    styles using built-in name corpora from wyrdbound-rng.

    Example:
        >>> service = NameService()
        >>> name = service.generate_name("character", "fantasy")
        >>> print(name)
        'Theron'
    """

    def __init__(
        self,
        name_list: str = "generic-fantasy",
        segmenter: str = "fantasy",
        seed: int | None = None,
    ) -> None:
        """Initialize the name service.

        Args:
            name_list: Name list identifier from wyrdbound-rng built-ins
            segmenter: Segmenter type ("fantasy" or "japanese")
            seed: Optional random seed for deterministic generation
        """
        if seed is not None:
            random.seed(seed)

        # Get segmenter class
        segmenter_class = _SEGMENTERS.get(segmenter.lower())
        if segmenter_class is None:
            raise ValueError(
                f"Unsupported segmenter: {segmenter}. "
                f"Supported: {list(_SEGMENTERS.keys())}"
            )

        # Create generator with built-in name list
        try:
            self.generator = Generator(name_list, segmenter=segmenter_class())
            self.name_list = name_list
            self.segmenter = segmenter
            logger.info(
                f"NameService initialized with {name_list} using {segmenter} segmenter"
            )
        except Exception as e:
            logger.error(f"Failed to initialize name generator: {e}")
            raise RuntimeError(
                f"Failed to initialize name generator with list '{name_list}': {e}"
            ) from e

    def generate_name(
        self,
        name_type: str = "character",
        style: str = "fantasy",
        max_length: int = 15,
        algorithm: str = "simple",
    ) -> str:
        """Generate a name using wyrdbound-rng.

        Args:
            name_type: Type of name (currently ignored, uses generator's corpus)
            style: Style of name (currently ignored, uses generator's corpus)
            max_length: Maximum character length for generated name
            algorithm: Generation algorithm ("simple", "bayesian", "very_simple")

        Returns:
            Generated name string

        Raises:
            RuntimeError: If name generation fails

        Example:
            >>> name = service.generate_name(max_length=12, algorithm="simple")
            >>> print(name)
            'Aldric'
        """
        logger.debug(
            f"Generating name with max_length={max_length}, algorithm={algorithm}"
        )

        try:
            result = self.generator.generate_name(
                max_len=max_length, algorithm=algorithm
            )
            name = str(result.name)
            logger.info(f"Generated name: {name}")
            return name
        except Exception as e:
            error_msg = f"Failed to generate name: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def generate_names(
        self,
        count: int,
        name_type: str = "character",
        style: str = "fantasy",
        max_length: int = 15,
        algorithm: str = "simple",
    ) -> list[str]:
        """Generate multiple names.

        Args:
            count: Number of names to generate
            name_type: Type of names (currently ignored)
            style: Style of names (currently ignored)
            max_length: Maximum character length for each name
            algorithm: Generation algorithm

        Returns:
            List of generated names

        Raises:
            ValueError: If count is invalid
            RuntimeError: If name generation fails

        Example:
            >>> names = service.generate_names(5, max_length=12)
            >>> for name in names:
            ...     print(name)
        """
        if count < 1:
            raise ValueError("Count must be at least 1")
        if count > 1000:
            raise ValueError("Count cannot exceed 1000")

        logger.debug(
            f"Generating {count} names with max_length={max_length}, "
            f"algorithm={algorithm}"
        )

        try:
            results = self.generator.generate(
                n=count, max_chars=max_length, algorithm=algorithm
            )
            names = [result.name for result in results]
            logger.info(f"Generated {len(names)} names successfully")
            return names
        except Exception as e:
            error_msg = f"Failed to generate {count} names: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_supported_types(self) -> list[str]:
        """Get list of supported name types.

        Note: With wyrdbound-rng, types depend on the loaded name list.
        This returns legacy API compatibility values.

        Returns:
            List of supported name type strings
        """
        return ["character", "place", "first", "last"]

    def get_supported_styles(self) -> list[str]:
        """Get list of supported name styles.

        Note: With wyrdbound-rng, styles depend on the loaded name list.
        This returns legacy API compatibility values.

        Returns:
            List of supported style strings
        """
        return ["fantasy"]

    def get_available_name_lists(self) -> list[str]:
        """Get list of available built-in name lists.

        Returns:
            List of built-in name list identifiers
        """
        return list(_BUILTIN_NAME_LISTS.keys())

    def name_exists_in_corpus(self, name: str) -> bool:
        """Check if a name exists in the source corpus.

        Args:
            name: Name to check

        Returns:
            True if name exists in corpus, False otherwise
        """
        exists: bool = self.generator.name_exists_in_corpus(name)
        return exists
