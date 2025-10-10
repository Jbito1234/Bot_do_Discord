import discord
from discord.ext import commands
from aiohttp import web
import asyncio

# ===============================
# Configurações do bot
# ===============================
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===============================
# Função para criar o webserver
# ===============================
async def handle(request):
    return web.Response(text="Bot ativo!")

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    print("Webserver iniciado na porta 10000")

# ===============================
# Evento ready
# ===============================
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# ===============================
# Exemplo de comando
# ===============================
@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

# ===============================
# Função principal
# ===============================
async def main():
    # Inicia webserver
    await start_webserver()
    # Inicia bot Discord
    await bot.start("SEU_TOKEN_DO_BOT_AQUI")  # <-- Coloque o token real aqui

# ===============================
# Roda tudo
# ===============================
asyncio.run(main())
