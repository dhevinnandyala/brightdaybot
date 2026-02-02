from utils.slack_utils import get_username, is_admin
from config import get_logger

from handlers.commands.user_commands import (
    handle_dm_help,
    handle_dm_admin_help,
    handle_dm_date,
    handle_add_command,
    handle_remove_command,
    handle_check_command,
    handle_test_command,
)
from handlers.commands.admin_commands import handle_admin_command
from handlers.commands.list_commands import (
    handle_list_command,
    handle_stats_command,
    handle_remind_command,
)
from handlers.commands.config_commands import handle_config_command

logger = get_logger("commands")


def handle_command(text, user_id, say, app):
    """Process commands sent as direct messages"""
    parts = text.strip().lower().split()
    command = parts[0] if parts else "help"
    username = get_username(app, user_id)

    logger.info(f"COMMAND: {username} ({user_id}) used DM command: {text}")

    if command == "help":
        handle_dm_help(say)
        return

    if command == "admin" and len(parts) > 1:
        admin_subcommand = parts[1]

        if admin_subcommand == "help":
            handle_dm_admin_help(say, user_id, app)
            return

        if not is_admin(app, user_id):
            say("You don't have permission to use admin commands")
            logger.warning(
                f"PERMISSIONS: {username} ({user_id}) attempted to use admin command without permission"
            )
            return

        handle_admin_command(admin_subcommand, parts[2:], say, user_id, app)
        return

    if command == "add" and len(parts) >= 2:
        handle_add_command(parts, user_id, say, app)
    elif command == "remove":
        handle_remove_command(user_id, say, app)
    elif command == "list":
        handle_list_command(parts, user_id, say, app)
    elif command == "check":
        handle_check_command(parts, user_id, say, app)
    elif command == "remind":
        handle_remind_command(parts, user_id, say, app)
    elif command == "stats":
        handle_stats_command(user_id, say, app)
    elif command == "config":
        handle_config_command(parts, user_id, say, app)
    elif command == "test":
        handle_test_command(user_id, say, app)
    else:
        handle_dm_help(say)
