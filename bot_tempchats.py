import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os # Boas práticas: use para carregar o token de forma segura

# ===============================
# Configurações do bot
# ===============================
# Define o token do bot. É recomendado usar variáveis de ambiente (os.getenv).
BOT_TOKEN = "DISCORD_TOKEN" # <-- COLOQUE SEU TOKEN REAL AQUI

intents = discord.Intents.default()
# Garante que as permissões necessárias estão ativas
intents.guilds = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===============================
# Função do Webserver
# ===============================
async def handle(request):
    """Handler simples para a rota raiz."""
    return web.Response(text="Bot ativo e webserver funcionando!")

async def start_webserver():
    """Configura e inicia o servidor web aiohttp."""
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    
    # Prepara o executor do aplicativo
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Configura o site na porta 10000
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    
    print("Webserver iniciado na porta 10000")
    
    # Mantém a tarefa viva indefinidamente.
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        # Limpeza ao parar a tarefa
        await runner.cleanup()
        print("Webserver desligado.")

# ===============================
# Evento ready
# ===============================
@bot.event
async def on_ready():
    """Executado quando o bot se conecta ao Discord."""
    print(f"Bot conectado como {bot.user} (ID: {bot.user.id})")
    print("-" * 30)

# ===============================
# Exemplo de comando
# ===============================
@bot.command()
async def ping(ctx):
    """Responde com 'Pong!' e a latência do bot."""
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latência: **{latency_ms}ms**")

# ===============================
# Função principal - Correção aqui!
# ===============================
async def main():
    # Usamos asyncio.gather para executar o bot e o webserver CONCORRENTEMENTE
    # O bot.start() é a tarefa principal que mantém o loop de eventos ativo.
    
    # Garante que o token não seja o placeholder
    if BOT_TOKEN == "SEU_TOKEN_DO_BOT_AQUI":
        print("ERRO: Por favor, substitua 'SEU_TOKEN_DO_BOT_AQUI' pelo token real do seu bot.")
        return

    # O servidor web será iniciado como uma tarefa em segundo plano.
    # O bot.start() é o await que irá rodar indefinidamente.
    webserver_task = asyncio.create_task(start_webserver())
    
    try:
        # Inicia o bot Discord. Esta linha bloqueará até que o bot seja encerrado.
        await bot.start(BOT_TOKEN)
    finally:
        # Se o bot cair, cancele a tarefa do webserver também.
        webserver_task.cancel()
        # Aguarde para garantir que o cancelamento seja processado.
        await asyncio.gather(webserver_task, return_exceptions=True)
        
        print("Aplicação principal encerrada.")

# ===============================
# Roda tudo
# ===============================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Encerrado pelo usuário.")
    except Exception as e:
        print(f"Ocorreu um erro fatal: {e}")
