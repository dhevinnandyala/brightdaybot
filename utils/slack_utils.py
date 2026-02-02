from __future__ import annotations

from slack_sdk.errors import SlackApiError

from config import username_cache, ADMIN_USERS, COMMAND_PERMISSIONS, get_logger

logger = get_logger("slack")


def get_username(app: object, user_id: str) -> str:
    """
    Get user's display name from their ID, with caching

    Args:
        app: Slack app instance
        user_id: User ID to look up

    Returns:
        Display name or formatted mention
    """
    # Check cache first
    if user_id in username_cache:
        return username_cache[user_id]

    try:
        response = app.client.users_profile_get(user=user_id)
        if response["ok"]:
            display_name = response["profile"]["display_name"]
            real_name = response["profile"]["real_name"]
            username = display_name if display_name else real_name
            # Cache the result
            username_cache[user_id] = username
            return username
        logger.error(f"API_ERROR: Failed to get profile for user {user_id}")
    except SlackApiError as e:
        logger.error(f"API_ERROR: Slack error when getting profile for {user_id}: {e}")

    # Fallback to mention format
    return f"{get_user_mention(user_id)}"


def get_user_mention(user_id: str) -> str:
    """
    Get a formatted mention for a user

    Args:
        user_id: User ID to format

    Returns:
        Formatted mention string
    """
    return f"<@{user_id}>" if user_id else "Unknown User"


def is_admin(app: object, user_id: str) -> bool:
    """
    Check if user is an admin (workspace admin or in ADMIN_USERS list).

    Uses the in-memory ADMIN_USERS list (kept in sync by admin add/remove
    commands) instead of reading from disk on every call.

    Args:
        app: Slack app instance
        user_id: User ID to check

    Returns:
        True if user is admin, False otherwise
    """
    # First, check if user is in the in-memory admin list
    if user_id in ADMIN_USERS:
        logger.debug(
            f"PERMISSIONS: {user_id} is admin via ADMIN_USERS list"
        )
        return True

    # Then check if they're a workspace admin
    try:
        user_info = app.client.users_info(user=user_id)
        is_workspace_admin = user_info.get("user", {}).get("is_admin", False)

        if is_workspace_admin:
            logger.debug(
                f"PERMISSIONS: {user_id} is admin via workspace permissions"
            )

        return is_workspace_admin
    except SlackApiError as e:
        logger.error(f"API_ERROR: Failed to check admin status for {user_id}: {e}")
        return False


def check_command_permission(app: object, user_id: str, command: str) -> bool:
    """
    Check if a user has permission to use a specific command

    Args:
        app: Slack app instance
        user_id: User ID to check
        command: The command to check permissions for

    Returns:
        True if user has permission, False otherwise
    """
    # Remind command always requires admin
    if command == "remind":
        return is_admin(app, user_id)

    # For other commands, check the permission settings
    if command in COMMAND_PERMISSIONS and COMMAND_PERMISSIONS[command]:
        return is_admin(app, user_id)

    # Commands not in the permission settings are available to all users
    return True


def get_channel_members(app: object, channel_id: str) -> list[str]:
    """
    Get all members of a channel with pagination support

    Args:
        app: Slack app instance
        channel_id: Channel ID to check

    Returns:
        List of user IDs
    """
    members = []
    next_cursor = None

    try:
        while True:
            # Make API call with cursor if we have one
            if next_cursor:
                result = app.client.conversations_members(
                    channel=channel_id, cursor=next_cursor, limit=1000
                )
            else:
                result = app.client.conversations_members(
                    channel=channel_id, limit=1000
                )

            # Add members from this page
            if result.get("members"):
                members.extend(result["members"])

            # Check if we need to fetch more pages
            next_cursor = result.get("response_metadata", {}).get("next_cursor")
            if not next_cursor:
                break

        logger.info(
            f"CHANNEL: Retrieved {len(members)} members from channel {channel_id}"
        )
        return members

    except SlackApiError as e:
        logger.error(f"API_ERROR: Failed to get channel members: {e}")
        return []


def send_message(app: object, channel: str, text: str, blocks: list | None = None) -> bool:
    """
    Send a message to a Slack channel with error handling

    Args:
        app: Slack app instance
        channel: Channel ID
        text: Message text
        blocks: Optional blocks for rich formatting

    Returns:
        True if successful, False otherwise
    """
    try:
        if blocks:
            app.client.chat_postMessage(channel=channel, text=text, blocks=blocks)
        else:
            app.client.chat_postMessage(channel=channel, text=text)

        # Log different messages based on whether this is a DM or channel
        if channel.startswith("U"):
            recipient = get_username(app, channel)
            logger.info(f"MESSAGE: Sent DM to {recipient} ({channel})")
        else:
            logger.info(f"MESSAGE: Sent message to channel {channel}")

        return True
    except SlackApiError as e:
        logger.error(f"API_ERROR: Failed to send message to {channel}: {e}")
        return False


# Common Slack emojis that are safe to use
SAFE_SLACK_EMOJIS = [
    ":tada:",
    ":birthday:",
    ":cake:",
    ":balloon:",
    ":gift:",
    ":confetti_ball:",
    ":sparkles:",
    ":star:",
    ":star2:",
    ":dizzy:",
    ":heart:",
    ":hearts:",
    ":champagne:",
    ":clap:",
    ":raised_hands:",
    ":thumbsup:",
    ":muscle:",
    ":crown:",
    ":trophy:",
    ":medal:",
    ":first_place_medal:",
    ":mega:",
    ":loudspeaker:",
    ":partying_face:",
    ":smile:",
    ":grinning:",
    ":joy:",
    ":sunglasses:",
    ":rainbow:",
    ":fire:",
    ":boom:",
    ":zap:",
    ":bulb:",
    ":art:",
    ":musical_note:",
    ":notes:",
    ":rocket:",
    ":100:",
    ":pizza:",
    ":hamburger:",
    ":sushi:",
    ":ice_cream:",
    ":beers:",
    ":cocktail:",
    ":wine_glass:",
    ":tumbler_glass:",
    ":drum_with_drumsticks:",
    ":guitar:",
    ":microphone:",
    ":headphones:",
    ":game_die:",
    ":dart:",
    ":bowling:",
    ":soccer:",
    ":basketball:",
    ":football:",
    ":baseball:",
    ":tennis:",
    ":8ball:",
    ":table_tennis_paddle_and_ball:",
    ":eyes:",
    ":wave:",
    ":point_up:",
    ":point_down:",
    ":point_left:",
    ":point_right:",
    ":ok_hand:",
    ":v:",
    ":handshake:",
    ":writing_hand:",
    ":pray:",
    ":clinking_glasses:",
]
