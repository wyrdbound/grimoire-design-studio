#!/usr/bin/env python3
"""
Main entry point for GRIMOIRE Design Studio.
"""

import argparse
import signal
import sys
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from pathlib import Path

    from PyQt6.QtCore import QCoreApplication
    from PyQt6.QtWidgets import QApplication

from .core.config import get_config


def setup_logging(debug: bool = False) -> None:
    """Set up comprehensive logging configuration with file rotation."""
    import logging
    import logging.handlers

    from grimoire_logging import get_logger

    # Determine log directory in user's app data
    log_dir = _get_app_data_directory() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Set log level
    level = logging.DEBUG if debug else logging.INFO

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler with formatted output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (10MB max, keep 5 files)
    log_file = log_dir / "grimoire-studio.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)  # Always debug level in files
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Initialize grimoire-logging
    logger = get_logger(__name__)
    logger.info("GRIMOIRE Design Studio starting...")
    logger.debug(f"Logging configured - Console: {level}, File: {log_file}")

    # Always inform user about log file location
    print(f"[LOG] Log files are saved to: {log_file}")
    if debug:
        print(
            "[DEBUG] Debug mode enabled - detailed logs will be written to the file above"
        )


def _get_app_data_directory() -> "Path":
    """Get the application data directory for the current platform."""
    import platform
    from pathlib import Path

    system = platform.system()
    if system == "Windows":
        # Use APPDATA on Windows
        import os

        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        return Path(app_data) / "GRIMOIRE Design Studio"
    elif system == "Darwin":  # macOS
        # Use ~/Library/Application Support on macOS
        return (
            Path.home() / "Library" / "Application Support" / "GRIMOIRE Design Studio"
        )
    else:  # Linux and other Unix-like systems
        # Use XDG_CONFIG_HOME or ~/.config on Linux
        import os

        config_home = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        return Path(config_home) / "grimoire-design-studio"


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="GRIMOIRE Design Studio - A design studio for GRIMOIRE systems"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    parser.add_argument(
        "--logs", action="store_true", help="Show log directory path and exit"
    )
    parser.add_argument(
        "--config-reset",
        action="store_true",
        help="Reset configuration to defaults and exit",
    )
    parser.add_argument(
        "--config-export",
        metavar="FILE",
        help="Export current configuration to file and exit",
    )
    parser.add_argument(
        "--config-import", metavar="FILE", help="Import configuration from file"
    )
    parser.add_argument(
        "--no-restore-session",
        action="store_true",
        help="Don't restore previous session on startup",
    )
    parser.add_argument(
        "--config-show",
        action="store_true",
        help="Display current configuration and exit",
    )
    return parser.parse_args()


def setup_signal_handlers(app: Union["QApplication", "QCoreApplication"]) -> None:
    """Set up signal handlers for graceful shutdown."""

    def signal_handler(signum: int, frame: Optional[object]) -> None:
        print(f"\nReceived signal {signum}, shutting down gracefully...")
        app.quit()

    # Set up Python signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # For better Qt integration, also handle SIGINT through Qt
    def handle_sigint() -> None:
        print("\nShutdown requested (Ctrl+C), shutting down gracefully...")
        app.quit()

    # Make the app quit on Ctrl+C by setting up a more responsive timer
    from PyQt6.QtCore import QTimer

    sigint_timer = QTimer()
    sigint_timer.timeout.connect(lambda: None)  # Allow Python signal processing
    sigint_timer.start(50)  # More frequent checks for better responsiveness


def main() -> int:
    """Main application entry point."""
    args = parse_arguments()

    # Handle configuration commands before setting up logging
    if args.config_reset:
        try:
            config = get_config()
            config.reset_to_defaults()
            print("[SUCCESS] Configuration reset to defaults")
            return 0
        except Exception as e:
            print(f"[ERROR] Failed to reset configuration: {e}", file=sys.stderr)
            return 1

    if args.config_export:
        try:
            config = get_config()
            config.export_config(args.config_export)
            print(f"[SUCCESS] Configuration exported to {args.config_export}")
            return 0
        except Exception as e:
            print(f"[ERROR] Failed to export configuration: {e}", file=sys.stderr)
            return 1

    if args.config_import:
        try:
            config = get_config()
            config.import_config(args.config_import)
            print(f"[SUCCESS] Configuration imported from {args.config_import}")
            return 0
        except Exception as e:
            print(f"[ERROR] Failed to import configuration: {e}", file=sys.stderr)
            return 1

    if args.config_show:
        try:
            config = get_config()
            print(config.display_config())
            return 0
        except Exception as e:
            print(f"[ERROR] Failed to display configuration: {e}", file=sys.stderr)
            return 1

    # Handle --logs flag before setting up logging
    if args.logs:
        log_dir = _get_app_data_directory() / "logs"
        log_file = log_dir / "grimoire-studio.log"
        print(f"[DIR] Log directory: {log_dir}")
        print(f"[FILE] Log file: {log_file}")
        print(f"[INFO] Log directory exists: {log_dir.exists()}")
        print(f"[INFO] Log file exists: {log_file.exists()}")
        if log_file.exists():
            import os

            print(f"[SIZE] Log file size: {log_file.stat().st_size:,} bytes")
            # Try to open the log directory in the system file manager
            # Skip opening during tests to avoid interrupting test runs

            is_testing = (
                os.environ.get("PYTEST_CURRENT_TEST")
                or os.environ.get("CI")
                or os.environ.get("GITHUB_ACTIONS")
                or "pytest" in sys.modules
            )

            if not is_testing:
                try:
                    import platform
                    import shutil
                    import subprocess  # nosec B404 - Safe usage for opening file manager

                    # Validate that the log directory exists and is safe to open
                    if not log_dir.exists() or not log_dir.is_dir():
                        print("ℹ️  Log directory does not exist or is not a directory")
                        return 0

                    # Use full executable paths for security
                    system = platform.system()
                    opener = None
                    opened = False

                    if system == "Darwin":  # macOS
                        opener = shutil.which("open")
                        if opener:
                            subprocess.run(
                                [opener, str(log_dir)], check=False, timeout=10
                            )  # nosec B603
                            opened = True
                    elif system == "Windows":
                        opener = shutil.which("explorer")
                        if opener:
                            subprocess.run(
                                [opener, str(log_dir)], check=False, timeout=10
                            )  # nosec B603
                            opened = True
                    elif system == "Linux":
                        opener = shutil.which("xdg-open")
                        if opener:
                            subprocess.run(
                                [opener, str(log_dir)], check=False, timeout=10
                            )  # nosec B603
                            opened = True

                    if opened:
                        print("[SUCCESS] Opened log directory in file manager")
                    else:
                        print("[INFO] Could not find system file manager command")
                except Exception as e:
                    print(f"[INFO] Could not open directory automatically: {e}")
            else:
                print("[TEST] Skipping file manager open (detected test environment)")
        return 0

    # Initialize configuration system
    config = get_config()

    # Apply configuration imports if requested
    if args.config_import:
        try:
            config.import_config(args.config_import)
            print(f"[SUCCESS] Configuration imported from {args.config_import}")
        except Exception as e:
            print(f"[WARNING] Failed to import configuration: {e}", file=sys.stderr)

    # Override debug setting from command line
    if args.debug:
        config.set("logging/level", "DEBUG")

    # Set session restore preference
    if args.no_restore_session:
        config.set("app/restore_session", False)

    # Setup logging using configuration
    debug_mode = config.get("logging/level", "INFO").upper() == "DEBUG"
    setup_logging(debug=debug_mode)

    try:
        # Import Qt after logging is set up
        import os

        from PyQt6.QtCore import QCoreApplication

        # Detect headless CI environment and use QCoreApplication to avoid GUI issues
        # This prevents Windows CI exit code 1 problems with Qt GUI initialization
        is_headless = (
            os.environ.get("QT_QPA_PLATFORM") in ("minimal", "offscreen")
            or os.environ.get("CI")
            or os.environ.get("GITHUB_ACTIONS")
            or os.environ.get("PYTEST_CURRENT_TEST")  # Running under pytest
        )

        if is_headless:
            # Use QCoreApplication for headless environments (CI, tests)
            app = QCoreApplication(sys.argv)
            app.setApplicationName("GRIMOIRE Design Studio")
            app.setApplicationVersion("1.0.0")
            app.setOrganizationName("Wyrdbound")
            app.setOrganizationDomain("wyrdbound.com")

            # Set up signal handlers for CTRL+C
            setup_signal_handlers(app)

            # For headless mode, just start and immediately exit successfully
            print("Running in headless mode - application initialized successfully")
            return 0
        else:
            # Use full GUI application for interactive mode
            from PyQt6.QtWidgets import QApplication

            # Import our new main window
            from .ui.main_window import MainWindow

            # Create the Qt application
            app = QApplication(sys.argv)
            app.setApplicationName("GRIMOIRE Design Studio")
            app.setApplicationVersion("1.0.0")
            app.setOrganizationName("Wyrdbound")
            app.setOrganizationDomain("wyrdbound.com")

            # Set up signal handlers for CTRL+C
            setup_signal_handlers(app)

            # Create the main window
            main_window = MainWindow()

            # Show the window
            main_window.show()

            # Run the application
            return app.exec()

    except ImportError as e:
        print(f"Error: Missing required dependencies: {e}", file=sys.stderr)
        print("Please install PyQt6 and other required packages", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nShutdown requested by user")
        return 0
    except Exception as e:
        import traceback

        print(f"Error: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
