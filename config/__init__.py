import os

# Re-export everything from sub-modules for backward compatibility.
# All existing `from config import X` statements continue to work.

from config.settings import (
    DATA_DIR,
    LOGS_DIR,
    STORAGE_DIR,
    TRACKING_DIR,
    BACKUP_DIR,
    MAX_BACKUPS,
    CACHE_DIR,
    WEB_SEARCH_CACHE_ENABLED,
    LOG_FILE,
    BIRTHDAYS_FILE,
    BIRTHDAY_CHANNEL,
    DATE_FORMAT,
    DATE_WITH_YEAR_FORMAT,
    DAILY_CHECK_TIME,
    DEFAULT_REMINDER_MESSAGE,
    DEFAULT_ADMIN_USERS,
    ADMIN_USERS,
    COMMAND_PERMISSIONS,
    username_cache,
    TEAM_NAME,
    BOT_NAME,
)

from config.logging_setup import (
    log_formatter,
    file_handler,
    root_logger,
    get_logger,
    logger,
)

from config.personalities import (
    BASE_TEMPLATE,
    BOT_PERSONALITIES,
    get_current_personality_name,
    set_current_personality,
    set_custom_personality_setting,
    get_full_template_for_personality,
)

# ----- CREATE DIRECTORY STRUCTURE -----

for directory in [DATA_DIR, LOGS_DIR, STORAGE_DIR, TRACKING_DIR, BACKUP_DIR, CACHE_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.info(f"CONFIG: Created directory {directory}")


def initialize_config():
    """Initialize configuration from storage files"""
    from config.settings import ADMIN_USERS, DEFAULT_ADMIN_USERS
    from config.personalities import _current_personality, BOT_PERSONALITIES

    # Import here to avoid circular imports
    from utils.config_storage import (
        load_admins_from_file,
        load_personality_setting,
        save_admins_to_file,
    )

    # Load admins
    admin_users_from_file = load_admins_from_file()

    if admin_users_from_file:
        ADMIN_USERS[:] = admin_users_from_file
        logger.info(f"CONFIG: Loaded {len(ADMIN_USERS)} admin users from file")
    else:
        # If no admins in file, use defaults but make sure to maintain any existing ones
        logger.info(f"CONFIG: No admins found in file, using default list")
        # Add any default admins that aren't already in the list
        for admin in DEFAULT_ADMIN_USERS:
            if admin not in ADMIN_USERS:
                ADMIN_USERS.append(admin)

        # Save the combined list to file
        save_admins_to_file(ADMIN_USERS)
        logger.info(f"CONFIG: Saved {len(ADMIN_USERS)} default admin users to file")

    # Add this debug print
    logger.info(f"CONFIG: ADMIN_USERS now contains: {ADMIN_USERS}")

    # Load personality settings
    personality_name, custom_settings = load_personality_setting()

    # Must mutate the module-level variable via the module
    import config.personalities as _personalities_mod
    _personalities_mod._current_personality = personality_name

    # If there are custom settings, apply them
    if custom_settings and isinstance(custom_settings, dict):
        for key, value in custom_settings.items():
            if key in BOT_PERSONALITIES["custom"]:
                BOT_PERSONALITIES["custom"][key] = value

    logger.info("CONFIG: Configuration initialized from storage files")
