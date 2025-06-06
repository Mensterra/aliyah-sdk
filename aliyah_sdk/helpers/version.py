from importlib.metadata import PackageNotFoundError, version

import requests

from aliyah_sdk.logging import logger


def get_aaliyah_version():
    try:
        pkg_version = version("aliyah-sdk")  # ← Change this
        return pkg_version
    except Exception as e:
        logger.warning("Error reading package version: %s", e)
        return None

def check_aaliyah_update():
    try:
        response = requests.get("https://pypi.org/pypi/aliyah-sdk/json")  # ← And this

        if response.status_code == 200:
            json_data = response.json()
            latest_version = json_data["info"]["version"]

            try:
                current_version = version("aliyah-sdk")  # ← And this
            except PackageNotFoundError:
                return None

            if not latest_version == current_version:
                logger.warning(
                    " WARNING: aaliyah-sdk is out of date. Please update with the command: 'pip install --upgrade aliyah-sdk'"  # ← And this
                )
    except Exception as e:
        logger.debug(f"Failed to check for updates: {e}")
        return None