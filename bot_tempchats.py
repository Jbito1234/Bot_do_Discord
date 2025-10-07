import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiohttp
import os
from aiohttp import web
from googletrans import Translator

# --- Intents ---
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree
translator = Translator()

# ============================
# 🔧 CONFIGURAÇÕES GERAIS
# ============================
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

CHANNEL_TRIGGER_ID = 1424934971277185024  # Canal gatilho
CATEGORY_ID = 1424934711251439677         # Categoria para canais temporários
temp_channels = {}                        # Canais temporários ativos
current_post_ids_cache = {}               # Cache de posts já enviados


# ============================
# 🌐 FUNÇÕES: WEB SERVER
# ============================
async def handle(request):
    return web.Response(text='Bot ativo!')

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Webserver iniciado na porta 8080")


# ============================
# 🔔 FUNÇÕES: MONITOR DE ATUALIZAÇÕES
# ============================
async def fetch_posts(game_id):
    """Busca postagens do Roblox e traduz para PT-BR."""
    url = f"https://games.roblox.com/v1/games/{game_id}/universe-updates?sortOrder=Desc&limit=20"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                if r.status != 200:
                    print(f"Erro ao buscar posts para {game_id}: {r.status}")
                    return []
                data = await r.json()
    except Exception as e:
        print(f"Erro ao pegar postagens ({game_id}):", e)
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

    if not current_post_ids_cache[game_id]:
        print(f"[{game_id}] Cache inicial preenchido.")
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
                print(f"Erro ao enviar embed: {e}")
            await asyncio.sleep(5)

        if novas_para_enviar:
            current_post_ids_cache[game_id].update({p['id'] for p in novas_para_enviar})

        await asyncio.sleep(interval)


# ============================
# 🎙️ FUNÇÕES: CANAIS TEMPORÁRIOS
# ============================
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
        temp_channels[temp_channel.id] = {"owner_id": member.id}
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
@app_commands.describe(texto='Descrição do canal')
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


# ============================
# 🚀 EVENTO PRINCIPAL
# ============================
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

    # Inicia o webserver
    if not hasattr(bot, 'webserver_started'):
        asyncio.create_task(start_webserver())
        bot.webserver_started = True

    # Sincroniza comandos
    try:
        await tree.sync()
        print("Comandos sincronizados com sucesso")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    # Inicia monitoramento dos jogos
    for config in CONFIGURACOES:
        print(f"Iniciando monitoramento de {config['NOME']} ({config['GAME_ID']})")
        bot.loop.create_task(verificar_atualizacoes(
            config["GAME_ID"],
            config["CHANNEL_ID"],
            config["INTERVALO"]
        ))
        

# ============================
# 🔑 INICIAR BOT
# ============================
bot.run(os.getenv('DISCORD_TOKEN'))
