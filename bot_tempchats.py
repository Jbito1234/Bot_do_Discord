import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from aiohttp import web

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ID do canal de voz que gera canais temporários
CHANNEL_TRIGGER_ID = 123456789012345678  # Troque pelo seu canal

# Dicionário para armazenar canais temporários
temp_channels = {}

# Evento quando o bot está pronto
@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    try:
        await tree.sync()
        print("Comandos sincronizados")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

# Evento para detectar mudança de estado de voz
@bot.event
async def on_voice_state_update(member, before, after):
    # Se entrou no canal gatilho
    if after.channel and after.channel.id == CHANNEL_TRIGGER_ID:
        guild = member.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(manage_channels=True)
        }

        # Cria canal temporário
        temp_channel = await guild.create_voice_channel(
            name=f"Canal do {member.display_name}",
            overwrites=overwrites,
            category=after.channel.category
        )

        # Move o membro pro canal criado
        await member.move_to(temp_channel)

        # Salva info
        temp_channels[temp_channel.id] = {
            "owner_id": member.id,
            "channel": temp_channel
        }

        # Checa se o canal fica vazio para deletar
        asyncio.create_task(check_empty_channel(temp_channel))

async def check_empty_channel(channel):
    await asyncio.sleep(5)  # Delay para evitar falsas deleções
    while True:
        if len(channel.members) == 0:
            try:
                await channel.delete()
            except Exception:
                pass
            temp_channels.pop(channel.id, None)
            break
        await asyncio.sleep(10)

# Comando slash para definir descrição do canal
@tree.command(name="descricao", description="Define a descrição do seu canal de voz temporário.")
@app_commands.describe(texto="Descrição para o canal")
async def descricao(interaction: discord.Interaction, texto: str):
    user = interaction.user
    for data in temp_channels.values():
        if data["owner_id"] == user.id:
            channel = data["channel"]
            await channel.edit(topic=texto)
            await interaction.response.send_message(f"Descrição definida: {texto}", ephemeral=True)
            return

    await interaction.response.send_message("Você não é dono de nenhum canal temporário ativo.", ephemeral=True)

# --- Servidor HTTP simples para manter o bot acordado ---

async def handle(request):
    return web.Response(text="Bot ativo!")

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

# Roda o webserver em background junto com o bot
@bot.event
async def on_connect():
    asyncio.create_task(start_webserver())

# Rodar o bot
import os
bot.run(os.getenv("DISCORD_TOKEN"))
