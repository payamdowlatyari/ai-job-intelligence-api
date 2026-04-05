from datetime import datetime, timedelta
import re


def parse_relative_time(value: str) -> datetime:
    """Convert '3 days ago' → datetime."""
    if not value:
        return None

    value = value.lower().strip()

    match = re.search(
        r"(\d+)\s+(minute|minutes|hour|hours|day|days|week|weeks|month|months)",
        value,
    )
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    now = datetime.utcnow()

    if "minute" in unit:
        return now - timedelta(minutes=amount)
    elif "hour" in unit:
        return now - timedelta(hours=amount)
    elif "day" in unit:
        return now - timedelta(days=amount)
    elif "week" in unit:
        return now - timedelta(weeks=amount)
    elif "month" in unit:
        return now - timedelta(days=30 * amount)

    return None