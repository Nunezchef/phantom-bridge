"""Phantom Bridge — Dependency installer.

Installs x11vnc and noVNC packages required for the remote browser viewer.
Run from A0's Plugins UI or manually: python execute.py
"""

import subprocess
import sys


def main():
    print("Phantom Bridge: Installing dependencies...")

    # Install x11vnc + novnc (includes websockify) via apt
    result = subprocess.run(
        ["apt-get", "install", "-y", "--no-install-recommends", "x11vnc", "novnc"],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print(f"ERROR: apt-get install failed:\n{result.stderr}")
        print("\nIf running outside Docker, install manually:")
        print("  sudo apt-get install x11vnc novnc")
        return 1

    print("Installed: x11vnc, novnc (with websockify)")

    # Install Python dependency
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "websockets>=12.0,<14.0"],
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        print(f"WARNING: pip install websockets failed:\n{result.stderr}")
    else:
        print("Installed: websockets (Python)")

    print("\nPhantom Bridge dependencies installed successfully.")
    print("You can now open the bridge from A0's sidebar panel.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
