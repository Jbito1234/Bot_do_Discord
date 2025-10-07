import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from aiohttp import web
import os

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

CHANNEL_TRIGGER_ID = 1424934971277185024  # ID do canal gatilho
CATEGORY_ID = 1424934711251439677  # ID da categoria onde os canais temporários serão criados

# temp_channels agora armazena apenas o owner_id por canal_id
temp_channels = {}

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    try:
        await tree.sync()
        print("Comandos sincronizados")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    # Inicia o webserver uma única vez
    if not hasattr(bot, 'webserver_started'):
        asyncio.create_task(start_webserver())
        bot.webserver_started = True

@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == CHANNEL_TRIGGER_ID:
        guild = member.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(manage_channels=True)
        }

        category = guild.get_channel(CATEGORY_ID)

        temp_channel = await guild.create_voice_channel(
            name=f'Canal do {member.display_name}',
            overwrites=overwrites,
            category=category
        )

        await member.move_to(temp_channel)

        # Salva apenas o owner_id
        temp_channels[temp_channel.id] = {
            "owner_id": member.id
        }

        asyncio.create_task(check_empty_channel(temp_channel))

async def check_empty_channel(channel):
    await asyncio.sleep(5)
    while True:
        if len(channel.members) == 0:
            try:
                await channel.delete()
            except Exception as e:
                print(f"Erro ao deletar canal: {e}")
            temp_channels.pop(channel.id, None)
            break
        await asyncio.sleep(10)

@tree.command(name='descricao', description='Define a descrição do seu canal de voz temporário.')
@app_commands.describe(texto='Descrição para o canal')
async def descricao(interaction: discord.Interaction, texto: str):
    user = interaction.user
    guild = interaction.guild

    for channel_id, data in temp_channels.items():
        if data['owner_id'] == user.id:
            channel = guild.get_channel(channel_id)
            if channel:
                await channel.edit(topic=texto)
                await interaction.response.send_message(f'Descrição definida: {texto}', ephemeral=True)
            else:
                await interaction.response.send_message('Não foi possível encontrar seu canal.', ephemeral=True)
            return

    await interaction.response.send_message('Você não é dono de nenhum canal temporário ativo.', ephemeral=True)

async def handle(request):
    return web.Response(text='Bot ativo!')

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

bot.run(os.getenv('DISCORD_TOKEN'))
