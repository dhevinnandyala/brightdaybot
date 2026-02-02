from datetime import datetime, timezone
from calendar import month_name

from utils.date_utils import date_to_words, calculate_age, calculate_days_until_birthday
from utils.storage import load_birthdays
from utils.slack_utils import (
    get_username,
    get_user_mention,
    check_command_permission,
    get_channel_members,
    is_admin,
)
from services.birthday import send_reminder_to_users
from config import BIRTHDAY_CHANNEL, get_logger

logger = get_logger("commands.list")


def handle_list_command(parts, user_id, say, app):
    """List upcoming or all birthdays"""
    # Check if this is "list all" command
    list_all = len(parts) > 1 and parts[1].lower() == "all"

    # List upcoming birthdays
    if not check_command_permission(app, user_id, "list"):
        say("You don't have permission to list birthdays")
        username = get_username(app, user_id)
        logger.warning(
            f"PERMISSIONS: {username} ({user_id}) attempted to use list command without permission"
        )
        return

    birthdays = load_birthdays()
    if not birthdays:
        say("No birthdays saved yet!")
        return

    # Use consistent UTC reference date for all calculations
    reference_date = datetime.now(timezone.utc)
    logger.info(
        f"LIST: Using reference date {reference_date.strftime('%Y-%m-%d')} (UTC)"
    )

    # Current UTC time display at the top
    current_utc = reference_date.strftime("%Y-%m-%d %H:%M:%S")

    # Convert to list for formatting
    birthday_list = []

    for uid, data in birthdays.items():
        bdate = data["date"]
        birth_year = data["year"]

        # For regular "list" we need days calculation
        days_until = None
        if not list_all:
            days_until = calculate_days_until_birthday(bdate, reference_date)

        username = get_username(app, uid)
        user_mention = get_user_mention(uid)

        # Parse the date components
        day, month = map(int, bdate.split("/"))

        age_text = ""
        if birth_year:
            # Calculate age they will be on their next birthday
            next_birthday_year = reference_date.year

            try:
                birthday_this_year = datetime(
                    next_birthday_year, month, day, tzinfo=timezone.utc
                )

                if birthday_this_year < reference_date:
                    next_birthday_year += 1

                next_age = next_birthday_year - birth_year
                age_text = f" (turning {next_age})"

            except ValueError:
                # Handle Feb 29 in non-leap years
                age_text = f" (age: {reference_date.year - birth_year})"

        # For "list all", sort by month and day
        sort_key = days_until if days_until is not None else (month * 100 + day)

        birthday_list.append(
            (
                uid,
                bdate,
                birth_year,
                username,
                sort_key,
                age_text,
                month,
                day,
                user_mention,
            )
        )

    # Sort appropriately
    if list_all:
        # For "list all", sort by month and day
        birthday_list.sort(key=lambda x: (x[6], x[7]))  # month, day
        title = f"📅 *All Birthdays:* (current UTC time: {current_utc})"
    else:
        # For regular list, sort by days until birthday
        birthday_list.sort(key=lambda x: x[4])
        title = f"📅 *Upcoming Birthdays:* (current UTC time: {current_utc})"

    # Format response
    response = f"{title}\n\n"

    # For list all, organize by month
    if list_all:
        current_month = None

        for (
            uid,
            bdate,
            birth_year,
            username,
            _,
            age_text,
            month,
            day,
            user_mention,
        ) in birthday_list:
            # Add month header if it's a new month
            if month != current_month:
                current_month = month
                month_name_str = month_name[month]
                response += f"\n*{month_name_str}*\n"

            # Format the date
            date_obj = datetime(
                2000, month, day
            )  # Using leap year for formatting
            day_str = date_obj.strftime("%d")

            # Format the year
            year_str = f" ({birth_year})" if birth_year else ""

            # Add the entry with user mention
            response += f"• {day_str}: {user_mention}{year_str}\n"
    else:
        # Standard "list" command - show next 10 birthdays with days until
        for (
            uid,
            bdate,
            birth_year,
            username,
            days,
            age_text,
            _,
            _,
            user_mention,
        ) in birthday_list[:10]:
            date_words = date_to_words(bdate)
            days_text = "Today! 🎉" if days == 0 else f"in {days} days"
            response += f"• {user_mention} ({date_words}{age_text}): {days_text}\n"

    say(response)
    logger.info(f"LIST: Generated birthday list for {len(birthday_list)} users")


def handle_stats_command(user_id, say, app):
    """Get birthday statistics"""
    if not check_command_permission(app, user_id, "stats"):
        say("You don't have permission to view stats")
        username = get_username(app, user_id)
        logger.warning(
            f"PERMISSIONS: {username} ({user_id}) attempted to use stats command without permission"
        )
        return

    birthdays = load_birthdays()
    total_birthdays = len(birthdays)

    # Calculate how many have years
    birthdays_with_years = sum(
        1 for data in birthdays.values() if data["year"] is not None
    )

    # Get channel members count
    channel_members = get_channel_members(app, BIRTHDAY_CHANNEL)
    total_members = len(channel_members)

    # Calculate coverage
    coverage_percentage = (
        (total_birthdays / total_members * 100) if total_members > 0 else 0
    )

    # Count birthdays by month
    months = [0] * 12
    for data in birthdays.values():
        try:
            month_idx = int(data["date"].split("/")[1]) - 1  # Convert from 1-12 to 0-11
            months[month_idx] += 1
        except (IndexError, ValueError):
            pass

    # Format month distribution
    month_names = [month_name[i][:3] for i in range(1, 13)]
    month_stats = []
    for i, count in enumerate(months):
        month_stats.append(f"{month_names[i]}: {count}")

    # Format response
    response = f"""📊 *Birthday Statistics*

• Total birthdays recorded: {total_birthdays}
• Channel members: {total_members}
• Coverage: {coverage_percentage:.1f}%
• Birthdays with year: {birthdays_with_years} ({birthdays_with_years/total_birthdays*100:.1f}% if recorded)

*Distribution by Month:*
{', '.join(month_stats)}

*Missing Birthdays:* {total_members - total_birthdays} members
"""
    say(response)


def handle_remind_command(parts, user_id, say, app):
    """Send reminders to users without birthdays"""
    if not check_command_permission(app, user_id, "remind"):
        say(
            "You don't have permission to send reminders. This command is restricted to admins."
        )
        username = get_username(app, user_id)
        logger.warning(
            f"PERMISSIONS: {username} ({user_id}) attempted to use remind command without permission"
        )
        return

    # Check if custom message is provided
    custom_message = " ".join(parts[1:]) if len(parts) > 1 else None

    # Get all users in the birthday channel
    channel_members = get_channel_members(app, BIRTHDAY_CHANNEL)
    if not channel_members:
        say("Could not retrieve channel members")
        return

    # Get users who already have birthdays
    birthdays = load_birthdays()
    users_with_birthdays = set(birthdays.keys())

    # Find users without birthdays
    users_missing_birthdays = [
        user for user in channel_members if user not in users_with_birthdays
    ]

    if not users_missing_birthdays:
        say(
            "Good news! All members of the birthday channel already have their birthdays saved. 🎉"
        )
        return

    # Send reminders to users without birthdays
    results = send_reminder_to_users(app, users_missing_birthdays, custom_message)

    # Prepare response message
    response_message = f"Reminder sent to {results['successful']} users"
    if results["failed"] > 0:
        response_message += f" (failed to send to {results['failed']} users)"
    if results["skipped_bots"] > 0:
        response_message += f" (skipped {results['skipped_bots']} bots)"

    say(response_message)
