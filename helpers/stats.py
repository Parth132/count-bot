import discord
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Any

from helpers.config import save_stats, save_daily_stats


def ensure_user_stats(stats: dict[str, Any], user_id: str, username: str):
    if user_id not in stats:
        stats[user_id] = {}

    user = stats[user_id]

    user.setdefault("username", username)
    user.setdefault("total_count", 0)
    user.setdefault("last_active_date", "")
    user.setdefault("last_active_day", "")
    user.setdefault("cur_streak", 0)
    user.setdefault("max_streak", 0)

    user["username"] = username
    return user


def check_permissions(roles, allowed_role_ids: list[int]) -> bool:
    for role in roles:
        if role.id in allowed_role_ids:
            return True
    return False


def cleanup_daily_stats(daily_stats: dict[str, Any], path=None) -> None:
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    keys_to_delete = []

    for key in daily_stats:
        day = datetime.strptime(key, "%d%m%Y").date()
        if (today - day).days > 30:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del daily_stats[key]

    save_daily_stats(daily_stats, path)


def build_daily_stats_embed(
    guild: discord.Guild,
    daily_stats: dict[str, Any],
    day: int = 0,
    count: int = 3,
):
    target_date = datetime.now(ZoneInfo("Asia/Kolkata")).date() - timedelta(days=day)
    key = target_date.strftime("%d%m%Y")

    if key not in daily_stats:
        return None

    data = daily_stats[key]

    embed = discord.Embed(
        title="📊 Daily Counting Statistics",
        description=f"Statistics for **{target_date.strftime('%d %b %Y')}**",
        color=discord.Color.blurple(),
    )

    embed.add_field(name="📈 Total Accepted Counts", value=f"**{data['total_accepted']:,}**", inline=True)
    embed.add_field(name="👥 Active Participants", value=f"**{len(data['users'])}**", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.add_field(name="🌱 New Participants", value=f"**{len(data['new_participants'])}**", inline=True)
    embed.add_field(name="🔄 Returning Counters", value=f"**{len(data['returning_users'])}**", inline=True)

    top_users = sorted(data["users"].items(), key=lambda x: x[1]["count"], reverse=True)[:count]
    medals = ["🥇", "🥈", "🥉"]
    leaderboard = ""

    for i, (user_id, info) in enumerate(top_users):
        member = guild.get_member(int(user_id))
        username = member.display_name if member else info["username"]
        medal = medals[i] if i < 3 else f"**#{i+1}**"
        leaderboard += f"{medal} {username}\n└ Accepted Counts: **{info['count']}**\n\n"

    if leaderboard == "":
        leaderboard = "No data available."

    embed.add_field(name="🏆 Daily Leaderboard", value=leaderboard, inline=False)
    embed.set_footer(text="Keep counting! 🚀")
    embed.timestamp = datetime.now(ZoneInfo("Asia/Kolkata"))
    return embed


def build_server_leaderboard(guild: discord.Guild, stats: dict[str, Any], count: int = 5):
    leaderboard = sorted(stats.items(), key=lambda x: x[1]["total_count"], reverse=True)[:count]

    embed = discord.Embed(
        title="🏆 Server Counting Leaderboard",
        description="Top members contributing to the counting game.",
        color=discord.Color.gold(),
    )

    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    leaderboard_text = ""

    for position, (user_id, data) in enumerate(leaderboard, start=1):
        member = guild.get_member(int(user_id))
        username = member.display_name if member else data["username"]
        data = ensure_user_stats(stats, user_id, username)

        rank = medals.get(position, f"`#{position}`")
        leaderboard_text += (
            f"{rank} **{username}**\n"
            f"> 📈 **Accepted Counts:** `{data['total_count']}`\n"
            f"> 🔥 **Current Streak:** `{data['cur_streak']}` days\n"
            f"> 🏆 **Best Streak:** `{data['max_streak']}` days\n"
            f"> 🕒 **Last Active:** {data['last_active_date']}\n\n"
        )

    embed.description = leaderboard_text

    total_counts = sum(user["total_count"] for user in stats.values())
    embed.set_footer(text=f"Tracking {len(stats)} members • {total_counts:,} accepted counts")
    embed.timestamp = datetime.now(ZoneInfo("Asia/Kolkata"))
    save_stats(stats)
    return embed


def build_daily_report_embed(guild: discord.Guild, daily_stats: dict[str, Any], day_offset: int = 1):
    yesterday = datetime.now(ZoneInfo("Asia/Kolkata")).date() - timedelta(days=day_offset)
    key = yesterday.strftime("%d%m%Y")

    if key not in daily_stats:
        return None

    day = daily_stats[key]

    top = sorted(day["users"].values(), key=lambda x: x["count"], reverse=True)[:3]

    embed = discord.Embed(
        title="📊 Daily Counting Report",
        description=f"Statistics for **{yesterday.strftime('%d %b %Y')}**",
        color=discord.Color.blurple(),
    )

    embed.add_field(name="📈 Total Accepted Counts", value=f"**{day['total_accepted']:,}**", inline=True)
    embed.add_field(name="👥 Active Participants", value=f"**{len(day['users'])}**", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.add_field(name="🌱 New Participants", value=f"**{len(day['new_participants'])}**", inline=True)
    embed.add_field(name="🔄 Returning Counters", value=f"**{len(day['returning_users'])}**", inline=True)

    leaderboard = ""
    medals = ["🥇", "🥈", "🥉"]

    for i, user in enumerate(top):
        leaderboard += f"{medals[i]} **{user['username']}** — `{user['count']}` counts\n"

    if leaderboard == "":
        leaderboard = "No counts yesterday."

    embed.add_field(name="🏆 Top Counters", value=leaderboard, inline=False)
    embed.set_footer(text="See you tomorrow for another recap! 🚀")
    embed.timestamp = datetime.now(ZoneInfo("Asia/Kolkata"))
    return embed
