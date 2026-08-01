import json
import random
import discord

with open("data/milestone_gifs.json", "r") as f:
    GIFS = json.load(f)

MILESTONE_TITLES = [
    "🎉 Milestone Reached!",
    "🏆 Incredible!",
    "🔥 Community Achievement!",
    "🚀 Keep Counting!",
    "🥳 Another Goal Crushed!"
]

MILESTONE_MESSAGES = [
    "Amazing work everyone! We've reached **{number:,}**!",
    "Another milestone unlocked — **{number:,}**!",
    "This server is unstoppable! **{number:,}** counts!",
    "Keep the momentum going! **{number:,}** reached!",
    "Congratulations everyone! **{number:,}** is here!",
    "What a journey! We just crossed **{number:,}**!",
    "The counting never stops! **{number:,}** achieved!"
]


def get_next_milestone(number: int):

    if number % 10000 == 0:
        return number + 10000

    if number % 1000 == 0:
        return number + 1000

    return number + 100


def get_gif_pool(number: int):

    if number % 10000 == 0:
        return GIFS["10000"]

    if number % 1000 == 0:
        return GIFS["1000"]

    return GIFS["100"]


def build_milestone_embed(number: int):

    embed = discord.Embed(
        title=random.choice(MILESTONE_TITLES),
        description=random.choice(MILESTONE_MESSAGES).format(
            number=number
        ),
        color=discord.Color.gold()
    )

    gif = random.choice(get_gif_pool(number))
    print(gif)

    embed.set_image(url=gif)

    embed.set_footer(
        text=f"Next Milestone: {get_next_milestone(number):,} 🚀"
    )

    return embed


async def send_milestone(number: int, channel):

    embed = build_milestone_embed(number)

    await channel.send(embed=embed)