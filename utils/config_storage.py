from __future__ import annotations

import os
import json
from config import STORAGE_DIR, get_logger

logger = get_logger("config_storage")

# File paths
ADMINS_FILE = os.path.join(STORAGE_DIR, "admins.json")
PERSONALITY_FILE = os.path.join(STORAGE_DIR, "personality.json")


def save_admins_to_file(admin_list: list[str]) -> bool:
    """
    Save admin user list to a file

    Args:
        admin_list: List of admin user IDs

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure admin_list is actually a list, not a string or other type
        if not isinstance(admin_list, list):
            logger.error(f"CONFIG_ERROR: admin_list is not a list: {type(admin_list)}")
            return False

        # Make sure the storage directory exists
        os.makedirs(os.path.dirname(ADMINS_FILE), exist_ok=True)

        with open(ADMINS_FILE, "w") as f:
            json.dump({"admins": admin_list}, f, indent=2)
        logger.info(f"CONFIG: Saved {len(admin_list)} admins to {ADMINS_FILE}")
        return True
    except Exception as e:
        logger.error(f"CONFIG_ERROR: Failed to save admin list: {e}")
        return False


def load_admins_from_file() -> list[str]:
    """
    Load admin user list from file

    Returns:
        list: List of admin user IDs, empty list if file doesn't exist
    """
    try:
        if not os.path.exists(ADMINS_FILE):
            logger.info(f"CONFIG: Admin file {ADMINS_FILE} not found, using defaults")
            return []

        with open(ADMINS_FILE, "r") as f:
            data = json.load(f)
            admins = data.get("admins", [])

            # Make sure we got a list back
            if not isinstance(admins, list):
                logger.error(
                    f"CONFIG_ERROR: Loaded admins is not a list: {type(admins)}"
                )
                return []

            logger.info(f"CONFIG: Loaded {len(admins)} admins from {ADMINS_FILE}")
            return admins
    except Exception as e:
        logger.error(f"CONFIG_ERROR: Failed to load admin list: {e}")
        return []


def save_personality_setting(personality_name: str, custom_settings: dict | None = None) -> bool:
    """
    Save current personality setting and any custom personality settings

    Args:
        personality_name: Current personality name (standard, mystic_dog, custom)
        custom_settings: Optional dictionary of custom personality settings

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data = {
            "current_personality": personality_name,
        }

        if custom_settings:
            data["custom_settings"] = custom_settings

        with open(PERSONALITY_FILE, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(
            f"CONFIG: Saved personality setting '{personality_name}' to {PERSONALITY_FILE}"
        )
        return True
    except Exception as e:
        logger.error(f"CONFIG_ERROR: Failed to save personality setting: {e}")
        return False


def load_personality_setting() -> tuple[str, dict | None]:
    """
    Load personality settings from file

    Returns:
        tuple: (personality_name, custom_settings), defaults if file doesn't exist
    """
    try:
        if not os.path.exists(PERSONALITY_FILE):
            logger.info(
                f"CONFIG: Personality file {PERSONALITY_FILE} not found, using defaults"
            )
            return "standard", None

        with open(PERSONALITY_FILE, "r") as f:
            data = json.load(f)
            personality = data.get("current_personality", "standard")
            custom_settings = data.get("custom_settings", None)

            logger.info(
                f"CONFIG: Loaded personality setting '{personality}' from {PERSONALITY_FILE}"
            )
            return personality, custom_settings
    except Exception as e:
        logger.error(f"CONFIG_ERROR: Failed to load personality setting: {e}")
        return "standard", None


def get_current_admins() -> list[str]:
    """Get the current admin list from file"""
    # Always load fresh from the file to ensure we have the latest
    return load_admins_from_file()
