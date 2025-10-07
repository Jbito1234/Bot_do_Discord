import discord
import os
import asyncio
from googletrans import Translator
import aiohttp  # Para requisições assíncronas

# --- Configurações Globais ---
CONFIGURACOES = [
    {
        "GAME_ID": "8752798054",
        "CHANNEL_ID": 1425085470144204861,
        "NOME": "Roube um Brainrot",
        "INTERVALO": 60
    },
    {
        "GAME_ID": "127742093697776",
        "CHANNEL_ID": 1425086215643725834,
        "NOME": "Plantas VS Brainrots",
        "INTERVALO": 60
    },
    {
        "GAME_ID": "108533757090220",
        "CHANNEL_ID": 1425086490379161671,
        "NOME": "Garden Tower Defense",
        "INTERVALO": 60
    }
]

# --- Intents corrigidas ---
intents = discord.Intents.default()
intents.guilds = True  # Necessário para fetch_channel
bot = discord.Bot(intents=intents)

translator = Translator()
current_post_ids_cache = {}  # Cache de posts já enviados


async def fetch_posts(game_id):
    """Busca postagens do Roblox de forma assíncrona e traduz para PT-BR."""
    url = f"https://games.roblox.com/v1/games/{game_id}/universe-updates?sortOrder=Desc&limit=20"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    print(f"Erro ao buscar posts para {game_id}: Status {r.status}")
                    return []
                data = await r.json()
    except Exception as e:
        print(f"Erro ao pegar postagens para {game_id}:", e)
        return []

    posts = []
    for post in data.get("data", []):
        title_lower = post.get("title", "").lower()
        if "event" in title_lower or "evento" in title_lower:
            post_type = "🎉 Evento"
            embed_color = discord.Color.gold()
        else:
            post_type = "🔧 Atualização"
            embed_color = discord.Color.blue()

        descricao_pt = translator.translate(post.get("body", ""), src='en', dest='pt').text

        posts.append({
            "id": post.get("id"),
            "titulo": post.get("title"),
            "descricao": descricao_pt,
            "data": post.get("created"),
            "imagem": post.get("thumbnailUrl"),
            "tipo": post_type,
            "cor": embed_color
        })
    return posts


async def verificar_atualizacoes(game_id, channel_id, interval):
    """Verifica e envia atualizações novas."""
    if game_id not in current_post_ids_cache:
        current_post_ids_cache[game_id] = set()

    await bot.wait_until_ready()
    
    try:
        canal = await bot.fetch_channel(channel_id)
    except Exception as e:
        print(f"Erro ao buscar canal {channel_id}: {e}")
        return

    if canal is None:
        print(f"Canal {channel_id} não encontrado.")
        return

    # Preencher cache na primeira execução
    if not current_post_ids_cache[game_id]:
        print(f"[{game_id}] Preenchendo cache inicial...")
        initial_posts = await fetch_posts(game_id)
        current_post_ids_cache[game_id] = {post['id'] for post in initial_posts}
        await asyncio.sleep(interval)
        return

    while True:
        novas_postagens = await fetch_posts(game_id)
        novas_para_enviar = [p for p in novas_postagens if p['id'] not in current_post_ids_cache[game_id]]

        for post in reversed(novas_para_enviar):
            linhas_desc = post["descricao"].split('\n')
            descricao_formatada = ""
            if len(post["descricao"]) > 1024 or len(linhas_desc) > 8:
                descricao_formatada = post["descricao"][:800] + "..."
            else:
                for i, linha in enumerate(linhas_desc):
                    if linha.strip():
                        descricao_formatada += f"{i+1}. {linha.strip()}\n"

            embed = discord.Embed(
                title=f"{post['tipo']} - {post['titulo']}",
                description=descricao_formatada,
                color=post['cor']
            )
            if post["imagem"]:
                embed.set_image(url=post["imagem"])
            embed.set_footer(text=f"Publicado em: {post['data']}")

            try:
                await canal.send(embed=embed)
            except Exception as e:
                print(f"Erro ao enviar embed para canal {channel_id}: {e}")
            await asyncio.sleep(5)

        if novas_para_enviar:
            current_post_ids_cache[game_id].update({post['id'] for post in novas_para_enviar})

        await asyncio.sleep(interval)


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    for config in CONFIGURACOES:
        print(f"Iniciando monitoramento de {config['NOME']} ({config['GAME_ID']})")
        bot.loop.create_task(verificar_atualizacoes(
            config["GAME_ID"],
            config["CHANNEL_ID"],
            config["INTERVALO"]
        ))


# Executa o bot
bot.run(os.getenv('DISCORD_TOKEN'))
