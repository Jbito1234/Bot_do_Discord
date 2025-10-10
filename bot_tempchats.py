import discord
from discord.ext import commands, tasks
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Guarda os canais temporários criados
temporarios = {}

# Nome base do canal temporário
NOME_CANAL = "TempChat"

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    print("Bot pronto para criar/mover canais temporários.")

async def criar_canal_temporario(guild):
    """Cria um canal temporário sem duplicar e respeitando rate limits."""
    # Evita criar se já existir
    for canal_id in temporarios.values():
        canal = guild.get_channel(canal_id)
        if canal:
            return canal  # Canal já existe

    try:
        canal = await guild.create_text_channel(NOME_CANAL)
        temporarios[guild.id] = canal.id
        print(f"Criado canal temporário: {canal.name}")
        await asyncio.sleep(1.5)  # Delay para respeitar rate limit
        return canal
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("Rate limit atingido. Aguardando...")
            await asyncio.sleep(5)
            return await criar_canal_temporario(guild)
        else:
            print(f"Erro ao criar canal: {e}")
            return None

async def mover_canal_temporario(guild, novo_nome):
    """Move/renomeia o canal temporário respeitando rate limits."""
    canal_id = temporarios.get(guild.id)
    if not canal_id:
        canal = await criar_canal_temporario(guild)
    else:
        canal = guild.get_channel(canal_id)
        if not canal:
            canal = await criar_canal_temporario(guild)

    try:
        await canal.edit(name=novo_nome)
        print(f"Canal renomeado para: {novo_nome}")
        await asyncio.sleep(1.5)  # Delay
    except discord.errors.HTTPException as e:
        if e.status == 429:
            print("Rate limit atingido ao mover canal. Aguardando...")
            await asyncio.sleep(5)
            await mover_canal_temporario(guild, novo_nome)
        else:
            print(f"Erro ao mover canal: {e}")

# Exemplo de comando para criar/mover canal temporário
@bot.command()
async def temp(ctx, nome: str):
    await mover_canal_temporario(ctx.guild, nome)
    await ctx.send(f"Canal temporário atualizado para: {nome}")

# Se você tiver um webserver, ele pode ser inicializado aqui também
from aiohttp import web

async def handle(request):
    return web.Response(text="Bot ativo!")

app = web.Application()
app.add_routes([web.get("/", handle)])

def run_webserver():
    web.run_app(app, host="0.0.0.0", port=10000)

# Rodar bot e webserver simultaneamente
async def main():
    await bot.start("SEU_TOKEN_AQUI")

# Para Render ou Google Cloud, use isso:
# asyncio.run(main())

if __name__ == "__main__":
    # Apenas exemplo para teste local
    import threading
    threading.Thread(target=run_webserver).start()
    asyncio.run(main())
