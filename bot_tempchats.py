# bot_tempchats_cloud.py
import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from aiohttp import web

# --------------------------
# Configurações
# --------------------------
CHANNEL_TRIGGER_ID = 1424934971277185024  # Canal gatilho
CATEGORY_ID = 1424934711251439677         # Categoria para canais temporários
KEEPALIVE_PORT = int(os.getenv("PORT", 8080))  # Porta para webserver

# --------------------------
# Intents & bot
# --------------------------
intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --------------------------
# Estado global
# --------------------------
temp_channels = {}  # {channel_id: {"owner_id": int}}

# --------------------------
# Webserver para keepalive
# --------------------------
async def handle_root(request):
    return web.Response(text="Bot ativo!")

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle_root)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', KEEPALIVE_PORT)
    await site.start()
    print(f"Webserver iniciado em 0.0.0.0:{KEEPALIVE_PORT}")

# --------------------------
# Eventos: canais temporários de voz
# --------------------------
@bot.event
async def on_voice_state_update(member, before, after):
    if after.channel and after.channel.id == CHANNEL_TRIGGER_ID:
        guild = member.guild
        category = guild.get_channel(CATEGORY_ID)
        if not category:
            print("Categoria não encontrada ou sem permissão.")
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(manage_channels=True)
        }

        try:
            temp_channel = await guild.create_voice_channel(
                name=f'Canal do {member.display_name}',
                overwrites=overwrites,
                category=category
            )
            await member.move_to(temp_channel)
        except Exception as e:
            print("Erro ao criar/mover canal temporário:", e)
            return

        temp_channels[temp_channel.id] = {"owner_id": member.id}
        asyncio.create_task(check_empty_channel(temp_channel))

async def check_empty_channel(channel: discord.VoiceChannel):
    await asyncio.sleep(5)
    while True:
        try:
            if len(channel.members) == 0:
                try:
                    await channel.delete()
                except Exception as e:
                    print(f"Erro ao deletar canal {channel.id}: {e}")
                temp_channels.pop(channel.id, None)
                break
        except Exception:
            temp_channels.pop(channel.id, None)
            break
        await asyncio.sleep(10)

# --------------------------
# Comando slash: descricao
# --------------------------
@tree.command(name='descricao', description='Define a descrição do seu canal de voz temporário.')
@app_commands.describe(texto='Descrição para o canal')
async def descricao(interaction: discord.Interaction, texto: str):
    user = interaction.user
    guild = interaction.guild

    for channel_id, data in list(temp_channels.items()):
        if data.get('owner_id') == user.id:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.edit(topic=texto)
                    await interaction.response.send_message(f'Descrição definida: {texto}', ephemeral=True)
                except Exception:
                    await interaction.response.send_message('Erro ao editar a descrição do canal.', ephemeral=True)
            else:
                await interaction.response.send_message('Não foi possível encontrar seu canal.', ephemeral=True)
            return

    await interaction.response.send_message('Você não é dono de nenhum canal temporário ativo.', ephemeral=True)

# --------------------------
# Evento on_ready
# --------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user} (ID: {bot.user.id})")
    if not hasattr(bot, 'webserver_started'):
        asyncio.create_task(start_webserver())
        bot.webserver_started = True
    try:
        await tree.sync()
        print("Comandos sincronizados")
    except Exception as e:
        print("Erro ao sincronizar comandos:", e)

# --------------------------
# Inicialização segura com retry
# --------------------------
async def start_bot():
    retry_delay = 60  # segundos
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("ERRO: variável de ambiente DISCORD_TOKEN não encontrada.")
        return

    while True:
        try:
            await bot.start(TOKEN)
        except discord.HTTPException as e:
            print("Erro HTTP ou rate limit detectado:", e)
            print(f"Reconectando em {retry_delay}s...")
            await asyncio.sleep(retry_delay)
        except Exception as e:
            print("Erro inesperado:", e)
            print(f"Reconectando em {retry_delay}s...")
            await asyncio.sleep(retry_delay)

# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    asyncio.run(start_bot())
