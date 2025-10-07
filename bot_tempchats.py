import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from aiohttp import web
import os

# Configura os intents, incluindo membros e estados de voz
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True  # Intents privilegiado, ativa no portal do Discord!

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ID do canal que serve como gatilho para criar canais temporários
CHANNEL_TRIGGER_ID = 1424936435051397183  # Troque pelo seu ID

# Dicionário para guardar os canais temporários criados e seus donos
temp_channels = {}

@bot.event
async def on_ready():
    print(f"Logado como {bot.user}")
    try:
        await tree.sync()
        print("Comandos slash sincronizados")
    except Exception as e:
        print(f"Erro ao sincronizar comandos: {e}")

    # Inicia o webserver apenas uma vez para manter o bot ativo
    if not hasattr(bot, 'webserver_started'):
        asyncio.create_task(start_webserver())
        bot.webserver_started = True

@bot.event
async def on_voice_state_update(member, before, after):
    # Quando o usuário entra no canal gatilho, cria um canal temporário pra ele
    if after.channel and after.channel.id == CHANNEL_TRIGGER_ID:
        guild = member.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=True),
            member: discord.PermissionOverwrite(manage_channels=True)
        }

        temp_channel = await guild.create_voice_channel(
            name=f'Canal do {member.display_name}',
            overwrites=overwrites,
            category=after.channel.category
        )

        await member.move_to(temp_channel)

        temp_channels[temp_channel.id] = {
            "owner_id": member.id,
            "channel": temp_channel
        }

        asyncio.create_task(check_empty_channel(temp_channel))

async def check_empty_channel(channel):
    await asyncio.sleep(5)  # Espera pra evitar delete falso
    while True:
        if len(channel.members) == 0:
            try:
                await channel.delete()
            except Exception as e:
                print(f"Erro ao deletar canal: {e}")
            temp_channels.pop(channel.id, None)
            break
        await asyncio.sleep(10)

# Comando slash para definir descrição do canal temporário
@tree.command(name='descricao', description='Define a descrição do seu canal de voz temporário.')
@app_commands.describe(texto='Descrição para o canal')
async def descricao(interaction: discord.Interaction, texto: str):
    user = interaction.user
    for data in temp_channels.values():
        if data['owner_id'] == user.id:
            channel = data['channel']
            await channel.edit(topic=texto)
            await interaction.response.send_message(f'Descrição definida: {texto}', ephemeral=True)
            return

    await interaction.response.send_message('Você não é dono de nenhum canal temporário ativo.', ephemeral=True)

# Webserver simples para manter o bot acordado (útil em serviços tipo Render)
async def handle(request):
    return web.Response(text='Bot ativo!')

async def start_webserver():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

# Inicia o bot pegando o token da variável de ambiente DISCORD_TOKEN
bot.run(os.getenv('DISCORD_TOKEN'))
