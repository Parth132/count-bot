import asyncio
import os
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from dotenv import load_dotenv

from helpers import config as config_helpers
from helpers import counting as counting_helpers
from helpers import stats as stats_helpers
from helpers.milestones import send_milestone

load_dotenv()
TOKEN = os.getenv("TOKEN")

DAILY_STATS_FILE = "daily_stats.json"
CONFIG_FILE = "config.json"
STATE_FILE = "count_state.json"
STAT_FILE = "stat_count.json"

ALLOWED_ROLE_ID = 1377336728100012102
ALLOWED_ROLE_ID_LIST = [924956391695863848,863827603701104690,1377336728100012102]

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# ----------------------------
# Config
# ----------------------------

def load_config():
    global config
    config = config_helpers.load_config()
    return config


def save_config():
    return config_helpers.save_config(config)


# ----------------------------
# State
# ----------------------------

def load_state():
    global state
    state = config_helpers.load_state()
    return state


def save_state():
    return config_helpers.save_state(state)


def load_stats():
    global stats
    stats = config_helpers.load_stats()
    return stats


def save_stats():
    return config_helpers.save_stats(stats)


# -------------------------
# Daily stats
# ------------------------

def load_daily_stats():
    global daily_stats
    daily_stats = config_helpers.load_daily_stats()
    return daily_stats


def save_daily_stats():
    return config_helpers.save_daily_stats(daily_stats)


daily_stats = load_daily_stats()
stats = load_stats()
config = load_config()
state = load_state()


# ---------------------------
# Helper Functions
# ---------------------------

def ensure_user_stats(user_id: str, username: str):
    return stats_helpers.ensure_user_stats(stats, user_id, username)


def get_configured_channel():
    channel_id = config["counting_channel_id"]
    if channel_id == 0:
        return None
    return client.get_channel(channel_id)


async def delete_message_safely(message):
    try:
        await message.delete()
    except Exception as e:
        print(f"Delete failed: {e}")


def build_user_stats_embed(user, data):
    embed = discord.Embed(
        title="📊 Counting Statistics",
        description=f"Statistics for **{user.display_name}**",
        color=discord.Color.blue(),
    )

    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="📈 Accepted Counts", value=f"`{data['total_count']:,}`", inline=True)
    embed.add_field(name="🔥 Current Streak", value=f"`{data['cur_streak']}` day(s)", inline=True)
    embed.add_field(name="🏆 Best Streak", value=f"`{data['max_streak']}` day(s)", inline=True)
    embed.add_field(name="🕒 Last Active", value=data["last_active_date"] or "Never", inline=False)
    embed.set_footer(text="Counting Bot • Keep the streak alive! :greed:")
    embed.timestamp = datetime.now(ZoneInfo("Asia/Kolkata"))
    return embed


def check_permissions(roles):
    return stats_helpers.check_permissions(roles, ALLOWED_ROLE_ID_LIST)


def cleanup_daily_stats():
    return stats_helpers.cleanup_daily_stats(daily_stats)


def build_daily_stats_embed(
    guild: discord.Guild,
    day: int = 0,
    count: int = 3
):
    return stats_helpers.build_daily_stats_embed(
        guild,
        daily_stats,
        day,
        count
    )


def build_server_leaderboard(guild: discord.Guild, count: int = 5):
    return stats_helpers.build_server_leaderboard(
        guild,
        stats,
        count
    )


def build_daily_report_embed(
    guild: discord.Guild,
    day_offset: int = 1,
):
    return stats_helpers.build_daily_report_embed(
        guild,
        daily_stats,
        day_offset
    )



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


    channel = get_configured_channel()

    if not channel:
        return

    cleanup_daily_stats()

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

    if not hasattr(client, "daily_report_started"):
        client.daily_report_started = True
        client.loop.create_task(daily_report_scheduler())



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
    message_count: int = 0,
    user: discord.Member | None = None
):

    if not check_permissions(interaction.user.roles):return

    await interaction.response.defer(ephemeral=True)

    state["last_number"] = count
    state["last_user_id"] = user.id if user else None
    save_state()

    deleted = 0

    channel = get_configured_channel()

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
    if not check_permissions(interaction.user.roles):return

    await interaction.response.defer(ephemeral=True)

    channel = get_configured_channel()

    if channel is None:
        await interaction.followup.send(
            "❌ Counting channel is not configured.",
            ephemeral=True
        )
        return
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

# user-stats
# ----------------------------

@tree.command(
    name="user-stats",
    description="Count stats for user"
)
async def user_stats(
    interaction: discord.Interaction,
    user: discord.Member | None = None
):

    if user is None:
        user = interaction.user

    user_id = str(user.id)

    data = ensure_user_stats(
        user_id,
        user.display_name
    )

    # save_stats()

    embed = build_user_stats_embed(user, data)
    await interaction.response.send_message(embed=embed)

# server-leaderboard
# ----------------------------

@tree.command(
    name="server-leaderboard",
    description="Shows the top counting members."
)
async def server_leaderboard(
    interaction: discord.Interaction,
    count: app_commands.Range[int, 1, 10] = 5
):

    if not stats:
        await interaction.response.send_message(
            "No statistics available.",
            ephemeral=True
        )
        return
    
    embed = build_server_leaderboard(
    interaction.guild,
    count
    )
    await interaction.response.send_message(embed=embed)

# daily-stats
# ----------------------------

@tree.command(
    name="daily-stats",
    description="View today's or yesterday's counting statistics."
)
@app_commands.describe(
    day="0 = Today, 1 = Yesterday",
    count="Number of users to display (1-10)"
)
async def daily_stats_command(
    interaction: discord.Interaction,
    day: app_commands.Range[int, 0, 1] = 0,
    count: app_commands.Range[int, 1, 10] = 3
):

    embed = build_daily_stats_embed(
        interaction.guild,
        day,
        count
    )

    if embed is None:
        await interaction.response.send_message(
            "No statistics found for that day.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(embed=embed)

async def post_daily_report():

    print('--------------------------------------')

    channel = await client.fetch_channel(config["counting_channel_id"])

    if channel is None:
        return

    embed = build_daily_report_embed(channel.guild)

    if embed is None:
        return

    perms = channel.permissions_for(channel.guild.me)

    print("Administrator:", perms.administrator)
    print("Send Messages:", perms.send_messages)
    print("Embed Links:", perms.embed_links)
    print("View Channel:", perms.view_channel)
    print("Read History:", perms.read_message_history)
    print("Use External Emojis:", perms.use_external_emojis)

    await channel.send(embed=embed)

async def daily_report_scheduler():

    await client.wait_until_ready()

    while not client.is_closed():

        now = datetime.now(ZoneInfo("Asia/Kolkata"))

        next_run = now.replace(
            hour=9,
            minute=30,
            second=0,
            microsecond=0
        )

        if now >= next_run:
            next_run += timedelta(days=1)
        print(now,next_run)
        wait_seconds = (next_run - now).total_seconds()

        await asyncio.sleep(wait_seconds)

        try:
            channel = await client.fetch_channel(config["counting_channel_id"])
            embed = build_daily_stats_embed(
                channel.guild,
                day=1,
                count=3
            )
            if embed:await channel.send(embed=embed)
            embed = build_server_leaderboard(channel.guild,5)
            await channel.send(embed=embed)
            await post_daily_report()
            print("Daily report posted.")
        except Exception:
            traceback.print_exc()

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
        await delete_message_safely(message)
        return

    # Must be integer
    if not content.isdigit():
        if is_allowed_role:
            return
        await delete_message_safely(message)
        return

    # Same user twice
    if message.author.id == state["last_user_id"]:
        await delete_message_safely(message)
        return

    # Reject leading zeros
    if str(int(content)) != content:
        await delete_message_safely(message)
        return

    number = int(content)

    # Must be next number according to saved state
    print(number, state["last_number"])
    if number != state["last_number"] + 1:
        await delete_message_safely(message)
        return

    # Valid count
    number = counting_helpers.update_count_state_and_stats(
        message,
        state,
        stats,
        daily_stats,
    )

    # Milestone messages
    if number % 10000 == 0:
        await message.add_reaction("🏆")
        await send_milestone(number, message.channel)

    elif number % 1000 == 0:
        await message.add_reaction("🔥")
        await send_milestone(number, message.channel)

    elif number % 100 == 0:
        await message.add_reaction("💯")
        await send_milestone(number, message.channel)

    print(
        f"Accepted count {number} "
        f"from {message.author}"
    )


# ----------------------------
# Edit Protection
# ----------------------------

@client.event
async def on_message_edit(before, after):

    if after.author.bot:
        return

    channel_id = config["counting_channel_id"]

    if channel_id == 0:
        return

    if after.channel.id != channel_id:
        return

    try:
        await after.delete()
        print('a message was edited and has been deleted.')
    except Exception as e:
        print(f"Edit delete failed: {e}")


client.run(TOKEN)