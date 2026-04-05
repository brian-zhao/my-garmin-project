"""
setup.py — First-time setup wizard.

Run once to install dependencies and save your Garmin credentials.

    python setup.py
"""

import subprocess
import sys
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"
REQUIRED_PACKAGES = ["garminconnect"]


def install_dependencies() -> None:
    print("\n[1/3] Checking dependencies...")
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace("-", "_"))
            print(f"  ✓  {pkg} already installed")
        except ImportError:
            print(f"  →  Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            print(f"  ✓  {pkg} installed")


def create_env() -> None:
    print("\n[2/3] Garmin Connect credentials")

    if ENV_FILE.exists():
        overwrite = input("  .env file already exists. Overwrite? (y/N): ").strip().lower()
        if overwrite != "y":
            print("  Keeping existing .env")
            return

    print("  Your credentials are stored locally in .env and never shared.")
    email = input("  Garmin email: ").strip()
    password = input("  Garmin password (characters visible): ").strip()

    ENV_FILE.write_text(f"GARMIN_EMAIL={email}\nGARMIN_PASSWORD={password}\n")
    print(f"  ✓  Credentials saved to {ENV_FILE}")


def test_login() -> None:
    print("\n[3/3] Testing Garmin login...")
    # Load the .env we just wrote
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            import os
            os.environ[k.strip()] = v.strip()

    try:
        from garmin_auth import garmin_login
        client = garmin_login()
        profile = client.get_user_profile()
        print(f"  ✓  Logged in successfully! (account id: {profile.get('id')})")
    except SystemExit as e:
        print(f"  ✗  Login failed: {e}")
        print("     Check your email and password in .env and run setup again.")
        sys.exit(1)


def main() -> None:
    print("=" * 50)
    print("  Garmin Running Analytics — Setup")
    print("=" * 50)

    install_dependencies()
    create_env()
    test_login()

    print("\n" + "=" * 50)
    print("  Setup complete! Run the app with:")
    print()
    print("      python run.py")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
