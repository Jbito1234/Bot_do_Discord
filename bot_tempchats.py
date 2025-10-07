import discord
import os
import asyncio
from deep_translator import GoogleTranslator
import aiohttp

# --- Configurações Globais ---
CONFIGURACOES = [
    {
        "GAME_ID": "8752798054",  # ID do jogo Roblox
        "CHANNEL_ID": 1425085470144204861,  # Canal do Discord
        "NOME_JOGO": "Roube uma Waifu"
    }
]

# --- Inicialização do Bot ---
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# --- Função para obter posts de atualizações de jogos Roblox ---
async def buscar_posts_jogo(game_id):
    url = f"https://games.roblox.com/v2/games/{game_id}/updates?sortOrder=Desc&limit=10"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"Erro ao buscar posts do jogo {game_id}: {resp.status}")
                return []
            data = await resp.json()
            return data.get("data", [])

# --- Função principal de monitoramento ---
async def monitorar_atualizacoes():
    print("🔍 Iniciando monitoramento de atualizações dos jogos Roblox...")

    # Cache local de posts já vistos
    posts_vistos = {conf["GAME_ID"]: [] for conf in CONFIGURACOES}

    await bot.wait_until_ready()
    canal = None

    while not bot.is_closed():
        for conf in CONFIGURACOES:
            game_id = conf["GAME_ID"]
            channel_id = conf["CHANNEL_ID"]
            nome_jogo = conf["NOME_JOGO"]

            if canal is None:
                canal = bot.get_channel(channel_id)

            if canal is None:
                print(f"❌ Canal {channel_id} não encontrado.")
                continue

            try:
                novos_posts = await buscar_posts_jogo(game_id)
                if not novos_posts:
                    continue

                # Verifica novos posts
                ids_novos = [p["id"] for p in novos_posts]
                ids_antigos = posts_vistos.get(game_id, [])

                novos = [p for p in novos_posts if p["id"] not in ids_antigos]

                if novos:
                    for post in novos:
                        titulo = post.get("title", "Sem título")
                        corpo = post.get("body", "Sem descrição")

                        # Tradução automática para português
                        descricao_pt = GoogleTranslator(source='auto', target='pt').translate(corpo)

                        embed = discord.Embed(
                            title=f"🆕 Nova atualização em {nome_jogo}!",
                            description=f"**{titulo}**\n\n{descricao_pt}",
                            color=discord.Color.blue()
                        )
                        embed.set_footer(text="Tradução automática - Google Translator")

                        await canal.send(embed=embed)
                        print(f"✅ Nova atualização enviada: {titulo}")

                    # Atualiza cache local
                    posts_vistos[game_id] = ids_novos

            except Exception as e:
                print(f"Erro ao verificar atualizações do jogo {game_id}: {e}")

        await asyncio.sleep(60 * 5)  # Espera 5 minutos antes de checar novamente

# --- Inicialização do Bot ---
@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    bot.loop.create_task(monitorar_atualizacoes())

# --- Execução ---
bot.run(os.getenv("DISCORD_TOKEN"))
