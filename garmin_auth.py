import base64
import logging
import os

import requests
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from garth.exc import GarthHTTPError

TOKEN_DIR = os.path.expanduser(os.getenv("TOKEN_DIR", "~/.garminconnect"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def get_credentials() -> tuple[str, str]:
    email = os.environ.get("GARMIN_EMAIL") or input("Enter Garmin email: ")
    raw_b64 = os.environ.get("GARMINCONNECT_BASE64_PASSWORD")
    if raw_b64:
        password = base64.b64decode(raw_b64).decode("utf-8")
    else:
        password = os.environ.get("GARMIN_PASSWORD") or input(
            "Enter Garmin password (characters will be visible): "
        )
    return email, password


def garmin_login() -> Garmin:
    try:
        logging.info("Trying to login using cached tokens from '%s'...", TOKEN_DIR)
        client = Garmin()
        client.login(TOKEN_DIR)
        logging.info("Login successful using cached tokens.")
        return client

    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError):
        logging.warning("No valid cached session — logging in with credentials.")

    try:
        email, password = get_credentials()
        client = Garmin(email=email, password=password, return_on_mfa=True)
        result, mfa_context = client.login()

        if result == "needs_mfa":
            mfa_code = input("Enter MFA code (email/SMS): ").strip()
            client.resume_login(mfa_context, mfa_code)

        client.garth.dump(TOKEN_DIR)
        logging.info("Tokens cached to '%s'.", TOKEN_DIR)

        # Reload from token store so subsequent calls use the stored session.
        client.login(TOKEN_DIR)
        return client

    except (
        FileNotFoundError,
        GarthHTTPError,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
        requests.exceptions.HTTPError,
    ) as err:
        logging.error("Login failed: %s", err)
        raise SystemExit("Could not authenticate with Garmin Connect.") from err
