import discord
from discord import app_commands
import json
import os
import time
from dotenv import load_dotenv
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Literal

load_dotenv()
TOKEN = os.getenv("TOKEN")

CONFIG_FILE = "config.json"
STATE_FILE = "count_state.json"
STAT_FILE = "stat_count.json"

ALLOWED_ROLE_ID = 1377336728100012102

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ----------------------------
# Config
# ----------------------------

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            "counting_channel_id": 0
        }

    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


# ----------------------------
# State
# ----------------------------

def load_state():
    if not os.path.exists(STATE_FILE):
        return {
            "last_number": 0,
            "last_user_id": None
        }

    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def load_stats():
    if not os.path.exists(STAT_FILE):
        return {}

    with open(STAT_FILE, "r") as f:
        return json.load(f)


def save_stats():
    with open(STAT_FILE, "w") as f:
        json.dump(stats, f, indent=4)


stats = load_stats()


config = load_config()
state = load_state()


# ---------------------------
# Helper Functions
# ---------------------------

def ensure_user_stats(user_id: str, username: str):
    if user_id not in stats:
        stats[user_id] = {}

    user = stats[user_id]

    # Backwards compatibility
    user.setdefault("username", username)
    user.setdefault("total_count", 0)
    user.setdefault("last_active_date", "")
    user.setdefault("last_active_day", "")
    user.setdefault("cur_streak", 1)
    user.setdefault("max_streak", 1)

    # Always keep username up to date
    user["username"] = username

    return user

# ----------------------------
# Startup
# ----------------------------

@client.event
async def on_ready():
    await tree.sync()

    print(f"Logged in as {client.user}")
    print(f"Counting channel: {config['counting_channel_id']}")
    print(f"Current count: {state['last_number']}")

    channel_id = config["counting_channel_id"]


    print(channel_id)
    if channel_id == 0:
        return


    channel = client.get_channel(channel_id)

    if not channel:
        return

    # Cleanup messages sent while bot was offline
    async for msg in channel.history(limit=100):

        if msg.author.bot:
            continue

        content = msg.content.strip()


        # If message is not a valid integer, delete it
        if not content.isdigit():
            try:
                await msg.delete()
            except Exception as e:
                print(f"Startup cleanup delete failed: {e}")
            continue

        number = int(content)

        # Stop cleanup once we reach a count that is
        # less than or equal to the saved count
        if number <= state["last_number"]:
            continue

        # Delete any number greater than the saved count
        try:
            await msg.delete()
        except Exception as e:
            print(f"Startup cleanup delete failed: {e}")


# ----------------------------
# Commands
# ----------------------------

# set-counting-channel
# ----------------------------

@tree.command(
    name="set-counting-channel",
    description="Set the counting channel"
)
@app_commands.checks.has_permissions(administrator=True)
async def set_counting_channel(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    config["counting_channel_id"] = channel.id
    save_config()

    await interaction.response.send_message(
        f"✅ Counting channel set to {channel.mention}",
        ephemeral=True
    )

# check-last-count
# ----------------------------

@tree.command(
    name="check-last-count",
    description="Show the last valid count"
)
async def check_last_count(interaction: discord.Interaction):

    await interaction.response.send_message(
        f"Current saved count: **{state['last_number']}**\n"
        f"Next valid number: **{state['last_number'] + 1}**",
        ephemeral=True
    )

# set-count-value
# ----------------------------

@tree.command(
    name="set-count-value",
    description="Manually set the current count and optionally the last user"
)
async def set_count(
    interaction: discord.Interaction,
    count: int,
    message_count: int,
    user: discord.Member | None = None
):
    if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message(
            "❌ You are not allowed to use this command.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    state["last_number"] = count
    state["last_user_id"] = user.id if user else None
    save_state()

    deleted = 0

    channel_id = config["counting_channel_id"]

    if channel_id:
        channel = client.get_channel(channel_id)

        if channel:
            async for msg in channel.history(limit=message_count):

                if msg.author.bot:
                    continue

                content = msg.content.strip()

                if not content.isdigit():
                    continue

                try:
                    number = int(content)

                    if number > count:
                        await msg.delete()
                        deleted += 1

                except Exception as e:
                    print(f"Delete failed: {e}")

    await interaction.followup.send(
        f"✅ Count updated.\n"
        f"Last number: **{count}**\n"
        f"Last user: {user.mention if user else 'None'}\n"
        f"Next valid number: **{count + 1}**\n"
        f"Deleted **{deleted}** messages with values greater than **{count}** "
        f"from the last **{message_count}** messages checked.",
        ephemeral=True
    )

# delete-last-messages
# ----------------------------

@tree.command(
name="delete-last-messages",
description="Delete the last N messages from the counting channel."
)
async def delete_last_messages(
    interaction: discord.Interaction,
    message_count: app_commands.Range[int, 1, 100]
):
    if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message(
            "❌ You are not allowed to use this command.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    channel_id = config["counting_channel_id"]

    if channel_id == 0:
        await interaction.followup.send(
            "❌ Counting channel is not configured.",
            ephemeral=True
        )
        return

    channel = client.get_channel(channel_id)

    if channel is None:
        await interaction.followup.send(
            "❌ Could not find the counting channel.",
            ephemeral=True
        )
        return

    deleted = 0

    async for msg in channel.history(limit=message_count):
        try:
            await msg.delete()
            deleted += 1
        except Exception as e:
            print(f"Delete failed: {e}")

    await interaction.followup.send(
        f"✅ Deleted **{deleted}** message(s).",
        ephemeral=True
    )

# server-leaderboard
# ----------------------------

@tree.command(
    name="server-leaderboard",
    description="Show the counting leaderboard."
)
async def server_leaderboard(
    interaction: discord.Interaction,
    sort_by: Literal['total count', 'max streak'],
    count: app_commands.Range[int, 1, 50] = 3,
):

    if not stats:
        await interaction.response.send_message(
            "No statistics available.",
            ephemeral=True
        )
        return

    if ALLOWED_ROLE_ID not in [role.id for role in interaction.user.roles]:
        await interaction.response.send_message(
            "❌ You are not allowed to use this command.",
            ephemeral=True
        )
        return

    leaderboard = sorted(
        stats.items(),
        key=lambda x: x[1]['_'.join(sort_by.split())],
        reverse=True
    )[:count]

    lines = ["## 📊 Counting Leaderboard\n"]

    for index, (user_id, data) in enumerate(leaderboard, start=1):

        member = interaction.guild.get_member(int(user_id))

        username = (
            member.display_name
            if member
            else data["username"]
        )

        data = ensure_user_stats(
        user_id,
        username
        )

        lines.append(
            f"### #{index} {username}\n"
            f"**Total Accepted Counts:** {data['total_count']}\n"
            f"**Current Streak:** 🔥 {data['cur_streak']}\n"
            f"**Best Streak:** 🏆 {data['max_streak']}\n"
            f"**Last Active:** {data['last_active_date']}\n"
        )

    save_stats()

    await interaction.response.send_message(
        "\n".join(lines)
    )


# ----------------------------
# Message Handling
# ----------------------------

@client.event
async def on_message(message):

    if message.author.bot:
        return

    channel_id = config["counting_channel_id"]

    if channel_id == 0:
        return

    if message.channel.id != channel_id:
        return

    content = message.content.strip()

    is_allowed_role = any(
        role.id == ALLOWED_ROLE_ID
        for role in message.author.roles
    )

    # Delete stickers/files/embeds/empty messages
    if (
        message.attachments
        or message.stickers
        or message.embeds
        or not content
    ):
        if is_allowed_role:
            return
        try:
            await message.delete()
        except Exception as e:
            print(f"Delete failed: {e}")
        return

    # Must be integer
    if not content.isdigit():
        if is_allowed_role:
            return
        try:
            await message.delete()
        except Exception as e:
            print(f"Delete failed: {e}")
        return

    # Same user twice
    if message.author.id == state["last_user_id"]:
        try:
            await message.delete()
        except Exception as e:
            print(f"Delete failed: {e}")
        return

    # Reject leading zeros
    if str(int(content)) != content:
        try:
            await message.delete()
        except Exception as e:
            print(f"Delete failed: {e}")
        return

    number = int(content)

    # Must be next number according to saved state
    print(number, state["last_number"])
    if number != state["last_number"] + 1:
        try:
            await message.delete()
        except Exception as e:
            print(f"Delete failed: {e}")
        return

    # Valid count
    state["last_number"] = number
    state["last_user_id"] = message.author.id

    save_state()

    # ----------------------------
    # Update User Stats
    # ----------------------------

    user_id = str(message.author.id)

    user = ensure_user_stats(
        user_id,
        message.author.display_name
    )

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    today_str = today.isoformat()

    # Increment accepted count
    user["total_count"] += 1

    last_day = user["last_active_day"]

    if last_day:

        last_day = datetime.strptime(
            last_day,
            "%Y-%m-%d"
        ).date()

        if today == last_day:
            # Already counted today
            pass

        elif today == last_day + timedelta(days=1):
            # Consecutive day
            user["cur_streak"] += 1

        else:
            # Streak broken
            user["max_streak"] = max(
                user["max_streak"],
                user["cur_streak"]
            )

            user["cur_streak"] = 1

    user["max_streak"] = max(
        user["max_streak"],
        user["cur_streak"]
    )

    user["last_active_day"] = today_str

    user["last_active_date"] = (
        datetime.now(ZoneInfo("Asia/Kolkata"))
        .strftime("%d %b %Y %I:%M %p")
    )

    save_stats()

    # Milestone messages
    if number % 10000 == 0:
        await message.add_reaction("🏆")
        await message.channel.send(
            f"🏆 **MILESTONE ACHIEVED!** 🏆\n"
            f"We've reached **{number:,}**! Incredible work everyone!"
        )

    elif number % 1000 == 0:
        await message.add_reaction("💪🏻")
        await message.channel.send(
            f"**{number:,}** reached! Keep the count going! 💪🏻"
        )

    elif number % 100 == 0:
        await message.add_reaction("💯")
        await message.channel.send(
            f"Nice! **{number:,}** reached already! Keep it up! 💯"
        )

    print(
        f"Accepted count {number} "
        f"from {message.author}"
    )


# ----------------------------
# Edit Protection
# ----------------------------

@client.event
async def on_message_edit(before, after):

    channel_id = config["counting_channel_id"]

    if channel_id == 0:
        return

    if after.channel.id != channel_id:
        return

    try:
        await after.delete()
    except Exception as e:
        print(f"Edit delete failed: {e}")


client.run(TOKEN)