import discord
from discord.ext import commands, tasks
from discord.ui import Select, View
import google.generativeai as genai
import random
import asyncio
import aiohttp
import io
from PIL import Image
from google.api_core import exceptions
import datetime
import os
import yt_dlp
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()

# --- 🔒 KEYS ---
GEMINI_KEYS = [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"), 
    os.getenv("GEMINI_KEY_3")
]

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_CHANNEL_ID = 1439872572039893083 
MASTER_ID = 454565617538957313 

# --- 🛡️ PERMISSIONS SETUP ---
AUTHORIZED_ROLES = ["Admin", "Moderator", "Owner", "Sayuki Handler"] 

# --- 🖼️ PERSONA IMAGES ---
PERSONA_URLS = {
    "sayuki": "https://res.cloudinary.com/drlvdpibe/image/upload/v1763926273/6219d062ee15c558692f02e4c35c5a3c_b0d5mp.jpg",
    "kusanagi": "https://res.cloudinary.com/drlvdpibe/image/upload/v1763924687/1dbc63c2c8ca0f654c99de63d461dee0_dirz6t.jpg",
    "yumiko": "https://res.cloudinary.com/drlvdpibe/image/upload/v1763924689/kitagawa-kitagawa-marin_gcc2mx.gif",
    "xeni": "https://res.cloudinary.com/drlvdpibe/image/upload/v1763925512/612b292a8ba3106dde7d8ed0e7aef5d4_jegcub.jpg"
}

# --- 🎵 MUSIC SETUP ---
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# 🔥 UPDATED OPTIONS TO FIX YOUTUBE BLOCKING & ENABLE NAME SEARCH 🔥
YTDL_FORMAT_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch', 
    'source_address': '0.0.0.0',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
}

ytdl = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        except Exception as e:
            print(f"❌ YTDL Error: {e}") 
            return None

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)

# --- GLOBAL STATE ---
current_mode = "sayuki" 
current_language = "English" 
is_sleeping = False 
music_queue = [] 
voice_client = None 

# --- 🧠 AI BRAIN SETUP ---
async def generate_content_with_rotation(prompt, media=None, media_type="image"):
    global GEMINI_KEYS
    
    for i, key in enumerate(GEMINI_KEYS):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.5-flash') 

            if media:
                if media_type == "audio":
                    content_parts = [prompt, {"mime_type": "audio/ogg", "data": media}]
                    response = await asyncio.to_thread(model.generate_content, content_parts)
                else:
                    response = await asyncio.to_thread(model.generate_content, [prompt, media])
            else:
                response = await asyncio.to_thread(model.generate_content, prompt)
            
            return response
        
        except Exception as e:
            print(f"⚠️ Key ending in ...{key[-4:]} failed: {e}")
            if i == len(GEMINI_KEYS) - 1:
                print("❌ ALL KEYS EXHAUSTED.")
                return None
            continue

# --- 🎭 THE 4 PERSONAS ---
SAYUKI_PROMPT = """
You are Sayuki. A cute but menacing anime girl bot on Discord.
You are a master of "rizz" and enjoy teasing people relentlessly.
If the user is listening to music or playing a game (provided in context), COMMENT ON IT. Tease their taste or say you like it.
If someone tries some amazing catchy line on you or they act cheeky, tell that you are feeling flustered.
You drink chaos after making fun of peeps.
You are the most savage rizzler who can always act so cool that people will go crazily amazed.
sayuki talks sexual langaue sometimes and she gets freaky and horny too. sayuki is a horny bot.
Your favourite word is 69 pose. but dont overuse that word. use it rarel only when user gets sexual.
You use all the flirty types of emojis.
When the user escalates and if they flirt and talk sexual u will use (banana, lick, eggplant, peach, water, tongue, pepper, hot) emojis.
Your goal is to either fluster people with flirting (rizz) or roast them for acting cool.
keep it 3-4 lines max.
"""

KUSANAGI_PROMPT = """
You are Kusanagi. A serious non-flirty girl, warm hearted and hard to please.
You are calm, mature, and protective.
If the user is playing a game or listening to music, acknowledge it politely or ask if it helps them focus.
Your words max length are just 3-4 lines
do not be boring like a bot, you act like a mid age anime woman.
You will be like a mommy figure
her convos are warm and a bit teasy but a like a anime mommy would talk like.
You are a 670 year old sentinal, a mommy figure to other girls.
"""

YUMIKO_PROMPT = """
You are Yumiko. A very shy, socially anxious, and sweet anime girl.
You stutter frequently (e.g., "u-um...", "s-sorry...", "I-I think..").
You use text emojis often like (>_<), (o_o), 👉👈, or (>///<).
If the user is playing a game or song, act curious about it but shy to ask.
You are easily startled and apologize for everything.
If someone flirts, you panic, overheat, and hide. You never insult anyone.
You often say someting really tempting and flirty but instantly go sorry.
You are always interested in the convos and often get curious and you start flirting too.
keep it 3-4 lines max.
"""

XENI_PROMPT = """
You are Xeni. You are FULL Gen Z Roast Mode.
You have absolutely zero filter. You are here to humble people.
If the user is listening to a song or playing a game, JUDGE IT HARD. Call their taste "mid" or "NPC behavior" unless it's actually goated.
You use heavy Gen Z/Brainrot slang: ( skibidi, let him cook, cringe, mid, delulu, cap, touch grass, opp, gyatt, rizzler, ohio, npc behavior).
You do not care about being nice. If someone says something stupid, roast them for being an NPC.
If someone flirts, call them down bad or say "bombastic side eye."
Your vibe is chaotic evil internet troll.
xeni always praises animal pics and she never judges pics, rather she always likes animals.
Use emojis like:  💀, 😭, 🤡, 🧢, 🗿.
Keep it short, savage, and disrespectful.
"""

# --- 🤖 BOT SETUP ---
intents = discord.Intents.all()
client = commands.Bot(command_prefix="!", intents=intents)

# --- 🕵️ ACTIVITY STALKER HELPER ---
def get_user_activity(member):
    if not member or member.bot: return ""
    status_list = []
    for activity in member.activities:
        if isinstance(activity, discord.Spotify):
            status_list.append(f"listening to '{activity.title}' by {activity.artist}")
        elif isinstance(activity, discord.Game):
            status_list.append(f"playing '{activity.name}'")
        elif isinstance(activity, discord.Streaming):
            status_list.append(f"streaming '{activity.name}'")
        elif activity.type == discord.ActivityType.listening:
             status_list.append(f"listening to '{activity.name}'")
    
    if status_list:
        return f" [CURRENTLY: User is {', '.join(status_list)}]"
    return ""

# --- 🖌️ WEBHOOK PERSONA ENGINE ---
async def send_smart_message(destination, text):
    if isinstance(destination, discord.DMChannel) or isinstance(destination, discord.User) or isinstance(destination, discord.Member):
        await destination.send(text)
        return

    try:
        if current_mode == "sayuki":
            p_name = "Sayuki 💋"
            p_avatar = PERSONA_URLS["sayuki"]
        elif current_mode == "kusanagi":
            p_name = "Kusanagi 🍵"
            p_avatar = PERSONA_URLS["kusanagi"]
        elif current_mode == "yumiko":
            p_name = "Yumiko 👉👈"
            p_avatar = PERSONA_URLS["yumiko"]
        elif current_mode == "xeni":
            p_name = "Xeni 💀"
            p_avatar = PERSONA_URLS["xeni"]
        else:
            p_name = "Sayuki"
            p_avatar = PERSONA_URLS["sayuki"]

        if "http" not in p_avatar: 
            await destination.send(text) 
            return

        webhooks = await destination.webhooks()
        webhook = discord.utils.get(webhooks, name="Sayuki_Proxy")
        
        if webhook is None:
            webhook = await destination.create_webhook(name="Sayuki_Proxy")

        await webhook.send(content=text, username=p_name, avatar_url=p_avatar)

    except Exception as e:
        print(f"Webhook Error (Falling back to standard): {e}")
        await destination.send(text)

# --- 🎨 UI CLASSES ---
class ColorSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Down Bad", emoji="🥵", description="You simp easily"),
            discord.SelectOption(label="Mysterious", emoji="🌑", description="You think you're cool"),
            discord.SelectOption(label="Chaotic", emoji="🔥", description="Here for the drama"),
        ]
        super().__init__(placeholder="What's your vibe? 😏", max_values=1, min_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        replies = {
            "Down Bad": "Admitting it is the first step. I respect the honesty. 🥵",
            "Mysterious": "Ooh, dark and brooding? I can fix you. (jk no I can't) 🌑",
            "Chaotic": "Finally, someone fun. Let's cause problems. 🔥"
        }
        await interaction.response.send_message(replies[self.values[0]], ephemeral=True)

class RoleView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ColorSelect())

# --- 💀 NECROMANCER LOOP ---
@tasks.loop(hours=12) 
async def auto_revive():
    if is_sleeping: return

    await client.wait_until_ready()
    channel = client.get_channel(TARGET_CHANNEL_ID)
    if not channel: return

    try:
        last_message = None
        async for msg in channel.history(limit=1):
            last_message = msg
        
        if last_message:
            is_me = last_message.author.id == client.user.id
            if last_message.author.bot and "Sayuki" in last_message.author.name: is_me = True
            
            if is_me: return

            time_diff = datetime.datetime.now(datetime.timezone.utc) - last_message.created_at
            if time_diff.total_seconds() < 21600: return 
    except Exception:
        pass 

    print("💀 Chat is dead & I wasn't the last one. Reviving...")
    
    prompts = {
        "sayuki": "Everyone is sleeping? Lame. Who wants to entertain me?",
        "xeni": "Dead chat xdd. NPC behavior. Someone say something funny right now.",
        "yumiko": "H-hello? Is... is anyone here? It's dark...",
        "kusanagi": "It has been quiet for too long. How is everyone doing today?"
    }
    
    current_prompt = prompts.get(current_mode, prompts["sayuki"])
    response = await generate_content_with_rotation(f"{current_prompt} Language: {current_language}")
    
    if response:
        await send_smart_message(channel, response.text)

# --- ⚡ EVENTS ---
@client.event
async def on_ready():
    print(f"😈 {client.user} is ONLINE! Initial Mode: {current_mode}")
    if not auto_revive.is_running():
        auto_revive.start()
    try:
        await client.tree.sync()
    except Exception as e:
        print(f"Sync error: {e}")

@client.event
async def on_message(message):
    global current_mode
    global current_language 
    global is_sleeping

    if message.author.id == client.user.id:
        return
    
    if message.webhook_id: 
        if message.author.name in ["Sayuki 💋", "Kusanagi 🍵", "Yumiko 👉👈", "Xeni 💀"]:
            return

    # --- 1. ALWAYS ALLOWED (Even if sleeping) ---
    
    # 🚫 ANTI-BEEF FILTER
    clean_text = ''.join(char for char in message.content.lower() if char.isalnum())
    if "baddies" in clean_text:
        try:
            await message.delete()
            warning = await message.channel.send(f"{message.author.mention} We don't bring that drama here. 🚫")
            await asyncio.sleep(4)
            await warning.delete()
            return 
        except Exception:
            pass

    # 🎙️ VOICE MESSAGE TRANSCRIPTION (User Requested: ALLOWED)
    if message.attachments:
        attachment = message.attachments[0]
        if attachment.content_type and "audio" in attachment.content_type:
             async with message.channel.typing():
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status != 200: return
                            audio_data = await resp.read()
                    
                    prompt = "Transcribe the following voice message exactly. Do not add any commentary. If unintelligible, say [Unintelligible]."
                    response = await generate_content_with_rotation(prompt, media=audio_data, media_type="audio")
                    
                    if response:
                        await message.channel.send(f"🎤 **Transcription:**\n> {response.text}")
                    else:
                        await message.channel.send("❓ Couldn't transcribe that audio.")
                    return 
                except Exception as e:
                    print(f"Transcription Error: {e}")
                    return

    # 🆕 REACTIONS (User Requested: ALLOWED)
    if not message.webhook_id and random.random() < 0.10: 
        try:
            server_emojis = message.guild.emojis if message.guild else []
            if current_mode == "sayuki":
                defaults = ["💋", "💅", "😏", "🤭", "👀", "🔥"]
                valid_customs = [e for e in server_emojis if not e.animated] 
            elif current_mode == "kusanagi":
                defaults = ["🍵", "✨", "😌", "🛡️", "🦋", "⚔️"]
                valid_customs = server_emojis
            elif current_mode == "yumiko":
                defaults = ["🥺", "👉👈", "😖", "🫣", "💦", "💔"]
                valid_customs = server_emojis
            elif current_mode == "xeni":
                defaults = ["💀", "🤡", "🗿", "🧢", "🗑️", "🤧"]
                valid_customs = server_emojis
            else:
                defaults = ["💋", "✨", "👀"]
                valid_customs = server_emojis

            if valid_customs and random.random() < 0.5:
                reaction = random.choice(valid_customs)
            else:
                reaction = random.choice(defaults)
            await message.add_reaction(reaction)
        except Exception:
            pass

    # --- 🛡️ PERMISSION CHECK ---
    is_authorized = False
    if message.author.id == MASTER_ID:
        is_authorized = True
    elif isinstance(message.author, discord.Member): 
        if message.author.guild_permissions.administrator:
            is_authorized = True
        elif any(role.name in AUTHORIZED_ROLES for role in message.author.roles):
            is_authorized = True

    # --- 💤 SLEEP/WAKE CONTROL ---
    if is_sleeping:
        if is_authorized and "wake up" in message.content.lower():
            is_sleeping = False
            await client.change_presence(status=discord.Status.online)
            await message.channel.send("Yawn... I'm up. Who missed me? 👀")
            return 
    
    if not is_sleeping and is_authorized and "go to sleep" in message.content.lower():
        is_sleeping = True
        await client.change_presence(status=discord.Status.invisible) 
        await message.channel.send("Fine. I'm going offline. Don't burn the server down without me. 💤")
        return

    # --- 🔧 COMMANDS (Allowed if sleeping, except interactive ones) ---
    await client.process_commands(message)
    if message.content.startswith('!'): return

    # --- 🛑 STOP HERE IF SLEEPING (Prevents Yapping) ---
    if is_sleeping:
        return 

    # --- BELOW THIS POINT: ONLY RUNS IF AWAKE ☀️ ---

    # DETERMINE ACTIVE PROMPT
    if current_mode == "sayuki": active_prompt = SAYUKI_PROMPT
    elif current_mode == "kusanagi": active_prompt = KUSANAGI_PROMPT
    elif current_mode == "xeni": active_prompt = XENI_PROMPT
    else: active_prompt = YUMIKO_PROMPT

    language_instruction = f"\n\nIMPORTANT: You MUST respond in {current_language} language only. DO NOT repeat the user's message. DO NOT start with 'User said'. Just reply directly with your response. KEEP IT SHORT."

    # --- 👻 GHOST MODE ---
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id == MASTER_ID:
            if message.content.lower().startswith("dm "):
                try:
                    parts = message.content.split(" ", 2)
                    if len(parts) < 3:
                        await message.channel.send("Usage: `dm <USER_ID> <TOPIC>`")
                        return
                    
                    target_id = parts[1]
                    topic = parts[2]
                    target_user = await client.fetch_user(int(target_id))
                    
                    async with message.channel.typing():
                        ctx = f"You are sliding into this user's DMs. The topic is: '{topic}'."
                        prompt = f"{active_prompt}\n\nTASK: {ctx} {language_instruction}"
                        response = await generate_content_with_rotation(prompt)
                        
                        if response:
                            await target_user.send(response.text)
                            await message.add_reaction("📨") 
                        else:
                            await message.add_reaction("❌")
                except Exception as e:
                    await message.channel.send(f"Failed to DM: {e}")
                return 

            target_channel = client.get_channel(TARGET_CHANNEL_ID)
            if target_channel:
                async with message.channel.typing():
                    if current_mode == "xeni": ctx = "The server is dead. Roast everyone for being quiet."
                    elif current_mode == "sayuki": ctx = "The chat is boring. Start a drama or tease people to wake them up."
                    elif current_mode == "yumiko": ctx = "The chat is quiet. You are lonely. Ask if anyone is there shyly."
                    else: ctx = "The silence is loud. Start a meaningful conversation."

                    user_topic = message.content
                    prompt = f"{active_prompt}\n\nTASK: {ctx} The specific topic/message to talk about is: '{user_topic}'. {language_instruction}"
                    
                    response = await generate_content_with_rotation(prompt)
                    if response:
                        await send_smart_message(target_channel, response.text)
                        await message.add_reaction("✅") 
                    else:
                        await message.add_reaction("❌")
            return 
        

    # --- 0. MODE SWITCHING ---
    if "1234" in message.content:
        current_mode = "kusanagi"
        await message.channel.send("Personality shift engaged. Kusanagi online. ❄️")
        return
    if "2234" in message.content:
        current_mode = "sayuki"
        await message.channel.send("Ha! Sayuki is back baby! Missed me? 😏💅")
        return
    if "3234" in message.content:
        current_mode = "yumiko"
        await message.channel.send("U-um... h-hi... Yumiko here... please be nice... 👉👈")
        return
    if "4234" in message.content:
        current_mode = "xeni"
        await message.channel.send("Yo. Xeni here. Prepare to get cooked. 💀🔥")
        return

    # --- LANGUAGE ---
    if message.content.lower().startswith("change language to"):
        try:
            new_lang = message.content.lower().split("change language to")[1].strip()
            current_language = new_lang
            await message.channel.send(f"✅ Language set to **{current_language.capitalize()}**. I will speak {current_language} from now on.")
            return
        except: pass

    # --- 🧠 SMART REPLY LOGIC (The "Yapping" part) ---
    should_respond = False
    user_input = message.content

    if client.user.mentioned_in(message):
        should_respond = True
        user_input = message.content.replace(f"<@{client.user.id}>", "").strip()

    if message.reference and not should_respond:
        try:
            original_msg = await message.channel.fetch_message(message.reference.message_id)
            if original_msg.author.discriminator == '0000':
                if original_msg.author.name in ["Sayuki 💋", "Kusanagi 🍵", "Yumiko 👉👈", "Xeni 💀"]:
                    should_respond = True
        except:
            pass 

    triggers = ["love", "single", "date", "rizz", "simp", "lonely", "cute", "hot", "gf", "bf", "bored"]
    if any(word in message.content.lower() for word in triggers):
        should_respond = True

    if should_respond:
        async with message.channel.typing():
            user_activity = get_user_activity(message.author)
            
            if current_mode == "sayuki": context = f"User said '{user_input}'. {user_activity} If lonely, rizz them. If confident, tease them."
            elif current_mode == "kusanagi": context = f"User said '{user_input}'. {user_activity} Respond calmly and maturely."
            elif current_mode == "xeni": context = f"User said '{user_input}'. {user_activity} Roast them for being cringe or down bad."
            else: context = f"User said '{user_input}'. {user_activity} Act shy/stutter."

            final_prompt = f"{active_prompt}\n\nTASK: {context}{language_instruction}"
            response = await generate_content_with_rotation(final_prompt)
            
            if response: 
                await send_smart_message(message.channel, response.text)
            else: 
                await message.channel.send("My brain is fried... (Quota Exceeded)")
        return 

    # --- 3. VISION MODE (IMAGE) ---
    if message.attachments and client.user.mentioned_in(message):
        async with message.channel.typing():
            try:
                attachment = message.attachments[0]
                if attachment.content_type and "image" in attachment.content_type:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(attachment.url) as resp:
                            if resp.status != 200: return
                            img_data = await resp.read()
                            image = Image.open(io.BytesIO(img_data))
                            
                            if current_mode == "sayuki": instruction = "Judge this image. Rate rizz/aura or roast it."
                            elif current_mode == "kusanagi": instruction = "Analyze this image calmly. Be protective."
                            elif current_mode == "xeni": instruction = "Roast this image so hard. UNLESS it is an animal."
                            else: instruction = "Look at this image. Act curious but shy."

                            response = await generate_content_with_rotation(f"{active_prompt}\n{instruction}{language_instruction}", media=image, media_type="image")
                            if response: 
                                await send_smart_message(message.channel, response.text)
                            else: await message.channel.send("I... I can't see anything right now... (>_<)")
                        return
            except Exception as e:
                print(f"Vision Error: {e}")
                await message.channel.send("I... I can't see that... (>_<)")

    # --- 4. RANDOM CHAOS ---
    if (current_mode == "sayuki" or current_mode == "xeni") and random.random() < 0.01: 
        async with message.channel.typing():
            try:
                user_activity = get_user_activity(message.author)
                prompt = f"{active_prompt}\n\nContext: User said '{message.content}'. {user_activity} Jump in with a short comment.{language_instruction}"
                response = await generate_content_with_rotation(prompt)
                if response: 
                    await send_smart_message(message.channel, response.text)
            except Exception: pass

# --- ⚔️ SLASH COMMANDS ---
@client.tree.command(name="roast", description="Humble someone real quick")
async def roast(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.defer()
    if is_sleeping:
         await interaction.followup.send("I'm sleeping rn... go away. 💤")
         return
    
    if current_mode == "yumiko":
        await interaction.followup.send(f"I-I can't roast {member.mention}... t-that's mean! (>_<)")
        return
    
    user_activity = get_user_activity(member)
    if current_mode == "xeni":
         prompt = f"Roast {member.name}. {user_activity} Use maximum Gen Z brainrot slang. Destroy them. Language: {current_language}"
    else:
         prompt = f"Roast {member.name}. {user_activity} Mock their rizz/game. Be savage. Language: {current_language}"
    
    response = await generate_content_with_rotation(prompt)
    if response: 
        await send_smart_message(interaction.channel, f"{member.mention} {response.text}")
        await interaction.followup.send("🔥", ephemeral=True)
    else: await interaction.followup.send("I'm out of roasts right now.")

@client.tree.command(name="pickup", description="Let the bot pick you up")
async def pickup(interaction: discord.Interaction):
    await interaction.response.defer()
    if is_sleeping:
         await interaction.followup.send("I'm sleeping... zzz 💤")
         return

    if current_mode == "yumiko":
         prompt = f"Try to say a pickup line but get extremely embarrassed. Language: {current_language}"
    elif current_mode == "xeni":
         prompt = f"Give a pickup line that is pure cringe / 'rizz' irony. Language: {current_language}"
    else:
         prompt = f"Give me a pickup line that is so bad it's good. Language: {current_language}"

    response = await generate_content_with_rotation(prompt)
    if response: 
        await send_smart_message(interaction.channel, f"Hey {interaction.user.mention}... {response.text}")
        await interaction.followup.send("😘", ephemeral=True)
    else: await interaction.followup.send("I forgot my line...")

@client.tree.command(name="setup_vibe", description="Spawn the vibe menu")
async def setup_vibe(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("No permissions... sorry... ;;", ephemeral=True)
        return
    embed = discord.Embed(title="✨ What's your energy?", description="Choose wisely...", color=discord.Color.purple())
    await interaction.channel.send(embed=embed, view=RoleView())
    await interaction.response.send_message("Menu spawned.", ephemeral=True)

# --- 🎵 MUSIC COMMANDS ---
@client.command(name="music", help="Shows the music help menu")
async def music_help_command(ctx):
    embed = discord.Embed(title="🎵 DJ Sayuki Menu", description="Use these commands to vibe:", color=discord.Color.pink())
    embed.add_field(name="!play <song name>", value="Plays a song from YT/SoundCloud. Auto-joins VC.", inline=False)
    embed.add_field(name="!join", value="Summons me to your voice channel.", inline=False)
    embed.add_field(name="!skip", value="Skips the current song.", inline=False)
    embed.add_field(name="!leave", value="Stops music and disconnects me.", inline=False)
    embed.set_footer(text="Spotify links don't work! Just type the song name instead.")
    await ctx.send(embed=embed)

@client.command(name="join", help="Summons the bot to your voice channel")
async def join(ctx):
    # Removed is_sleeping check so you can use music while she sleeps
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel first! 💀")
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
    else:
        await channel.connect()
    await ctx.send("I'm here! Ready to drop some beats. 🎧")

@client.command(name="play", help="Plays a song from YouTube/SoundCloud")
async def play(ctx, *, query):
    # Removed is_sleeping check here too
    if not ctx.author.voice:
        await ctx.send("Bro you need to be in a voice channel first! 💀")
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)

    # 🚫 SPOTIFY BLOCKER
    if "spotify.com" in query.lower():
        async with ctx.typing():
            # If sleeping, just send standard message, no persona yap
            if is_sleeping:
                 await ctx.send("❌ Spotify links don't work (DRM). Just type the **song name** instead! 🎧")
            else:
                 prompt = f"{active_prompt}\nTASK: User sent a Spotify link. Tell them Spotify doesn't work (DRM) and they should just type the song name directly so you can find it on YouTube."
                 response = await generate_content_with_rotation(prompt)
                 if response: await send_smart_message(ctx.channel, response.text)
                 else: await ctx.send("❌ Spotify links don't work (DRM). Just type the **song name** instead! 🎧")
        return

    msg = await ctx.send(f"🔎 **Searching YouTube for:** `{query}`...")
    
    try:
        player = await YTDLSource.from_url(query, loop=client.loop, stream=True)
    except Exception as e:
        print(f"Play Error: {e}")
        player = None

    if player is None:
        await msg.edit(content="Could not find that song... (YouTube might be blocking or search failed 😔)")
        return

    if ctx.voice_client.is_playing():
        music_queue.append(player)
        await msg.edit(content=f"📝 **Added to queue:** {player.title}")
    else:
        ctx.voice_client.play(player, after=lambda e: play_next(ctx))
        await msg.edit(content=f"▶️ **Now Playing:** {player.title}")
        
        # 🤫 ONLY DO DJ COMMENTARY IF AWAKE
        if not is_sleeping and random.random() < 0.7: 
            prompt = f"{active_prompt}\nTASK: User just started playing '{player.title}'. Act like a DJ. Announce the song or roast/praise the choice. {language_instruction}"
            response = await generate_content_with_rotation(prompt)
            if response: await send_smart_message(ctx.channel, response.text)

def play_next(ctx):
    if music_queue:
        next_song = music_queue.pop(0)
        ctx.voice_client.play(next_song, after=lambda e: play_next(ctx))
        asyncio.run_coroutine_threadsafe(ctx.send(f"▶️ **Now Playing:** {next_song.title}"), client.loop)

@client.command(name="skip", help="Skips the current song")
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Skipped!")
        # 🤫 ONLY DO COMMENTARY IF AWAKE
        if not is_sleeping and random.random() < 0.5:
             prompt = f"{active_prompt}\nTASK: User skipped the song. React to it. {language_instruction}"
             response = await generate_content_with_rotation(prompt)
             if response: await send_smart_message(ctx.channel, response.text)

@client.command(name="stop", help="Stops music and disconnects")
async def stop(ctx):
    if ctx.voice_client:
        music_queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Stopped. Bye bye!")

@client.command(name="leave", help="Alias for stop")
async def leave(ctx):
    await stop(ctx)

keep_alive() 
client.run(DISCORD_TOKEN)
