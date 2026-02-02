from __future__ import annotations

from datetime import datetime, timezone

from utils.date_utils import check_if_birthday_today, date_to_words, get_star_sign
from utils.storage import (
    load_birthdays,
    get_announced_birthdays_today,
    mark_birthday_announced,
    cleanup_old_announcement_files,
)
from utils.slack_utils import get_username, send_message, get_user_mention
from utils.message_generator import send_birthday_announcement
from config import BIRTHDAY_CHANNEL, get_logger

logger = get_logger("birthday")


def send_reminder_to_users(app: object, users: list[str], custom_message: str | None = None) -> dict:
    """
    Send reminder message to multiple users

    Args:
        app: Slack app instance
        users: List of user IDs
        custom_message: Optional custom message provided by admin

    Returns:
        Dictionary with successful and failed sends
    """
    results = {"successful": 0, "failed": 0, "skipped_bots": 0, "users": []}

    logger.info(f"REMINDER: Starting to send {len(users)} reminders")

    for user_id in users:
        # Skip bots
        try:
            user_info = app.client.users_info(user=user_id)
            if user_info.get("user", {}).get("is_bot", False):
                results["skipped_bots"] += 1
                continue
        except Exception as e:
            logger.error(f"API_ERROR: Failed to check if {user_id} is a bot: {e}")
            # Assume not a bot and try to send anyway

        # Get username for personalization
        username = get_username(app, user_id)

        # Create lively personalized message if no custom message provided
        if not custom_message:
            # Pick random elements for variety
            import random

            greetings = [
                f"Hey there {get_user_mention(user_id)}! :wave:",
                f"Hello {get_user_mention(user_id)}! :sunny:",
                f"Greetings, {get_user_mention(user_id)}! :sparkles:",
                f"Hi {get_user_mention(user_id)}! :smile:",
                f"*Psst* {get_user_mention(user_id)}! :eyes:",
            ]

            intros = [
                "Looks like we don't have your birthday on record yet!",
                "I noticed your birthday isn't in our celebration calendar!",
                "We're missing an important date - YOUR birthday!",
                "The birthday list has a person-shaped hole that looks just like you!",
                "Our birthday celebration squad is missing some info about you!",
            ]

            reasons = [
                "We'd love to celebrate your special day with you! :birthday:",
                "We want to make sure your day gets the celebration it deserves! :tada:",
                "Everyone deserves a little birthday recognition! :cake:",
                "Our team celebrations wouldn't be complete without yours! :gift:",
                "We don't want to miss the chance to celebrate you! :confetti_ball:",
            ]

            instructions = [
                "Just send me your birthday in DD/MM format (like `14/02`), or include the year with DD/MM/YYYY (like `14/02/1990`).",
                "Simply reply with your birthday as DD/MM (example: `25/12`) or with the year DD/MM/YYYY (example: `25/12/1990`).",
                "Drop me a quick message with your birthday in DD/MM format (like `31/10`) or with the year DD/MM/YYYY (like `31/10/1985`).",
                "Just type your birthday as DD/MM (like `01/04`) or include the year with DD/MM/YYYY (like `01/04/1988`).",
                "Send your birthday as DD/MM (example: `19/07`) or with the year if you'd like DD/MM/YYYY (example: `19/07/1995`).",
            ]

            outros = [
                "Thanks! :star:",
                "Can't wait to celebrate with you! :raised_hands:",
                "Looking forward to it! :sparkles:",
                "Your birthday will be awesome! :rocket:",
                "Thanks for helping us make our workplace more fun! :party-blob:",
            ]

            message = (
                f"{random.choice(greetings)}\n\n"
                f"{random.choice(intros)} {random.choice(reasons)}\n\n"
                f"{random.choice(instructions)}\n\n"
                f"{random.choice(outros)}"
            )
        else:
            # Use custom message but ensure it includes the user's mention
            if f"{get_user_mention(user_id)}" not in custom_message:
                message = f"{get_user_mention(user_id)}, {custom_message}"
            else:
                message = custom_message

        # Send the message
        sent = send_message(app, user_id, message)
        if sent:
            results["successful"] += 1
            results["users"].append(user_id)
            logger.info(f"REMINDER: Sent to {username} ({user_id})")
        else:
            results["failed"] += 1

    logger.info(
        f"REMINDER: Completed sending reminders - {results['successful']} successful, {results['failed']} failed, {results['skipped_bots']} bots skipped"
    )
    return results


def daily(app: object, moment: datetime) -> int:
    """
    Run daily tasks like birthday messages

    Args:
        app: Slack app instance
        moment: Current datetime with timezone info
    """
    # Ensure moment has timezone info
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)

    logger.info(
        f"DAILY: Running birthday checks for {moment.strftime('%Y-%m-%d')} (UTC)"
    )
    birthdays = load_birthdays()

    # Clean up old announcement files
    cleanup_old_announcement_files()

    # Get already announced birthdays
    already_announced = get_announced_birthdays_today()

    birthday_count = 0
    for user_id, birthday_data in birthdays.items():
        # Skip if already announced today
        if user_id in already_announced:
            logger.info(f"BIRTHDAY: Skipping already announced birthday for {user_id}")
            birthday_count += 1
            continue

        # Use our accurate date checking function instead of string comparison
        if check_if_birthday_today(birthday_data["date"], moment):
            username = get_username(app, user_id)
            logger.info(f"BIRTHDAY: Today is {username}'s ({user_id}) birthday!")
            birthday_count += 1

            date_words = date_to_words(
                birthday_data["date"], birthday_data.get("year")
            )
            send_birthday_announcement(
                app,
                BIRTHDAY_CHANNEL,
                username,
                user_id,
                birthday_data["date"],
                date_words,
                birthday_data.get("year"),
            )
            mark_birthday_announced(user_id)

    if birthday_count == 0:
        logger.info("DAILY: No birthdays today")

    return birthday_count
