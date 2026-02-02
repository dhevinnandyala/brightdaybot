from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from calendar import month_name

from config import DATE_FORMAT, DATE_WITH_YEAR_FORMAT, get_logger

logger = get_logger("date")


def extract_date(message: str) -> dict[str, str | int | None]:
    """
    Extract the first found date from a message

    Args:
        message: The message to extract a date from

    Returns:
        Dictionary with 'status', 'date', and optional 'year'
    """
    # Try to match date with year first (DD/MM/YYYY)
    year_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", message)
    if year_match:
        date_with_year = year_match.group(1)
        try:
            date_obj = datetime.strptime(date_with_year, DATE_WITH_YEAR_FORMAT)
            # Split into date and year
            date = date_obj.strftime(DATE_FORMAT)
            year = date_obj.year
            return {"status": "success", "date": date, "year": year}
        except ValueError:
            logger.error(f"DATE_ERROR: Invalid date format with year: {date_with_year}")
            return {"status": "invalid_date", "date": None, "year": None}

    # Try to match date without year (DD/MM)
    match = re.search(r"\b(\d{2}/\d{2})(?!/\d{4})\b", message)
    if not match:
        logger.debug(f"DATE_ERROR: No date pattern found in: {message}")
        return {"status": "no_date", "date": None, "year": None}

    date = match.group(1)
    try:
        datetime.strptime(date, DATE_FORMAT)
        return {"status": "success", "date": date, "year": None}
    except ValueError:
        logger.error(f"DATE_ERROR: Invalid date format: {date}")
        return {"status": "invalid_date", "date": None, "year": None}


def date_to_words(date: str, year: int | None = None) -> str:
    """
    Convert date in DD/MM to readable format, optionally including year

    Args:
        date: Date in DD/MM format
        year: Optional year to include

    Returns:
        Date in words (e.g., "5th of July" or "5th of July, 1990")
    """
    date_obj = datetime.strptime(date, DATE_FORMAT)

    day = date_obj.day
    if 11 <= day <= 13:
        day_str = f"{day}th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        day_str = f"{day}{suffix}"

    month = month_name[date_obj.month]

    if year:
        return f"{day_str} of {month}, {year}"
    return f"{day_str} of {month}"


def calculate_age(birth_year: int, birth_date: str | None = None) -> int:
    """
    Calculate age based on birth year, optionally accounting for month/day.

    Args:
        birth_year: Year of birth
        birth_date: Optional date in DD/MM format for precise age calculation

    Returns:
        Current age
    """
    today = datetime.now()
    age = today.year - birth_year
    if birth_date:
        try:
            day, month = map(int, birth_date.split("/"))
            if (today.month, today.day) < (month, day):
                age -= 1
        except (ValueError, IndexError):
            pass
    return age


def check_if_birthday_today(date_str: str, reference_date: datetime | None = None) -> bool:
    """
    Check if a date string in DD/MM format matches today's date

    Args:
        date_str: Date in DD/MM format
        reference_date: Optional reference date, defaults to today in UTC

    Returns:
        True if the date matches today's date, False otherwise
    """
    if not reference_date:
        reference_date = datetime.now(timezone.utc)

    day, month = map(int, date_str.split("/"))

    # Compare just the day and month
    return day == reference_date.day and month == reference_date.month


def calculate_days_until_birthday(date_str: str, reference_date: datetime | None = None) -> int:
    """
    Calculate days until a birthday

    Args:
        date_str: Date in DD/MM format
        reference_date: Optional reference date, defaults to today in UTC

    Returns:
        Number of days until the next birthday from reference date
    """
    if not reference_date:
        reference_date = datetime.now(timezone.utc)

    # Strip any time component for clean comparison
    reference_date = datetime(
        reference_date.year,
        reference_date.month,
        reference_date.day,
        tzinfo=timezone.utc,
    )

    day, month = map(int, date_str.split("/"))

    # First try this year's birthday
    try:
        birthday_date = datetime(reference_date.year, month, day, tzinfo=timezone.utc)

        # If birthday has already passed this year
        if birthday_date < reference_date:
            # Use next year's birthday
            birthday_date = datetime(
                reference_date.year + 1, month, day, tzinfo=timezone.utc
            )

        days_until = (birthday_date - reference_date).days
        return days_until

    except ValueError:
        # Handle invalid dates (like February 29 in non-leap years)
        # Default to next valid occurrence
        logger.warning(
            f"Invalid date {date_str} for current year, calculating next occurrence"
        )

        # Try next year if this year doesn't work
        next_year = reference_date.year + 1
        while True:
            try:
                birthday_date = datetime(next_year, month, day, tzinfo=timezone.utc)
                break
            except ValueError:
                next_year += 1

        days_until = (birthday_date - reference_date).days
        return days_until


def get_star_sign(date_str: str) -> str | None:
    """Get star sign from a date string in DD/MM format"""
    try:
        day, month = map(int, date_str.split("/"))

        # Simple date ranges for star signs
        if (month == 1 and day >= 20) or (month == 2 and day <= 18):
            return "Aquarius"
        elif (month == 2 and day >= 19) or (month == 3 and day <= 20):
            return "Pisces"
        elif (month == 3 and day >= 21) or (month == 4 and day <= 19):
            return "Aries"
        elif (month == 4 and day >= 20) or (month == 5 and day <= 20):
            return "Taurus"
        elif (month == 5 and day >= 21) or (month == 6 and day <= 20):
            return "Gemini"
        elif (month == 6 and day >= 21) or (month == 7 and day <= 22):
            return "Cancer"
        elif (month == 7 and day >= 23) or (month == 8 and day <= 22):
            return "Leo"
        elif (month == 8 and day >= 23) or (month == 9 and day <= 22):
            return "Virgo"
        elif (month == 9 and day >= 23) or (month == 10 and day <= 22):
            return "Libra"
        elif (month == 10 and day >= 23) or (month == 11 and day <= 21):
            return "Scorpio"
        elif (month == 11 and day >= 22) or (month == 12 and day <= 21):
            return "Sagittarius"
        else:  # (month == 12 and day >= 22) or (month == 1 and day <= 19)
            return "Capricorn"

    except Exception as e:
        logger.error(f"Failed to determine star sign: {e}")
        return None
