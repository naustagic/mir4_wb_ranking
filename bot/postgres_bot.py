import discord
from discord.ext import commands, tasks
from datetime import datetime
import asyncio
import asyncpg
import json
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get the environment variables
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_DATABASE = os.getenv('DB_DATABASE')
DB_HOST = os.getenv('DB_HOST')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Insert the destination voice channel ID here
DESTINATION_CHANNEL_ID = 896186390470090774

# Insert the text channel ID where the bot will send information
TEXT_CHANNEL_ID = 1174224690328387644

# Insert the start and end time for each interval
FIRST_INTERVAL_START = datetime.strptime("10:05", "%H:%M")
FIRST_INTERVAL_END = datetime.strptime("10:06", "%H:%M")

SECOND_INTERVAL_START = datetime.strptime("12:05", "%H:%M")
SECOND_INTERVAL_END = datetime.strptime("12:06", "%H:%M")

THIRD_INTERVAL_START = datetime.strptime("20:05", "%H:%M")
THIRD_INTERVAL_END = datetime.strptime("20:06", "%H:%M")

FOURTH_INTERVAL_START = datetime.strptime("22:05", "%H:%M")
FOURTH_INTERVAL_END = datetime.strptime("22:06", "%H:%M")

MAX_MEMBERS_PER_FIELD = 25

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Add a variable for counting
start_count = 0

# Connect to the PostgreSQL database
async def create_pool():
    return await asyncpg.create_pool(user=DB_USER, password=DB_PASSWORD, database=DB_DATABASE, host=DB_HOST)

# Function to register presence
async def register_presence(member, wb_interval, pool):
    horario = datetime.now()
    member_name = member.nick or member.name

    async with pool.acquire() as connection:
        insert_query = "INSERT INTO presenca (usuario_id, wb_interval, horario) VALUES ($1, $2, $3)"
        await connection.execute(insert_query, member_name, wb_interval, horario)

    # Adiciona as informações ao arquivo backup.json
    backup_data = {
        "usuario_id": member_name,
        "wb_interval": wb_interval,
        "horario": horario.strftime("%Y-%m-%d %H:%M:%S")
    }
    with open('backup.json', 'a') as f:
        f.write(json.dumps(backup_data) + "\n")

# Function to be called when the bot is ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    check_users.start()

    # Create the table if it does not exist
    pool = await create_pool()
    create_table_query = """
        CREATE TABLE IF NOT EXISTS presenca (
            id SERIAL PRIMARY KEY,
            usuario_id VARCHAR(255),
            wb_interval VARCHAR(50),
            horario TIMESTAMP
        )
    """
    async with pool.acquire() as connection:
        await connection.execute(create_table_query)

# Function to send user information to the text channel
@tasks.loop(minutes=1)
async def check_users():
    global start_count

    destination_channel = bot.get_channel(DESTINATION_CHANNEL_ID)

    if destination_channel is None:
        print("Destination channel not found.")
        return

    now = datetime.now()
    footer_text = now.strftime("%d/%m %H:%M")

    if now.time() >= FIRST_INTERVAL_START.time() and now.time() <= FIRST_INTERVAL_END.time():
        title = "Players WB Lab. Manhã:"
        wb_interval = "Lab Manhã"
        start_count = 0
    elif now.time() >= SECOND_INTERVAL_START.time() and now.time() <= SECOND_INTERVAL_END.time():
        title = "Players WB Vales Manhã:"
        wb_interval = "Vales Manhã"
        start_count = 0
    elif now.time() >= THIRD_INTERVAL_START.time() and now.time() <= THIRD_INTERVAL_END.time():
        title = "Players WB Lab. Noite:"
        wb_interval = "Lab Noite"
        start_count = 0
    elif now.time() >= FOURTH_INTERVAL_START.time() and now.time() <= FOURTH_INTERVAL_END.time():
        title = "Players WB Vales Noite:"
        wb_interval = "Vales Noite"
        start_count = 0
    else:
        return

    members_list = [member.nick or member.name for member in destination_channel.members]
    if not members_list:
        return

    pool = await create_pool()

    for member in destination_channel.members:
        await register_presence(member, wb_interval, pool)

    if len(members_list) <= MAX_MEMBERS_PER_FIELD:
        embed = discord.Embed(title=title)
        embed.add_field(name="Members", value="\n".join(f"`{i+1}. {member}`" for i, member in enumerate(members_list)), inline=False)
        embed.set_footer(text=footer_text)
        await bot.get_channel(TEXT_CHANNEL_ID).send(embed=embed)
    else:
        embeds = []
        members_chunks = [members_list[i:i+MAX_MEMBERS_PER_FIELD] for i in range(0, len(members_list), MAX_MEMBERS_PER_FIELD)]
        for i, chunk in enumerate(members_chunks):
            embed = discord.Embed(title=title)
            field_name = f"Members (part {start_count + i + 1} of {len(members_chunks)})"
            field_value = "\n".join(f"`{start_count + i + 1}. {member}`" for i, member in enumerate(chunk))
            embed.add_field(name=field_name, value=field_value, inline=False)
            embed.set_footer(text=f"{footer_text} - Part {start_count + i + 1}/{len(members_chunks)}")
            embeds.append(embed)
        for i, embed in enumerate(embeds):
            if i == len(embeds) - 1:
                embed.add_field(name="Total de Players", value=str(len(members_list)), inline=False)
            await bot.get_channel(TEXT_CHANNEL_ID).send(embed=embed)
        start_count += len(members_list)

# Insert your bot token here
bot.run(BOT_TOKEN)
