from utils.slack_utils import get_username, get_user_mention, is_admin
from utils.storage import create_backup, restore_latest_backup
from utils.message_generator import get_current_personality
from utils.health_check import get_status_summary, get_system_status
from utils.web_search import clear_cache
from utils.config_storage import save_admins_to_file
from config import (
    ADMIN_USERS,
    BOT_PERSONALITIES,
    get_current_personality_name,
    set_current_personality,
    DATA_DIR,
    STORAGE_DIR,
    CACHE_DIR,
    BIRTHDAYS_FILE,
    get_logger,
)

logger = get_logger("commands.admin")


def handle_admin_command(subcommand, args, say, user_id, app):
    """Handle admin-specific commands"""
    username = get_username(app, user_id)

    if subcommand == "list":
        _handle_admin_list(say, app)
    elif subcommand == "add" and args:
        _handle_admin_add(args, say, user_id, username, app)
    elif subcommand == "remove" and args:
        _handle_admin_remove(args, say, user_id, username, app)
    elif subcommand == "backup":
        create_backup()
        say("Manual backup of birthdays file created successfully.")
        logger.info(f"ADMIN: {username} ({user_id}) triggered manual backup")
    elif subcommand == "restore":
        if args and args[0] == "latest":
            if restore_latest_backup():
                say("Successfully restored from the latest backup")
            else:
                say("Failed to restore. No backups found or restore failed.")
        else:
            say("Use `admin restore latest` to restore from the most recent backup.")
    elif subcommand == "personality":
        _handle_personality(args, say, user_id, username)
    elif subcommand == "cache":
        handle_cache_command(args, user_id, say, app)
    elif subcommand == "status":
        is_detailed = len(args) > 0 and args[0].lower() == "detailed"
        handle_status_command(
            [None, "detailed" if is_detailed else None], user_id, say, app
        )
        logger.info(
            f"ADMIN: {username} ({user_id}) requested system status {'with details' if is_detailed else ''}"
        )
    else:
        say(
            "Unknown admin command. Use `admin help` for information on admin commands."
        )


def _handle_admin_list(say, app):
    """List all configured admin users"""
    from utils.config_storage import get_current_admins

    current_admins = get_current_admins()
    logger.info(
        f"ADMIN_LIST: Current admin list has {len(current_admins)} users: {current_admins}"
    )

    if not current_admins:
        say("No additional admin users configured.")
        return

    admin_list = []
    for admin_id in current_admins:
        try:
            admin_name = get_username(app, admin_id)
            admin_list.append(f"• {admin_name} ({admin_id})")
        except Exception as e:
            logger.error(f"ERROR: Failed to get username for admin {admin_id}: {e}")
            admin_list.append(f"• {admin_id} (name unavailable)")

    say(f"*Configured Admin Users:*\n\n" + "\n".join(admin_list))


def _handle_admin_add(args, say, user_id, username, app):
    """Add a new admin user"""
    new_admin = args[0].strip("<@>").upper()

    # Validate user exists
    try:
        user_info = app.client.users_info(user=new_admin)
        if not user_info.get("ok", False):
            say(f"User ID `{new_admin}` not found.")
            return
    except Exception:
        say(f"User ID `{new_admin}` not found or invalid.")
        return

    # Get the current list from the file
    from utils.config_storage import load_admins_from_file

    current_admins = load_admins_from_file()

    if new_admin in current_admins:
        say(f"User {get_user_mention(new_admin)} is already an admin.")
        return

    # Add to the list from the file
    current_admins.append(new_admin)

    # Save the combined list
    if save_admins_to_file(current_admins):
        # Update in-memory list too
        ADMIN_USERS[:] = current_admins

        new_admin_name = get_username(app, new_admin)
        say(f"Added {new_admin_name} ({get_user_mention(new_admin)}) as admin")
        logger.info(
            f"ADMIN: {username} ({user_id}) added {new_admin_name} ({new_admin}) as admin"
        )
    else:
        say(
            f"Failed to add {get_user_mention(new_admin)} as admin due to an error saving to file."
        )


def _handle_admin_remove(args, say, user_id, username, app):
    """Remove an admin user"""
    admin_to_remove = args[0].strip("<@>").upper()

    from utils.config_storage import load_admins_from_file

    current_admins = load_admins_from_file()

    if admin_to_remove not in current_admins:
        say(f"User {get_user_mention(admin_to_remove)} is not in the admin list.")
        return

    # Remove from the list
    current_admins.remove(admin_to_remove)

    # Save the updated list
    if save_admins_to_file(current_admins):
        # Update in-memory list too
        ADMIN_USERS[:] = current_admins

        removed_name = get_username(app, admin_to_remove)
        say(
            f"Removed {removed_name} ({get_user_mention(admin_to_remove)}) from admin list"
        )
        logger.info(
            f"ADMIN: {username} ({user_id}) removed {removed_name} ({admin_to_remove}) from admin list"
        )
    else:
        say(
            f"Failed to remove {get_user_mention(admin_to_remove)} due to an error saving to file."
        )


def _handle_personality(args, say, user_id, username):
    """Handle personality sub-commands"""
    if not args:
        # Display current personality
        current = get_current_personality_name()
        personalities = ", ".join([f"`{p}`" for p in BOT_PERSONALITIES.keys()])
        say(
            f"Current bot personality: `{current}`\nAvailable personalities: {personalities}\n\nUse `admin personality [name]` to change."
        )
    else:
        # Set new personality
        new_personality = args[0].lower()
        if new_personality not in BOT_PERSONALITIES:
            say(
                f"Unknown personality: `{new_personality}`. Available options: {', '.join(BOT_PERSONALITIES.keys())}"
            )
            return

        if set_current_personality(new_personality):
            personality = get_current_personality()
            say(
                f"Bot personality changed to `{new_personality}`: {personality['name']}, {personality['description']}"
            )
            logger.info(
                f"ADMIN: {username} ({user_id}) changed bot personality to {new_personality}"
            )
        else:
            say(f"Failed to change personality to {new_personality}")


def handle_cache_command(parts, user_id, say, app):
    """Handle cache management commands"""
    username = get_username(app, user_id)

    if len(parts) < 2:
        say(
            "Usage: `admin cache clear [date]` - Clear cache (optionally for specific date)"
        )
        return

    if parts[1] != "clear":
        say("Unknown cache command. Available commands: `clear`")
        return

    # Check if a specific date was provided
    specific_date = None
    if len(parts) >= 3:
        try:
            if "/" in parts[2]:
                specific_date = parts[2]
        except (ValueError, IndexError):
            say("Invalid date format. Please use DD/MM format (e.g., 25/12)")
            return

    # Clear the cache
    count = clear_cache(specific_date)

    if specific_date:
        say(f"✅ Cleared web search cache for date: {specific_date}")
    else:
        say(f"✅ Cleared all web search cache ({count} files)")

    logger.info(
        f"ADMIN: {username} ({user_id}) cleared {'date-specific ' if specific_date else ''}web search cache"
    )


def handle_status_command(parts, user_id, say, app):
    """Handler for the status command"""
    username = get_username(app, user_id)
    summary = get_status_summary()

    # Check if the user wants detailed information
    is_detailed = len(parts) > 1 and parts[1] == "detailed"

    if is_detailed:
        # Add detailed information for advanced users
        status = get_system_status()

        # Add system paths
        detailed_info = [
            "\n*System Paths:*",
            f"• Data Directory: `{DATA_DIR}`",
            f"• Storage Directory: `{STORAGE_DIR}`",
            f"• Birthdays File: `{BIRTHDAYS_FILE}`",
            f"• Cache Directory: `{CACHE_DIR}`",
        ]

        # Add cache statistics if available
        if (
            status["components"]["cache"]["status"] == "ok"
            and status["components"]["cache"].get("file_count", 0) > 0
        ):
            detailed_info.extend(
                [
                    "\n*Cache Details:*",
                    f"• Total Files: {status['components']['cache']['file_count']}",
                    f"• Oldest Cache: {status['components']['cache'].get('oldest_cache', {}).get('file', 'N/A')} ({status['components']['cache'].get('oldest_cache', {}).get('date', 'N/A')})",
                    f"• Newest Cache: {status['components']['cache'].get('newest_cache', {}).get('file', 'N/A')} ({status['components']['cache'].get('newest_cache', {}).get('date', 'N/A')})",
                ]
            )

        summary += "\n" + "\n".join(detailed_info)

    say(summary)
    logger.info(
        f"STATUS: {username} ({user_id}) requested system status {'with details' if is_detailed else ''}"
    )
