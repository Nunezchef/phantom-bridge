"""Phantom Bridge — Setup script.

Installs x11vnc and noVNC packages, then prints setup instructions.
Run from A0's Plugins UI or manually: python execute.py
"""

import shutil
import subprocess
import sys


def main():
    print("=" * 50)
    print("  Phantom Bridge — Setup")
    print("=" * 50)
    print()

    # Check what's already installed
    has_x11vnc = shutil.which("x11vnc") is not None
    has_websockify = shutil.which("websockify") is not None

    if has_x11vnc and has_websockify:
        print("[OK] x11vnc and websockify already installed.")
    else:
        print("Installing x11vnc and noVNC...")
        result = subprocess.run(
            ["apt-get", "install", "-y", "--no-install-recommends", "x11vnc", "novnc"],
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            print(f"[ERROR] apt-get install failed:\n{result.stderr}")
            print("\nManual install: sudo apt-get install x11vnc novnc")
            return 1

        print("[OK] Installed x11vnc and noVNC (with websockify)")

    # Install Python dependency
    try:
        import websockets  # noqa: F401
        print("[OK] websockets already installed.")
    except ImportError:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "websockets>=12.0,<14.0"],
            text=True,
            capture_output=True,
        )
        if result.returncode == 0:
            print("[OK] Installed websockets (Python)")
        else:
            print(f"[WARN] pip install websockets failed: {result.stderr[:100]}")

    print()
    print("-" * 50)
    print("  Setup complete!")
    print("-" * 50)
    print()
    print("  Make sure port 6080 is exposed in docker-compose.yml:")
    print()
    print('    ports:')
    print('      - "5050:5000"')
    print('      - "6080:6080"    # Phantom Bridge viewer')
    print()
    print("  Then restart: docker compose up -d")
    print()
    print("  Open A0's sidebar > Phantom Bridge to start browsing.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
