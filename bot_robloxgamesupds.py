import discord
import requests
import asyncio
from googletrans import Translator

# --- 1. Informações de Configuração Global ---
# O token do seu bot (ÚNICO para todas as verificações)
TOKEN = "SEU_TOKEN_DO_BOT" 

# Lista de configurações: Adicione quantos jogos você quiser aqui!
CONFIGURACOES = [
    {
        "GAME_ID": "111111111",      # ID do primeiro jogo no Roblox
        "CHANNEL_ID": 123456789,     # ID do canal para as notas do Jogo A
        "NOME": "Jogo A",
        "INTERVALO": 20              # Intervalo de checagem em segundos (20s)
    },
    {
        "GAME_ID": "222222222",      # ID do segundo jogo no Roblox
        "CHANNEL_ID": 987654321,     # ID do canal para as notas do Jogo B
        "NOME": "Jogo B",
        "INTERVALO": 30              # Intervalo de checagem em segundos (30s)
    }
    # Adicione mais objetos de configuração aqui, seguindo o padrão acima.
]
# -----------------------------------

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)
translator = Translator()

# Dicionário para armazenar os IDs de postagens vistas, separadamente para cada jogo.
# A chave é o GAME_ID.
current_post_ids_cache = {} 


async def fetch_posts(game_id):
    """Busca as últimas postagens de atualização/evento do Roblox e as traduz."""
    url = f"https://games.roblox.com/v1/games/{game_id}/universe-updates?sortOrder=Desc&limit=20"
    try:
        r = requests.get(url)
        if r.status_code != 200:
            print(f"Erro ao buscar posts para o Jogo {game_id}: Status {r.status_code}")
            return []
            
        data = r.json().get("data", [])
        posts = []
        for post in data:
            title_lower = post.get("title", "").lower()
            
            # Determina o tipo de postagem e cor
            if "event" in title_lower or "evento" in title_lower:
                post_type = "🎉 Evento"
                embed_color = discord.Color.gold()
            else:
                post_type = "🔧 Atualização"
                embed_color = discord.Color.blue()

            # Traduz a descrição para português
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
    except Exception as e:
        print(f"Erro ao pegar postagens para {game_id}:", e)
        return []

async def verificar_atualizacoes(game_id, channel_id, interval):
    """Verifica e publica novas atualizações para um jogo e canal específicos."""
    
    # Garante que o set de IDs para este jogo exista
    if game_id not in current_post_ids_cache:
        current_post_ids_cache[game_id] = set()
    
    await bot.wait_until_ready()
    canal = bot.get_channel(channel_id)
    
    if canal is None:
        print(f"Canal {channel_id} para o jogo {game_id} não encontrado.")
        # Pausa e retorna se o canal não for encontrado
        print("sleep")
        await asyncio.sleep(interval)
        return

    # --- Lógica Inicial (Preenchimento do Cache) ---
    if not current_post_ids_cache[game_id]:
        print(f"[{game_id}] Primeira execução: Preenchendo cache de posts existentes...")
        initial_posts = await fetch_posts(game_id)
        current_post_ids_cache[game_id] = {post['id'] for post in initial_posts}
        print(f"[{game_id}] Cache preenchido com {len(current_post_ids_cache[game_id])} postagens iniciais.")
        
        # Pausa conforme regra de 'sleep'
        print("sleep")
        await asyncio.sleep(interval)
        return 

    # --- Loop de Checagem Contínua ---
    while True:
        novas_postagens = await fetch_posts(game_id)
        novas_para_enviar = []
        
        # Encontra as postagens novas
        for post in reversed(novas_postagens):
            if post['id'] not in current_post_ids_cache[game_id]:
                novas_para_enviar.append(post)

        # Envia as novas postagens
        for post in novas_para_enviar:
            
            # --- Formatação do Design Inspirado na Imagem ---
            descricao_formatada = ""
            linhas_desc = post["descricao"].split('\n')
            
            # Formatação da descrição para simular lista/itens
            if len(post["descricao"]) > 1024 or len(linhas_desc) > 8:
                descricao_formatada = post["descricao"][:800] + "..."
                descricao_formatada = f"{post['tipo'].split(' ')[1]}:\n" + \
                                      f"{descricao_formatada}\n\n" + \
                                      f"... Pontos de Notas!\n"
            else:
                for i, linha in enumerate(linhas_desc):
                    if linha.strip():
                        descricao_formatada += f"{i+1}.** {linha.strip()}\n"
                
                if len(descricao_formatada) > 4096:
                    descricao_formatada = descricao_formatada[:4000] + "\n*(Descrição cortada...)*"
            
            # Cria o Embed (sem set_author, para que o bot apareça como remetente padrão)
            embed = discord.Embed(
                title=f"#{'🔧' if post['tipo'].startswith('Atualização') else '🎉'} | Notas de {post['tipo'].split(' ')[1]} - {game_id}!",
                description=f"*Bem-vindo(a) a* {post['tipo']} *| {post['titulo']}*\n\n" + 
                            descricao_formatada,
                color=post['cor']
            )
            
            if post["imagem"]:
                embed.set_image(url=post["imagem"])
                
            embed.set_footer(text=f"Publicado em: {post['data']}")
            
            await canal.send(embed=embed)
            
            # --- Pausa entre o envio das notas (Regra do Usuário) ---
            print("sleep")
            await asyncio.sleep(5) 
            # -----------------------------------------------------------

        # Atualiza o cache de IDs
        if novas_para_enviar:
            current_post_ids_cache[game_id].update({post['id'] for post in novas_para_enviar})

        # --- Pausa no final do loop principal ---
        print("sleep")
        await asyncio.sleep(interval)


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    
    # Inicia uma tarefa assíncrona para CADA jogo na configuração
    for config in CONFIGURACOES:
        print(f"Iniciando monitoramento para {config['NOME']} ({config['GAME_ID']}) no Canal {config['CHANNEL_ID']}")
        bot.loop.create_task(
            verificar_atualizacoes(
                config["GAME_ID"], 
                config["CHANNEL_ID"], 
                config["INTERVALO"]
            )
        )

# Inicia o bot com o ÚNICO TOKEN
bot.run(TOKEN)
