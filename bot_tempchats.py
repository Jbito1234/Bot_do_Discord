import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import os 

# ===============================
# Configurações Essenciais
# ===============================
# >>>>>> MUDAR AQUI <<<<<<
LOBBY_CHANNEL_ID = 1424934971277185024    # ID do canal de voz 'Lobby' que aciona a criação
TARGET_CATEGORY_ID = 1424934711251439677  # ID da categoria onde os canais TEMPORÁRIOS serão criados

BOT_TOKEN = os.getenv("DISCORD_TOKEN") 

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.voice_states = True # ESSENCIAL: Precisa deste intent para detectar entradas e saídas de voz
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
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    
    print("Webserver iniciado na porta 10000")
    
    # Mantém a tarefa viva indefinidamente.
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
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
# Lógica do Chat de Voz Temporário (NOVO)
# ===============================
@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    
    # --- 1. Lógica de DELEÇÃO ---
    # Verifica se o usuário saiu de um canal (before.channel existe)
    if before.channel and before.channel.id != LOBBY_CHANNEL_ID:
        # Verifica se o canal que ele saiu ficou vazio
        if len(before.channel.members) == 0:
            # Verifica se o canal está na categoria correta para ser deletado
            if before.channel.category_id == TARGET_CATEGORY_ID:
                print(f"Canal vazio detectado: {before.channel.name}. Deletando em 5 segundos...")
                
                # Atraso antes de deletar (conforme instrução)
                await asyncio.sleep(5) 
                
                try:
                    await before.channel.delete()
                    print(f"Canal {before.channel.name} deletado com sucesso.")
                except discord.Forbidden:
                    print("ERRO: Não tenho permissão para deletar este canal.")
                return

    # --- 2. Lógica de CRIAÇÃO ---
    # Verifica se o usuário entrou em um novo canal (after.channel existe)
    if after.channel and after.channel.id == LOBBY_CHANNEL_ID:
        guild = member.guild
        category = discord.utils.get(guild.categories, id=TARGET_CATEGORY_ID)
        
        if not category:
            print(f"ERRO: Categoria com ID {TARGET_CATEGORY_ID} não encontrada. Verifique as configurações.")
            # Move o usuário de volta se a categoria estiver errada
            await asyncio.sleep(1) # Atraso (conforme instrução)
            await member.move_to(None)
            return

        new_channel_name = f"Chat de {member.display_name}"
        
        # Atraso antes de criar o canal (conforme instrução)
        await asyncio.sleep(1) 
        
        try:
            # Cria o novo canal de voz na categoria especificada
            new_channel = await guild.create_voice_channel(
                name=new_channel_name,
                category=category
            )
            print(f"Canal temporário criado: {new_channel.name}")
            
            # Move o usuário para o novo canal
            await asyncio.sleep(0.5) # Atraso (conforme instrução)
            await member.move_to(new_channel)
            
        except discord.Forbidden:
            print("ERRO: O bot não tem permissão para criar ou mover canais na categoria.")
        except Exception as e:
            print(f"Erro ao criar/mover canal: {e}")

# ===============================
# Exemplo de comando
# ===============================
@bot.command()
async def ping(ctx):
    """Responde com 'Pong!' e a latência do bot."""
    latency_ms = round(bot.latency * 1000)
    await ctx.send(f"Pong! Latência: **{latency_ms}ms**")

# ===============================
# Função principal
# ===============================
async def main():
    if BOT_TOKEN is None:
        print("ERRO FATAL: Variável de ambiente 'DISCORD_TOKEN' não encontrada.")
        print("Por favor, defina o token do seu bot como uma variável de ambiente.")
        return

    webserver_task = asyncio.create_task(start_webserver())
    
    try:
        await bot.start(BOT_TOKEN)
    finally:
        webserver_task.cancel()
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
