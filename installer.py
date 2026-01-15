"""Platform-agnostic installer interface for Focus Blocker."""

import sys

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"

if IS_WINDOWS:
    from windows_installer import (
        install,
        uninstall,
        get_status,
        is_installed,
        is_running,
    )
elif IS_MACOS:
    from macos_installer import install, uninstall, get_status, is_installed, is_running
else:

    def install() -> bool:
        print(f"Error: Unsupported platform '{sys.platform}'.")
        return False

    def uninstall() -> bool:
        print(f"Error: Unsupported platform '{sys.platform}'.")
        return False

    def get_status() -> dict:
        return {"installed": False, "running": False, "error": "Unsupported platform"}

    def is_installed() -> bool:
        return False

    def is_running() -> bool:
        return False


__all__ = ["install", "uninstall", "get_status", "is_installed", "is_running"]
