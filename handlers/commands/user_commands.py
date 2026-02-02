from utils.date_utils import (
    extract_date,
    date_to_words,
    calculate_age,
    check_if_birthday_today,
)
from utils.storage import save_birthday, remove_birthday, load_birthdays
from utils.slack_utils import get_username, is_admin, send_message
from utils.message_generator import (
    completion,
    create_birthday_announcement,
    send_birthday_announcement,
)
from config import BIRTHDAY_CHANNEL, get_logger

logger = get_logger("commands.user")


def handle_dm_help(say):
    """Send help information for DM commands"""
    help_text = """
Here's how you can interact with me:

1. *Set your birthday:*
   • Send a date in DD/MM format (e.g., `25/12` for December 25th)
   • Or include the year: DD/MM/YYYY (e.g., `25/12/1990`)

2. *Commands:*
   • `add DD/MM` - Add or update your birthday
   • `add DD/MM/YYYY` - Add or update your birthday with year
   • `remove` - Remove your birthday
   • `help` - Show this help message
   • `check` - Check your saved birthday
   • `check @user` - Check someone else's birthday
   • `test` - See a test birthday message for yourself

Admin commands are also available. Type `admin help` for more information.
"""
    say(help_text)
    logger.info("HELP: Sent DM help information")


def handle_dm_admin_help(say, user_id, app):
    """Send admin help information"""
    if not is_admin(app, user_id):
        say("You don't have permission to view admin commands.")
        return

    admin_help = """
*Admin Commands:*

• `admin list` - List configured admin users
• `admin add USER_ID` - Add a user as admin
• `admin remove USER_ID` - Remove a user from admin list

• `list` - List upcoming birthdays
• `list all` - List all birthdays organized by month
• `stats` - View birthday statistics
• `remind [message]` - Send reminders to users without birthdays

• `admin status` - View system health and component status
• `admin status detailed` - View detailed system information

• `config` - View command permissions
• `config COMMAND true/false` - Change command permissions

*Data Management:*
• `admin backup` - Create a manual backup of birthdays data
• `admin restore latest` - Restore from the latest backup
• `admin cache clear` - Clear all web search cache
• `admin cache clear DD/MM` - Clear web search cache for a specific date

*Bot Personality:*
• `admin personality` - Show current bot personality
• `admin personality [name]` - Change bot personality
  Available options: standard, mystic_dog, custom

*Custom Personality:*
• `admin custom name [value]` - Set custom bot name
• `admin custom description [value]` - Set custom bot description
• `admin custom style [value]` - Set custom writing style
• `admin custom format [value]` - Set custom format instruction
• `admin custom template [value]` - Set custom template extension
"""
    say(admin_help)
    logger.info(f"HELP: Sent admin help to {user_id}")


def handle_dm_date(say, user, result, app):
    """Handle a date sent in a DM"""
    date = result["date"]
    year = result["year"]

    # Format birthday information for response
    if year:
        date_words = date_to_words(date, year)
        age = calculate_age(year)
        age_text = f" (Age: {age})"
    else:
        date_words = date_to_words(date)
        age_text = ""

    updated = save_birthday(date, user, year, get_username(app, user))

    # Check if birthday is today and send announcement if so
    if check_if_birthday_today(date):
        say(
            f"It's your birthday today! {date_words}{age_text} - I'll send an announcement to the birthday channel right away!"
        )
        username = get_username(app, user)
        send_birthday_announcement(app, BIRTHDAY_CHANNEL, username, user, date, date_words, year)
    else:
        if updated:
            say(
                f"Birthday updated to {date_words}{age_text}. If this is incorrect, please try again with the correct date."
            )
        else:
            say(
                f"{date_words}{age_text} has been saved as your birthday. If this is incorrect, please try again."
            )


def handle_add_command(parts, user_id, say, app):
    """Handle the add birthday command"""
    date_text = " ".join(parts[1:])
    result = extract_date(date_text)
    username = get_username(app, user_id)

    if result["status"] == "no_date":
        say("No date found. Please use format: `add DD/MM` or `add DD/MM/YYYY`")
        return

    if result["status"] == "invalid_date":
        say("Invalid date. Please use format: `add DD/MM` or `add DD/MM/YYYY`")
        return

    date = result["date"]
    year = result["year"]

    updated = save_birthday(date, user_id, year, username)

    if year:
        date_words = date_to_words(date, year)
        age = calculate_age(year)
        age_text = f" (Age: {age})"
    else:
        date_words = date_to_words(date)
        age_text = ""

    # Check if birthday is today and send announcement if so
    if check_if_birthday_today(date):
        say(
            f"It's your birthday today! {date_words}{age_text} - I'll send an announcement to the birthday channel right away!"
        )
        send_birthday_announcement(app, BIRTHDAY_CHANNEL, username, user_id, date, date_words, year)
    else:
        if updated:
            say(f"Your birthday has been updated to {date_words}{age_text}")
        else:
            say(f"Your birthday ({date_words}{age_text}) has been saved!")


def handle_remove_command(user_id, say, app):
    """Handle the remove birthday command"""
    username = get_username(app, user_id)
    removed = remove_birthday(user_id, username)
    if removed:
        say("Your birthday has been removed from our records")
    else:
        say("You don't have a birthday saved in our records")


def handle_check_command(parts, user_id, say, app):
    """Check a specific user's birthday or your own"""
    target_user = parts[1].strip("<@>") if len(parts) > 1 else user_id
    target_user = target_user.upper()

    birthdays = load_birthdays()
    if target_user in birthdays:
        data = birthdays[target_user]
        date = data["date"]
        year = data["year"]

        if year:
            date_words = date_to_words(date, year)
            age = calculate_age(year)
            age_text = f" (Age: {age})"
        else:
            date_words = date_to_words(date)
            age_text = ""

        if target_user == user_id:
            say(f"Your birthday is set to {date_words}{age_text}")
        else:
            target_username = get_username(app, target_user)
            say(f"{target_username}'s birthday is {date_words}{age_text}")
    else:
        if target_user == user_id:
            say(
                "You don't have a birthday saved. Use `add DD/MM` or `add DD/MM/YYYY` to save it."
            )
        else:
            target_username = get_username(app, target_user)
            say(f"{target_username} doesn't have a birthday saved.")


def handle_test_command(user_id, say, app):
    """Generate a test birthday message for the user"""
    birthdays = load_birthdays()
    from datetime import datetime

    today = datetime.now()
    date_str = today.strftime("%d/%m")
    birth_year = birthdays.get(user_id, {}).get("year")
    username = get_username(app, user_id)

    try:
        # First try to get the user's actual birthday if available
        if user_id in birthdays:
            user_date = birthdays[user_id]["date"]
            birth_year = birthdays[user_id]["year"]
            date_words = date_to_words(user_date, birth_year)
        else:
            # If no birthday is saved, use today's date
            user_date = date_str
            date_words = "today"

        say(f"Generating a test birthday message for you... this might take a moment.")

        # Try to get personalized AI message
        test_message = completion(username, date_words, user_id, user_date, birth_year)

        say(f"Here's what your birthday message would look like:\n\n{test_message}")
        logger.info(f"TEST: Generated test birthday message for {username} ({user_id})")

    except Exception as e:
        logger.error(f"AI_ERROR: Failed to generate test message: {e}")

        # Fallback to announcement
        say(
            "I couldn't generate a custom message, but here's a template of what your birthday message would look like:"
        )

        # Create a test announcement using the user's data or today's date
        announcement = create_birthday_announcement(
            user_id,
            username,
            user_date if user_id in birthdays else date_str,
            birth_year,
        )

        say(announcement)
