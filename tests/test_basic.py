"""
Basic tests for GRIMOIRE Design Studio installation and setup.
"""


def test_package_import():
    """Test that the package can be imported."""
    import grimoire_studio

    assert grimoire_studio.__version__ == "1.0.0"


def test_main_function_exists():
    """Test that the main function exists and is callable."""
    from grimoire_studio.main import main

    assert callable(main)


def test_parse_arguments():
    """Test command line argument parsing."""
    import sys

    from grimoire_studio.main import parse_arguments

    # Save original argv
    original_argv = sys.argv[:]

    try:
        # Test help argument parsing
        sys.argv = ["grimoire-studio", "--debug"]
        args = parse_arguments()
        assert args.debug is True

        sys.argv = ["grimoire-studio"]
        args = parse_arguments()
        assert args.debug is False

    finally:
        # Restore original argv
        sys.argv[:] = original_argv
