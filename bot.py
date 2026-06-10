import discord
import asyncio
import aiohttp
import os
from datetime import datetime

# Token et Channel ID via variables d'environnement Railway
TOKEN = os.environ.get("TOKEN")
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", "0"))
MOTS_CLES = ["nike air force", "jordan 1", "stone island", "north face", "ralph lauren"]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

annonces_vues = set()

PRIX_REVENTE = {
    "nike air force": (45, 80),
    "jordan 1": (80, 150),
    "air max": (50, 100),
    "yeezy": (100, 200),
    "stone island": (60, 150),
    "north face": (40, 90),
    "ralph lauren": (20, 50),
    "lacoste": (20, 45),
    "adidas": (25, 60),
    "new balance": (40, 80),
}

def estimer_revente(titre, prix_achat):
    titre_lower = titre.lower()
    for marque, (mini, maxi) in PRIX_REVENTE.items():
        if marque in titre_lower:
            revente = round((mini + maxi) / 2)
            marge = revente - prix_achat
            return revente, marge
    revente = round(prix_achat * 1.8)
    marge = revente - prix_achat
    return revente, marge

def generer_description(titre, prix_achat, etat="très bon état"):
    return (
        f"✨ {titre} en {etat} !\n\n"
        f"📦 État : {etat.capitalize()}\n"
        f"📐 Taille indiquée dans les photos\n"
        f"🚚 Envoi rapide sous 24h\n"
        f"💬 N'hésitez pas à faire une offre !\n\n"
        f"#{titre.lower().replace(' ', '')} #vinted #mode #occasion"
    )

def verdict(marge):
    if marge >= 20:
        return "🟢 EXCELLENTE AFFAIRE"
    elif marge >= 10:
        return "🟡 BONNE AFFAIRE"
    elif marge >= 0:
        return "🟠 MARGE FAIBLE"
    else:
        return "🔴 PAS RENTABLE"

async def scraper_vinted(mot_cle):
    url = f"https://www.vinted.fr/api/v2/catalog/items?search_text={mot_cle.replace(' ', '+')}&per_page=20&order=newest_first"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("items", [])
    except Exception as e:
        print(f"Erreur scraping {mot_cle}: {e}")
    return []

async def surveiller():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)
    print(f"✅ Bot démarré - Surveillance de {len(MOTS_CLES)} mots-clés")

    while not client.is_closed():
        for mot in MOTS_CLES:
            items = await scraper_vinted(mot)
            for item in items:
                item_id = str(item.get("id"))
                if item_id in annonces_vues:
                    continue
                annonces_vues.add(item_id)

                titre = item.get("title", "Article")
                prix_achat = float(item.get("price", 0))
                etat = item.get("status", "bon état")
                lien = f"https://www.vinted.fr/items/{item_id}"
                photo = item.get("photo", {}).get("url", "")

                revente, marge = estimer_revente(titre, prix_achat)
                desc = generer_description(titre, prix_achat, etat)

                if marge < 5:
                    continue

                embed = discord.Embed(
                    title=f"🛍️ {titre}",
                    url=lien,
                    color=0x00FF88 if marge >= 20 else 0xFFAA00 if marge >= 10 else 0xFF6600
                )
                embed.add_field(name="💸 Prix achat", value=f"{prix_achat}€", inline=True)
                embed.add_field(name="📈 Prix revente estimé", value=f"{revente}€", inline=True)
                embed.add_field(name="💰 Marge potentielle", value=f"+{marge}€", inline=True)
                embed.add_field(name="🏷️ État", value=etat, inline=True)
                embed.add_field(name="📊 Verdict", value=verdict(marge), inline=True)
                embed.add_field(name="📝 Description prête", value=desc, inline=False)
                embed.add_field(name="🔗 Lien", value=lien, inline=False)
                if photo:
                    embed.set_thumbnail(url=photo)
                embed.set_footer(text=f"Vinted Bot • {datetime.now().strftime('%H:%M:%S')}")

                await channel.send(embed=embed)

        await asyncio.sleep(300)

@client.event
async def on_ready():
    print(f"✅ Connecté en tant que {client.user}")
    client.loop.create_task(surveiller())

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("!prix"):
        parts = message.content.split()
        if len(parts) >= 3:
            try:
                prix_achat = float(parts[-1])
                titre = " ".join(parts[1:-1])
                revente, marge = estimer_revente(titre, prix_achat)
                await message.channel.send(
                    f"**{titre}**\n"
                    f"💸 Achat : {prix_achat}€\n"
                    f"📈 Revente estimée : {revente}€\n"
                    f"💰 Marge : +{marge}€\n"
                    f"📊 {verdict(marge)}"
                )
            except:
                await message.channel.send("Usage : `!prix nom article prix_achat` (ex: `!prix nike air force 35`)")

    if message.content.startswith("!desc"):
        titre = message.content[6:].strip()
        if titre:
            desc = generer_description(titre, 0)
            await message.channel.send(f"📝 Description générée :\n```{desc}```")

    if message.content.startswith("!alerte"):
        mot = message.content[8:].strip()
        if mot and mot not in MOTS_CLES:
            MOTS_CLES.append(mot)
            await message.channel.send(f"✅ Alerte ajoutée pour : **{mot}**")
        else:
            await message.channel.send("⚠️ Mot-clé déjà surveillé ou invalide.")

    if message.content == "!alertes":
        liste = "\n".join([f"• {m}" for m in MOTS_CLES])
        await message.channel.send(f"🔍 Mots-clés surveillés :\n{liste}")

    if message.content == "!aide":
        await message.channel.send(
            "**Commandes disponibles :**\n"
            "`!prix [article] [prix]` → Calcule la rentabilité\n"
            "`!desc [article]` → Génère une description\n"
            "`!alerte [mot-clé]` → Ajoute une alerte\n"
            "`!alertes` → Liste vos alertes\n"
            "`!aide` → Affiche ce message"
        )

client.run(TOKEN)
