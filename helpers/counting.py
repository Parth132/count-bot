from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any

from helpers.config import save_daily_stats, save_stats, save_state
from helpers.stats import ensure_user_stats


def update_count_state_and_stats(
    message,
    state: dict[str, Any],
    stats: dict[str, Any],
    daily_stats: dict[str, Any],
) -> int:
    number = int(message.content.strip())

    state["last_number"] = number
    state["last_user_id"] = message.author.id
    save_state(state)

    user_id = str(message.author.id)
    is_new_user = user_id not in stats

    user = ensure_user_stats(stats, user_id, message.author.display_name)

    today_date = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    today_str = today_date.isoformat()
    today_key = today_date.strftime("%d%m%Y")

    if today_key not in daily_stats:
        daily_stats[today_key] = {
            "total_accepted": 0,
            "new_participants": [],
            "returning_users": [],
            "users": {},
        }

    today_stats = daily_stats[today_key]
    today_stats["total_accepted"] += 1

    if user_id not in today_stats["users"]:
        today_stats["users"][user_id] = {
            "username": message.author.display_name,
            "count": 0,
        }

    today_stats["users"][user_id]["username"] = message.author.display_name
    today_stats["users"][user_id]["count"] += 1

    if is_new_user and user_id not in today_stats["new_participants"]:
        today_stats["new_participants"].append(user_id)

    user["total_count"] += 1

    last_day = user["last_active_day"]
    if last_day:
        last_day = datetime.strptime(last_day, "%Y-%m-%d").date()

        if today_date == last_day:
            pass
        elif today_date == last_day + timedelta(days=1):
            user["cur_streak"] += 1
        else:
            if user_id not in today_stats["returning_users"]:
                today_stats["returning_users"].append(user_id)

            user["max_streak"] = max(user["max_streak"], user["cur_streak"])
            user["cur_streak"] = 1
    else:
        user["cur_streak"] = 1

    user["max_streak"] = max(user["max_streak"], user["cur_streak"])
    user["last_active_day"] = today_str
    user["last_active_date"] = (
        datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %I:%M %p")
    )

    save_stats(stats)
    save_daily_stats(daily_stats)
    return number
