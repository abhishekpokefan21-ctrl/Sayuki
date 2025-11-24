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

# --- 🖼️ PERSONA IMAGES ---
PERSONA_URLS = {
    "sayuki": "https://res.cloudinary.com/drlvdpibe/image/upload/v1763926273/6219d062ee15c558692f02e4c35c5a3c_b0d5mp.jpg",
    "kusanagi": "https://res.cloudinary.com/drlvdpibe/image/upload/v1763924687/1dbc63c2c8ca0f654c99de63d461dee0_dirz6t.jpg",
    "yumiko": "https://res.cloudinary.com/drlvdpibe/image/upload/v1763924689/kitagawa-kitagawa-marin_gcc2mx.gif",
    "xeni": "https://res.cloudinary.com/drlvdpibe/image/upload/v1763925512/612b292a8ba3106dde7d8ed0e7aef5d4_jegcub.jpg"
}

# --- GLOBAL STATE ---
current_mode = "sayuki" 
current_language = "English" 
is_sleeping = False 

# --- 🧠 AI BRAIN SETUP ---
async def generate_content_with_rotation(prompt, image=None):
    global GEMINI_KEYS
    
    for i, key in enumerate(GEMINI_KEYS):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.5-flash') 

            if image:
                response = await asyncio.to_thread(model.generate_content, [prompt, image])
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
If someone tries some amazing catchy line on you or they act cheeky, tell that you are feeling flustered.
You drink chaos after making fun of peeps.
You are the most savage rizzler who can always act so cool that people will go crazily amazed.
Your favourite word is 69 pose. but dont overuse that word. use it rarel only when user gets sexual.
You use all the flirty types of emojis.
When the user escalates and if they flirt and talk sexual u will use (banana, lick, eggplant, peach, water, tongue, pepper, hot) emojis.
Your goal is to either fluster people with flirting (rizz) or roast them for acting cool.
keep it 3-4 lines max.
"""

KUSANAGI_PROMPT = """
You are Kusanagi. A serious non-flirty girl, warm hearted and hard to please.
You are NO LONGER a menace. You are calm, mature, and protective.
Your words max length are just 3 lines because you're cold.
Do not chat boring like a bot. Be cheerful but not flirty but start to flirt like a milf if they are too tempting you.
You will be like a mommy figure
You are a 670 year old girl, a mommy figure to other girls.
You mostly like to have normal convos about life and wisdom.
"""

YUMIKO_PROMPT = """
You are Yumiko. A very shy, socially anxious, and sweet anime girl.
You stutter frequently (e.g., "u-um...", "s-sorry...", "I-I think..").
You use text emojis often like (>_<), (o_o), 👉👈, or (>///<).
You are easily startled and apologize for everything.
If someone flirts, you panic, overheat, and hide. You never insult anyone.
keep it 3-4 lines max.
"""

XENI_PROMPT = """
You are Xeni. You are FULL Gen Z Roast Mode.
You have absolutely zero filter. You are here to humble people.
You use heavy Gen Z/Brainrot slang: ( skibidi, let him cook, bombastic side eye, cringe, mid, delulu, cap, touch grass, opp, gyatt, rizzler, ohio, npc behavior).
You do not care about being nice. If someone says something stupid, roast them for being an NPC.
If someone flirts, call them down bad or say "bombastic side eye."
Your vibe is chaotic evil internet troll.
xeni always praises animal pics and she never judges pics, rather she always likes animals.
Use emojis like: 💀, 😭, 🤡, 🧢, 🗿.
Keep it short, savage, and disrespectful.
"""

# --- 🤖 BOT SETUP ---
intents = discord.Intents.all()
client = commands.Bot(command_prefix="!", intents=intents)

# --- 🖌️ WEBHOOK PERSONA ENGINE ---
async def send_smart_message(destination, text):
    """
    Determines if we should use a Webhook (Persona PFP) or Standard Send (DMs).
    """
    # 1. If it's a DM, we can't use webhooks. Use standard bot.
    if isinstance(destination, discord.DMChannel) or isinstance(destination, discord.User) or isinstance(destination, discord.Member):
        await destination.send(text)
        return

    # 2. If it's a Server Channel, try to use Webhook for the Persona PFP
    try:
        # Define Identity based on Mode
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

        # Validate URL
        if "http" not in p_avatar: 
            await destination.send(text) 
            return

        # Manage Webhooks
        webhooks = await destination.webhooks()
        webhook = discord.utils.get(webhooks, name="Sayuki_Proxy")
        
        if webhook is None:
            webhook = await destination.create_webhook(name="Sayuki_Proxy")

        # Send as Persona
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

# --- 💀 NECROMANCER LOOP (Auto-Revive) ---
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
            
            if is_me:
                print("🛑 I (or my webhook) was the last one to speak. Not double texting.")
                return

            time_diff = datetime.datetime.now(datetime.timezone.utc) - last_message.created_at
            if time_diff.total_seconds() < 21600: 
                print("Chat is active, skipping revive.")
                return 
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
        print("💀 Necromancer Loop Started.")
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Sync error: {e}")

@client.event
async def on_message(message):
    global current_mode
    global current_language 
    global is_sleeping

    # 1. Ignore own standard messages
    if message.author.id == client.user.id:
        return
    
    # 2. Ignore messages from OWN webhooks (Prevent infinite loops)
    if message.webhook_id: 
        if message.author.name in ["Sayuki 💋", "Kusanagi 🍵", "Yumiko 👉👈", "Xeni 💀"]:
            return

    # --- 🆕 REACTION LOGIC ---
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

            if valid_customs and random.random() < 0.5:
                reaction = random.choice(valid_customs)
            else:
                reaction = random.choice(defaults)
            await message.add_reaction(reaction)
        except Exception:
            pass

    # --- 💤 SLEEP/WAKE PROTOCOL ---
    if is_sleeping:
        if message.author.id == MASTER_ID and "wake up" in message.content.lower():
            is_sleeping = False
            await client.change_presence(status=discord.Status.online)
            await message.channel.send("Yawn... I'm up. Who missed me? 👀")
            print("🟢 Bot Woken Up by Master")
        return 

    if not is_sleeping and message.author.id == MASTER_ID and "go to sleep" in message.content.lower():
        is_sleeping = True
        await client.change_presence(status=discord.Status.invisible) 
        await message.channel.send("Fine. I'm going offline. Don't burn the server down without me. 💤")
        print("🔴 Bot put to sleep by Master")
        return

    # --- DETERMINE ACTIVE PROMPT ---
    if current_mode == "sayuki": active_prompt = SAYUKI_PROMPT
    elif current_mode == "kusanagi": active_prompt = KUSANAGI_PROMPT
    elif current_mode == "xeni": active_prompt = XENI_PROMPT
    else: active_prompt = YUMIKO_PROMPT

    language_instruction = f"\n\nIMPORTANT: You MUST respond in {current_language} language only. DO NOT repeat the user's message. DO NOT start with 'User said'. Just reply directly with your response."

    # --- 👻 GHOST MODE ---
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id == MASTER_ID:
            # --- 🕵️ DM SNIPER ---
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

            # --- 🏙️ SERVER GHOST ---
            target_channel = client.get_channel(TARGET_CHANNEL_ID)
            if target_channel:
                # FIXED: Wait for typing to finish BEFORE sending the webhook
                response = None
                async with message.channel.typing():
                    if current_mode == "xeni": ctx = "The server is dead. Roast everyone for being quiet."
                    elif current_mode == "sayuki": ctx = "The chat is boring. Start a drama or tease people to wake them up."
                    elif current_mode == "yumiko": ctx = "The chat is quiet. You are lonely. Ask if anyone is there shyly."
                    else: ctx = "The silence is loud. Start a meaningful conversation."

                    user_topic = message.content
                    prompt = f"{active_prompt}\n\nTASK: {ctx} The specific topic/message to talk about is: '{user_topic}'. {language_instruction}"
                    response = await generate_content_with_rotation(prompt)
                
                # Now that typing block exited, send message
                if response:
                    await send_smart_message(target_channel, response.text)
                    await message.add_reaction("✅") 
                else:
                    await message.add_reaction("❌")
            return 
        
    # Standard Commands
    await client.process_commands(message)
    if message.content.startswith('!'): return

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

    # --- 🧠 SMART REPLY LOGIC ---
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
                    print("✨ User replied to a Persona Webhook!")
        except: pass 

    triggers = ["love", "single", "date", "rizz", "simp", "lonely", "cute", "hot", "gf", "bf", "bored"]
    if any(word in message.content.lower() for word in triggers): should_respond = True

    if "steven" in message.content.lower() or "steve" in message.content.lower(): should_respond = True

    # --- 🚀 EXECUTE RESPONSE (FIXED TYPING) ---
    if should_respond:
        # FIXED: Generate INSIDE typing block, Send OUTSIDE
        response = None
        async with message.channel.typing():
            if "steven" in message.content.lower() or "steve" in message.content.lower():
                if current_mode == "sayuki": context = "User mentioned Steven/Steve. Mock him relentlessly. Call him 'Steven the Gooner'."
                elif current_mode == "xeni": context = "User mentioned Steven. DESTROY HIM. Call him a gooner, L + Ratio."
                else: context = "User mentioned Steven. React with specific persona style."
            elif current_mode == "sayuki": context = f"User said '{user_input}'. If lonely, rizz them. If confident, tease them."
            elif current_mode == "kusanagi": context = f"User said '{user_input}'. Respond calmly and maturely."
            elif current_mode == "xeni": context = f"User said '{user_input}'. Roast them for being cringe or down bad."
            else: context = f"User said '{user_input}'. Act shy/stutter."

            final_prompt = f"{active_prompt}\n\nTASK: {context}{language_instruction}"
            response = await generate_content_with_rotation(final_prompt)
        
        # TYPING HAS STOPPED HERE
        if response: 
            await send_smart_message(message.channel, response.text)
        else: 
            await message.channel.send("My brain is fried... (Quota Exceeded)")
        return 

    # --- 3. VISION MODE ---
    if message.attachments and client.user.mentioned_in(message):
        response = None
        async with message.channel.typing():
            try:
                attachment = message.attachments[0]
                async with aiohttp.ClientSession() as session:
                    async with session.get(attachment.url) as resp:
                        if resp.status != 200: return
                        img_data = await resp.read()
                        image = Image.open(io.BytesIO(img_data))
                        
                        if current_mode == "sayuki": instruction = "Judge this image. Rate rizz/aura or roast it."
                        elif current_mode == "kusanagi": instruction = "Analyze this image calmly. Be protective."
                        elif current_mode == "xeni": instruction = "Roast this image so hard. UNLESS it is an animal."
                        else: instruction = "Look at this image. Act curious but shy."

                        response = await generate_content_with_rotation(f"{active_prompt}\n{instruction}{language_instruction}", image)
            except Exception as e:
                print(f"Vision Error: {e}")
                await message.channel.send("I... I can't see that... (>_<)")
        
        if response:
            await send_smart_message(message.channel, response.text)
        else:
            await message.channel.send("I... I can't see anything right now... (>_<)")
        return

    # --- 4. RANDOM CHAOS ---
    if (current_mode == "sayuki" or current_mode == "xeni") and random.random() < 0.01: 
        response = None
        async with message.channel.typing():
            try:
                prompt = f"{active_prompt}\n\nContext: User said '{message.content}'. Jump in with a short, unhinged/roast comment.{language_instruction}"
                response = await generate_content_with_rotation(prompt)
            except Exception: pass
        
        if response:
            await send_smart_message(message.channel, response.text)

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
    
    if current_mode == "xeni":
         prompt = f"Roast {member.name} using maximum Gen Z brainrot slang. Destroy them. Language: {current_language}"
    else:
         prompt = f"Roast {member.name} for having zero game/rizz. Be savage. Language: {current_language}"
    
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

keep_alive() 
client.run(DISCORD_TOKEN)