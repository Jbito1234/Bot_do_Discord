# bot_tempchats_full.py
import os
import asyncio
import aiohttp
from aiohttp import web
import discord
from discord.ext import commands
from discord import app_commands
from deep_translator import GoogleTranslator

# --------------------------
# Configurações
# --------------------------
CONFIGURACOES = [
    {
        "GAME_ID": "8752798054",
        "CHANNEL_ID": 1425085470144204861,
        "NOME": "Roube um Brainrot",
        "INTERVALO": 60  # segundos
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

CHANNEL_TRIGGER_ID = 1424934971277185024  # Canal gatilho
CATEGORY_ID = 1424934711251439677         # Categoria para canais temporários

# --------------------------
# Intents & bot
# --------------------------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# --------------------------
# Estado global
# --------------------------
temp_channels = {}                # {channel_id: {"owner_id": int}}
current_post_ids_cache = {}       # {game_id: set(post_ids)}

# --------------------------
# Util: tradução sem bloquear loop
# --------------------------
async def traduzir_para_pt(texto: str) -> str:
    texto = texto or ""
    try:
        # deep-translator usa requests (bloqueante) -> roda em thread separado
        return await asyncio.to_thread(GoogleTranslator(source='auto', target='pt').translate, texto)
    except Exception as e:
        print("Erro na tradução:", e)
        return texto

# --------------------------
# Webserver (útil pra keepalive)
# --------------------------
async def handle_root(request):
    return web.Response(text="Bot ativo!")

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle_root)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Webserver iniciado em 0.0.0.0:8080")

# --------------------------
# Buscar posts do Roblox (assíncrono)
# --------------------------
async def fetch_posts(game_id: str):
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
        title_lower = (post.get("title") or "").lower()
        if "event" in title_lower or "evento" in title_lower:
            post_type = "🎉 Evento"
            embed_color = discord.Color.gold()
        else:
            post_type = "🔧 Atualização"
            embed_color = discord.Color.blue()

        # traduzimos o corpo de cada post de forma não bloqueante
        descricao_original = post.get("body", "") or ""
        posts.append({
            "id": post.get("id"),
            "titulo": post.get("title", "Sem título"),
            "descricao_original": descricao_original,
            "data": post.get("created"),
            "imagem": post.get("thumbnailUrl"),
            "tipo": post_type,
            "cor": embed_color
        })
    return posts

# --------------------------
# Verifica atualizações por jogo (uma task por config)
# --------------------------
async def verificar_atualizacoes(game_id: str, channel_id: int, interval: int):
    # garante entrada no cache
    if game_id not in current_post_ids_cache:
        current_post_ids_cache[game_id] = set()

    await bot.wait_until_ready()

    # tenta buscar canal (fetch para garantir)
    try:
        canal = await bot.fetch_channel(channel_id)
    except Exception as e:
        print(f"Erro ao buscar canal {channel_id}: {e}")
        canal = None

    if canal is None:
        print(f"Canal {channel_id} não encontrado. Vou tentar novamente depois.")
    # Preencher cache inicial (não envia posts antigos)
    if not current_post_ids_cache[game_id]:
        print(f"[{game_id}] Preenchendo cache inicial...")
        initial_posts = await fetch_posts(game_id)
        current_post_ids_cache[game_id] = {p['id'] for p in initial_posts}
        print(f"[{game_id}] Cache inicial com {len(current_post_ids_cache[game_id])} posts.")

    while True:
        try:
            if canal is None:
                try:
                    canal = await bot.fetch_channel(channel_id)
                except Exception as e:
                    print(f"Erro ao (re)buscar canal {channel_id}: {e}")
                    canal = None

            novas_postagens = await fetch_posts(game_id)
            novas_para_enviar = [p for p in novas_postagens if p['id'] not in current_post_ids_cache[game_id]]

            # envia em ordem cronológica (do mais antigo pro mais novo)
            for post in reversed(novas_para_enviar):
                descricao_traduzida = await traduzir_para_pt(post["descricao_original"])

                # formata descrição (limita tamanho/linhas)
                linhas_desc = descricao_traduzida.split('\n')
                if len(descricao_traduzida) > 1024 or len(linhas_desc) > 8:
                    descricao_formatada = descricao_traduzida[:800] + "..."
                else:
                    descricao_formatada = ""
                    for i, linha in enumerate(linhas_desc):
                        if linha.strip():
                            descricao_formatada += f"{i+1}. {linha.strip()}\n"

                embed = discord.Embed(
                    title=f"{post['tipo']} - {post['titulo']}",
                    description=descricao_formatada or descricao_traduzida,
                    color=post['cor']
                )
                if post["imagem"]:
                    embed.set_image(url=post["imagem"])
                embed.set_footer(text=f"Publicado em: {post.get('data')}")

                if canal:
                    try:
                        await canal.send(embed=embed)
                        print(f"Enviado post {post['id']} para canal {channel_id}")
                    except Exception as e:
                        print(f"Erro ao enviar embed para canal {channel_id}: {e}")
                else:
                    print(f"Canal {channel_id} ainda não disponível, pulando envio.")

                await asyncio.sleep(1)  # pequeno intervalo entre envios

            if novas_para_enviar:
                current_post_ids_cache[game_id].update({p['id'] for p in novas_para_enviar})

        except Exception as e:
            print(f"Erro no loop de verificação para {game_id}: {e}")

        await asyncio.sleep(interval)

# --------------------------
# Eventos: canais temporários de voz
# --------------------------
@bot.event
async def on_voice_state_update(member, before, after):
    # se entrou no canal gatilho, cria temporário e move usuário
    if after.channel and after.channel.id == CHANNEL_TRIGGER_ID:
        guild = member.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(manage_channels=True)
        }

        category = guild.get_channel(CATEGORY_ID)
        try:
            temp_channel = await guild.create_voice_channel(
                name=f'Canal do {member.display_name}',
                overwrites=overwrites,
                category=category
            )
        except Exception as e:
            print("Erro ao criar canal temporário:", e)
            return

        try:
            await member.move_to(temp_channel)
        except Exception as e:
            print("Erro ao mover membro para canal temporário:", e)

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
            # canal pode já ter sido deletado fora do nosso fluxo
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
                except Exception as e:
                    await interaction.response.send_message('Erro ao editar a descrição do canal.', ephemeral=True)
            else:
                await interaction.response.send_message('Não foi possível encontrar seu canal.', ephemeral=True)
            return

    await interaction.response.send_message('Você não é dono de nenhum canal temporário ativo.', ephemeral=True)

# --------------------------
# Evento on_ready: inicia webserver, sincroniza comandos e inicia monitoramentos
# --------------------------
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user} (ID: {bot.user.id})")

    # start webserver uma vez
    if not hasattr(bot, 'webserver_started'):
        asyncio.create_task(start_webserver())
        bot.webserver_started = True

    # sincroniza comandos de aplicativo
    try:
        await tree.sync()
        print("Comandos sincronizados")
    except Exception as e:
        print("Erro ao sincronizar comandos:", e)

    # inicia uma task por configuração de jogo
    for conf in CONFIGURACOES:
        print(f"Iniciando monitoramento de {conf['NOME']} ({conf['GAME_ID']})")
        bot.loop.create_task(verificar_atualizacoes(conf["GAME_ID"], conf["CHANNEL_ID"], conf["INTERVALO"]))

# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("ERRO: variável de ambiente DISCORD_TOKEN não encontrada.")
    else:
        bot.run(TOKEN)
