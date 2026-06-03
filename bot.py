"""
MantisTrackerBot — Crypto Airdrop Tracker
Telegram: @Mantis_Tracker_Bot
Features: Multilingual (EN/ES), Mini App, Wallet Tracker,
          Weekly Leaderboard, Airdrop Submissions, Daily Digest,
          Scam Safety Scoring, Chain Filters
"""

import logging
import asyncio
import json
import os
import hashlib
import re
from datetime import datetime, time as dtime

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    BotCommand, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

from airdrop_sources import fetch_all_airdrops, PRIORITY_CHAINS

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

MINI_APP_URL      = os.environ.get("MINI_APP_URL", "")
CHANNEL_ID        = os.environ.get("CHANNEL_ID", "")   # e.g. @MantisAirdrops
SUBMISSIONS_SHEET = os.environ.get("SUBMISSIONS_URL", "https://forms.gle/YOUR_FORM_ID")

DAILY_HOUR   = 8
DAILY_MINUTE = 0
WEEKLY_DAY   = 6   # Sunday = 6

DATA_FILE        = "airdrop_data.json"
USERS_FILE       = "users.json"
SUBMISSIONS_FILE = "submissions.json"
LEADERBOARD_FILE = "leaderboard.json"
WALLETS_FILE     = "wallets.json"

CHAIN_EMOJIS = {
    "SOL": "◎", "BTC": "₿", "ETH": "Ξ",
    "BNB": "🔶", "BASE": "🔵", "ARB": "🔷",
    "MATIC": "🟣", "AVAX": "🔺", "OTHER": "🪙",
}

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── TRANSLATIONS ─────────────────────────────────────────────────────────────

STRINGS = {
    "en": {
        "welcome": (
            "🦗 *Welcome to MantisTrackerBot!*\n\n"
            "Your personal crypto airdrop radar.\n\n"
            "Tracking: SOL ◎ | BTC ₿ | ETH Ξ | BNB 🔶\n\n"
            "📅 Daily digest every morning at *8AM UTC*\n"
            "🛡️ Every listing safety-scored 0–10\n"
            "🔍 Filter by chain\n\n"
            "_Golden Rule: If it asks for your seed phrase "
            "or to send crypto — it is a SCAM._"
        ),
        "btn_dashboard":  "🚀 Open Dashboard",
        "btn_airdrops":   "📋 Today's Airdrops",
        "btn_new":        "🆕 New Today",
        "btn_filter":     "⚙️ Chain Filters",
        "btn_safety":     "🛡️ Safety Guide",
        "btn_tips":       "💡 Security Tips",
        "btn_status":     "📊 Bot Status",
        "btn_wallet":     "👛 Track Wallet",
        "btn_submit":     "📝 Submit Airdrop",
        "btn_leaderboard":"🏆 Leaderboard",
        "btn_language":   "🌐 Language / Idioma",
        "btn_help":       "❓ Help",
        "no_airdrops":    "😕 No safe airdrops for your current filters.\nUse /filter to adjust or /refresh to update.",
        "refreshing":     "🔄 Refreshing airdrop data...",
        "refresh_done":   "✅ Done! Use /airdrops to see the latest.",
        "filters_saved":  "✅ Filters saved! Use /airdrops to see your list.",
        "wallet_prompt":  "👛 *Wallet Tracker*\n\nSend me your wallet address and I will check it against current airdrops.\n\nSupports: ETH, SOL, BNB addresses\n\n⚠️ _We never store private keys — address only._",
        "submit_prompt":  (
            "📝 *Submit an Airdrop*\n\n"
            "Want your project listed on MantisTracker?\n\n"
            "Fill out our submission form:\n"
            "{url}\n\n"
            "✅ *Listing includes:*\n"
            "• Safety review before publishing\n"
            "• Chain and status badge\n"
            "• Estimated value display\n"
            "• Reach to all subscribers\n\n"
            "🛡️ *Safety requirements:*\n"
            "• Must be free to claim\n"
            "• Must have official website\n"
            "• Must have verifiable social presence\n"
            "• No seed phrase or private key requirements\n"
            "• No send-to-claim mechanics\n\n"
            "Submissions reviewed within 24–48 hours."
        ),
        "lang_select":    "🌐 *Select Language*\n\nChoose your preferred language:",
        "lang_set":       "✅ Language set to English!",
    },
    "es": {
        "welcome": (
            "🦗 *¡Bienvenido a MantisTrackerBot!*\n\n"
            "Tu radar personal de airdrops de criptomonedas.\n\n"
            "Rastreando: SOL ◎ | BTC ₿ | ETH Ξ | BNB 🔶\n\n"
            "📅 Resumen diario cada mañana a las *8AM UTC*\n"
            "🛡️ Cada listado con puntuación de seguridad 0–10\n"
            "🔍 Filtra por cadena\n\n"
            "_Regla de oro: Si pide tu frase semilla o enviar cripto — es una ESTAFA._"
        ),
        "btn_dashboard":  "🚀 Abrir Panel",
        "btn_airdrops":   "📋 Airdrops de Hoy",
        "btn_new":        "🆕 Nuevos Hoy",
        "btn_filter":     "⚙️ Filtros de Cadena",
        "btn_safety":     "🛡️ Guía de Seguridad",
        "btn_tips":       "💡 Consejos de Seguridad",
        "btn_status":     "📊 Estado del Bot",
        "btn_wallet":     "👛 Rastrear Billetera",
        "btn_submit":     "📝 Enviar Airdrop",
        "btn_leaderboard":"🏆 Clasificación",
        "btn_language":   "🌐 Language / Idioma",
        "btn_help":       "❓ Ayuda",
        "no_airdrops":    "😕 Sin airdrops seguros para tus filtros actuales.\nUsa /filter para ajustar o /refresh para actualizar.",
        "refreshing":     "🔄 Actualizando datos de airdrops...",
        "refresh_done":   "✅ ¡Listo! Usa /airdrops para ver lo último.",
        "filters_saved":  "✅ ¡Filtros guardados! Usa /airdrops para ver tu lista.",
        "wallet_prompt":  "👛 *Rastreador de Billetera*\n\nEnvíame tu dirección de billetera y verificaré los airdrops actuales.\n\nCompatible con: ETH, SOL, BNB\n\n⚠️ _Nunca almacenamos claves privadas — solo la dirección._",
        "submit_prompt":  (
            "📝 *Enviar un Airdrop*\n\n"
            "¿Quieres que tu proyecto aparezca en MantisTracker?\n\n"
            "Completa nuestro formulario:\n"
            "{url}\n\n"
            "✅ *El listado incluye:*\n"
            "• Revisión de seguridad antes de publicar\n"
            "• Insignia de cadena y estado\n"
            "• Valor estimado mostrado\n"
            "• Alcance a todos los suscriptores\n\n"
            "🛡️ *Requisitos de seguridad:*\n"
            "• Debe ser gratuito para reclamar\n"
            "• Debe tener sitio web oficial\n"
            "• Debe tener presencia social verificable\n"
            "• Sin requisitos de frase semilla o clave privada\n"
            "• Sin mecánicas de envío para reclamar\n\n"
            "Envíos revisados en 24–48 horas."
        ),
        "lang_select":    "🌐 *Seleccionar Idioma*\n\nElige tu idioma preferido:",
        "lang_set":       "✅ ¡Idioma configurado en Español!",
    }
}

SAFETY_GUIDE = {
    "en": (
        "🛡️ *Airdrop Safety Guide*\n\n"
        "*Score Scale:*\n"
        "✅ 0 — Safe\n"
        "🟡 1–2 — Low Risk\n"
        "🟠 3–5 — Moderate Risk\n"
        "🔴 6–7 — High Risk\n"
        "☠️ 8–10 — Likely Scam\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚨 *Walk away immediately if it:*\n"
        "• Asks for seed phrase or private key\n"
        "• Asks you to SEND crypto to claim\n"
        "• Charges any fee to activate claim\n"
        "• Guarantees massive returns\n"
        "• Only contact is a random DM\n\n"
        "✅ *Trust signals:*\n"
        "• Listed on CoinMarketCap or CoinGecko\n"
        "• Verified X account with history\n"
        "• Public GitHub with active commits\n"
        "• Security audit completed\n"
        "• 100% free to claim"
    ),
    "es": (
        "🛡️ *Guía de Seguridad de Airdrops*\n\n"
        "*Escala de puntuación:*\n"
        "✅ 0 — Seguro\n"
        "🟡 1–2 — Riesgo bajo\n"
        "🟠 3–5 — Riesgo moderado\n"
        "🔴 6–7 — Riesgo alto\n"
        "☠️ 8–10 — Probable estafa\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚨 *Aléjate inmediatamente si:*\n"
        "• Pide frase semilla o clave privada\n"
        "• Te pide ENVIAR cripto para reclamar\n"
        "• Cobra alguna tarifa para activar\n"
        "• Garantiza retornos masivos\n"
        "• Solo contacto es un DM aleatorio\n\n"
        "✅ *Señales de confianza:*\n"
        "• Listado en CoinMarketCap o CoinGecko\n"
        "• Cuenta X verificada con historial\n"
        "• GitHub público con commits activos\n"
        "• Auditoría de seguridad completada\n"
        "• 100% gratuito para reclamar"
    ),
}

TIPS_GUIDE = {
    "en": (
        "💡 *Crypto Security Tips*\n\n"
        "🔑 Never share your password or PIN with anyone\n"
        "🌱 Seed phrase = wallet access. Never type it anywhere\n"
        "🪣 Use a burner wallet for airdrops\n"
        "🔒 Enable 2FA on every exchange and email\n"
        "🛑 Revoke old approvals at revoke.cash\n"
        "🔗 Always verify URLs before connecting\n"
        "⚙️ Use a hardware wallet for real holdings\n"
        "🎭 Fake support bots are everywhere — admins never DM first\n"
        "💰 Real airdrops are ALWAYS free\n"
        "🚨 If scammed: move funds, revoke approvals, change passwords"
    ),
    "es": (
        "💡 *Consejos de Seguridad Cripto*\n\n"
        "🔑 Nunca compartas tu contraseña o PIN con nadie\n"
        "🌱 Frase semilla = acceso a billetera. Nunca la escribas en ningún lado\n"
        "🪣 Usa una billetera desechable para airdrops\n"
        "🔒 Activa 2FA en cada exchange y correo\n"
        "🛑 Revoca aprobaciones antiguas en revoke.cash\n"
        "🔗 Siempre verifica las URLs antes de conectar\n"
        "⚙️ Usa una billetera hardware para fondos reales\n"
        "🎭 Los bots falsos de soporte son comunes — los admins nunca hacen DM primero\n"
        "💰 Los airdrops reales son SIEMPRE gratuitos\n"
        "🚨 Si te estafaron: mueve fondos, revoca aprobaciones, cambia contraseñas"
    ),
}

DAILY_SAFETY_TIPS = [
    ("🔑", "Never share your password or PIN — not support, not admins, not bots."),
    ("🌱", "Your seed phrase is your wallet. If anyone asks for it, they are stealing from you."),
    ("🔒", "Enable 2FA on every exchange. Use an authenticator app, not SMS."),
    ("🔗", "Always check the URL before connecting your wallet. One wrong letter = drained."),
    ("🪣", "Use a separate burner wallet for airdrops — never your main wallet."),
    ("📧", "Never click crypto links from emails or DMs. Go directly to the official site."),
    ("💰", "Real airdrops are 100% free. If it costs anything to claim — it is a scam."),
    ("👤", "No legitimate project will ever DM you first asking you to claim a reward."),
    ("📱", "Store your seed phrase on paper offline — never in photos, notes, or cloud."),
    ("🚨", "If a deal sounds too good to be true (100x guaranteed!) — it always is."),
    ("🔍", "Before interacting with any contract, verify it on Etherscan or Solscan."),
    ("🤫", "Do not publicly share your wallet address or holdings."),
    ("⚙️",  "Use a hardware wallet (Ledger or Trezor) for significant crypto holdings."),
    ("🛑", "Revoke old token approvals at revoke.cash — they can be exploited anytime."),
    ("🎭", "Fake support accounts on Telegram and Discord are everywhere. Never trust DMs."),
    ("🧪", "Test any new contract with a tiny amount before going all in."),
    ("📵", "Never enter your seed phrase into any website, app, or bot — ever."),
    ("🔐", "Use a unique strong password for every crypto account. Use a password manager."),
    ("🕵️", "Check a project's GitHub, audit status, and team before trusting it."),
    ("🌐", "Bookmark your most-used DeFi sites. Scammers buy misspelled domain ads."),
]

# ─── SCAM SCORING ─────────────────────────────────────────────────────────────

SCAM_RED_FLAGS = [
    "send crypto", "send eth", "send bnb", "send sol", "send btc",
    "private key", "seed phrase", "mnemonic", "secret phrase",
    "import wallet", "unlock airdrop", "activate wallet",
    "processing fee", "gas fee required", "pay to claim",
    "guaranteed returns", "100x guaranteed", "1000x",
    "connect wallet to receive", "dm for claim", "dm to claim",
]
SCAM_YELLOW_FLAGS = [
    "connect wallet", "sign transaction", "approve contract",
    "limited time only", "act now", "expires in",
]
TRUST_SIGNALS = [
    "coinmarketcap", "coingecko", "official", "verified",
    "github", "audited", "mainnet", "testnet",
]


def calculate_scam_score(airdrop: dict) -> tuple:
    text = " ".join([
        airdrop.get("name", ""),
        airdrop.get("description", ""),
        airdrop.get("requirements", ""),
        airdrop.get("url", ""),
    ]).lower()
    score, warnings = 0, []
    for flag in SCAM_RED_FLAGS:
        if flag in text:
            score += 3
            warnings.append(f"🚨 '{flag}'")
    for flag in SCAM_YELLOW_FLAGS:
        if flag in text:
            score += 1
            warnings.append(f"⚠️ '{flag}'")
    if airdrop.get("source") == "curated":
        score = max(0, score - 2)
    for signal in TRUST_SIGNALS:
        if signal in text:
            score = max(0, score - 1)
    score = min(10, score)
    if score == 0:   label = "✅ SAFE"
    elif score <= 2: label = "🟡 LOW RISK"
    elif score <= 5: label = "🟠 MODERATE"
    elif score <= 7: label = "🔴 HIGH RISK"
    else:            label = "☠️ LIKELY SCAM"
    return score, label, warnings


# ─── PERSISTENCE ──────────────────────────────────────────────────────────────

def _load(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_users():     return _load(USERS_FILE, {})
def save_users(d):    _save(USERS_FILE, d)
def load_cache():     return _load(DATA_FILE, {"airdrops": [], "last_updated": None, "new_ids": []})
def save_cache(d):    _save(DATA_FILE, d)
def load_subs():      return _load(SUBMISSIONS_FILE, [])
def save_subs(d):     _save(SUBMISSIONS_FILE, d)
def load_lb():        return _load(LEADERBOARD_FILE, {})
def save_lb(d):       _save(LEADERBOARD_FILE, d)
def load_wallets():   return _load(WALLETS_FILE, {})
def save_wallets(d):  _save(WALLETS_FILE, d)


def get_user(uid: int) -> dict:
    users = load_users()
    key   = str(uid)
    if key not in users:
        users[key] = {
            "id": uid,
            "filters": PRIORITY_CHAINS.copy(),
            "notifications": True,
            "language": "en",
            "joined": datetime.now().isoformat(),
            "wallet": None,
            "awaiting": None,
        }
        save_users(users)
    return users[key]


def update_user(uid: int, patch: dict):
    users = load_users()
    key   = str(uid)
    if key not in users:
        get_user(uid)
        users = load_users()
    users[key].update(patch)
    save_users(users)


def t(uid: int, key: str) -> str:
    """Get translated string for user."""
    users = load_users()
    lang  = users.get(str(uid), {}).get("language", "en")
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))


# ─── LEADERBOARD ──────────────────────────────────────────────────────────────

def record_click(airdrop_id: str, airdrop_name: str):
    lb = load_lb()
    if airdrop_id not in lb:
        lb[airdrop_id] = {"name": airdrop_name, "clicks": 0, "week_clicks": 0}
    lb[airdrop_id]["clicks"]      += 1
    lb[airdrop_id]["week_clicks"] += 1
    save_lb(lb)


def get_leaderboard(top_n: int = 5) -> list:
    lb = load_lb()
    return sorted(lb.values(), key=lambda x: x["week_clicks"], reverse=True)[:top_n]


def reset_weekly_clicks():
    lb = load_lb()
    for k in lb:
        lb[k]["week_clicks"] = 0
    save_lb(lb)


# ─── WALLET CHECKER ───────────────────────────────────────────────────────────

def is_valid_address(address: str) -> tuple:
    """Returns (is_valid, chain)"""
    address = address.strip()
    if re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return True, "ETH/BNB/BASE"
    if re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', address):
        return True, "SOL"
    if re.match(r'^(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}$', address):
        return True, "BTC"
    return False, "UNKNOWN"


def check_wallet_eligibility(address: str) -> str:
    valid, chain = is_valid_address(address)
    if not valid:
        return "❌ Invalid wallet address. Please check and try again."

    cache    = load_cache()
    airdrops = cache.get("airdrops", [])

    # Match airdrops to wallet's chain
    chain_map = {
        "ETH/BNB/BASE": ["ETH", "BNB", "BASE", "ARB", "MATIC"],
        "SOL":  ["SOL"],
        "BTC":  ["BTC"],
    }
    relevant_chains = chain_map.get(chain, [])
    relevant = [
        a for a in airdrops
        if a.get("chain") in relevant_chains
        and calculate_scam_score(a)[0] <= 5
    ]

    short = f"{address[:6]}...{address[-4:]}"

    lines = [
        f"👛 *Wallet Check*\n",
        f"Address: `{short}`",
        f"Detected chain: `{chain}`\n",
        f"🎯 *{len(relevant)} potentially eligible airdrops:*\n",
    ]

    for i, a in enumerate(relevant[:8], 1):
        em  = CHAIN_EMOJIS.get(a.get("chain", "OTHER"), "🪙")
        est = a.get("est_value", "")
        lines.append(
            f"{i}. {em} *{a['name']}*"
            + (f" — `{est}`" if est else "")
        )
        if a.get("url"):
            lines.append(f"   🔗 {a['url']}")

    lines.append(
        "\n⚠️ _Eligibility is not guaranteed — always verify on official sites._\n"
        "🛡️ _Never connect your main wallet to unverified sites._"
    )
    return "\n".join(lines)


# ─── FORMATTERS ───────────────────────────────────────────────────────────────

def fmt_card(airdrop: dict, index: int = None) -> str:
    chain  = airdrop.get("chain", "OTHER")
    emoji  = CHAIN_EMOJIS.get(chain, "🪙")
    score, label, _ = calculate_scam_score(airdrop)
    name   = airdrop.get("name", "Unknown")
    url    = airdrop.get("url", "")
    status = airdrop.get("status", "unknown").upper()
    est    = airdrop.get("est_value", "")
    prefix = f"{index}. " if index else ""
    lines  = [f"{prefix}{emoji} *{name}*"]
    lines.append(f"Chain: `{chain}` | Status: `{status}`")
    if est:
        lines.append(f"Est. Value: `{est}`")
    lines.append(f"Safety: {label} `({score}/10)`")
    if url:
        lines.append(f"🔗 [Details]({url})")
    return "\n".join(lines)


def fmt_digest(airdrops: list, new_ids: list, lang: str = "en") -> str:
    date_str = datetime.now().strftime("%B %d, %Y")
    priority = [a for a in airdrops
                if a.get("chain") in PRIORITY_CHAINS
                and calculate_scam_score(a)[0] <= 5]
    others   = [a for a in airdrops
                if a.get("chain") not in PRIORITY_CHAINS
                and calculate_scam_score(a)[0] <= 2]
    tip_i    = datetime.now().timetuple().tm_yday % len(DAILY_SAFETY_TIPS)
    tip_e, tip_t = DAILY_SAFETY_TIPS[tip_i]

    if lang == "es":
        header = (
            f"🦗 *MANTIS TRACKER — Resumen Diario*\n"
            f"📅 {date_str}\n{'─'*28}\n"
            f"*{len(airdrops)}* airdrops | *{len(new_ids)}* nuevos hoy\n\n"
        )
        footer = (
            f"{'─'*28}\n💡 *Consejo de Seguridad:*\n{tip_e} {tip_t}\n\n"
            f"🛡️ Los airdrops legítimos son SIEMPRE gratuitos.\n\n"
            f"/airdrops  /new  /filter  /tips  /safety"
        )
    else:
        header = (
            f"🦗 *MANTIS TRACKER — Daily Digest*\n"
            f"📅 {date_str}\n{'─'*28}\n"
            f"*{len(airdrops)}* airdrops tracked | *{len(new_ids)}* new today\n\n"
        )
        footer = (
            f"{'─'*28}\n💡 *Daily Safety Tip:*\n{tip_e} {tip_t}\n\n"
            f"🛡️ Legit airdrops are always FREE.\n\n"
            f"/airdrops  /new  /filter  /tips  /safety"
        )

    body = "⭐ *SOL · BTC · ETH · BNB*\n\n"
    for i, a in enumerate(priority[:8], 1):
        body += fmt_card(a, index=i) + "\n\n"
    if others:
        label = "🌐 *Otras Cadenas*" if lang == "es" else "🌐 *Other Chains*"
        body += f"{label} ({len(others)} safe)\n\n"
        for i, a in enumerate(others[:3], 1):
            body += fmt_card(a, index=i) + "\n\n"
    return header + body + footer


def fmt_leaderboard(lang: str = "en") -> str:
    top = get_leaderboard(10)
    if lang == "es":
        title  = "🏆 *Clasificación Semanal — Airdrops Más Populares*\n\n"
        footer = "\n_Actualizado cada domingo. Basado en clics de la semana._"
        none   = "📊 Aún no hay datos esta semana."
    else:
        title  = "🏆 *Weekly Leaderboard — Most Popular Airdrops*\n\n"
        footer = "\n_Updated every Sunday. Based on clicks this week._"
        none   = "📊 No data yet this week."
    if not top:
        return title + none
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    lines  = [title]
    for i, entry in enumerate(top):
        medal  = medals[i] if i < len(medals) else f"{i+1}."
        clicks = entry.get("week_clicks", 0)
        name   = entry.get("name", "Unknown")
        lines.append(f"{medal} *{name}* — {clicks} clicks")
    return "\n".join(lines) + footer


# ─── START / MENU ─────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    get_user(uid)
    kb = []
    if MINI_APP_URL:
        kb.append([InlineKeyboardButton(
            t(uid, "btn_dashboard"),
            web_app=WebAppInfo(url=MINI_APP_URL)
        )])
    kb += [
        [InlineKeyboardButton(t(uid, "btn_airdrops"),    callback_data="c_airdrops"),
         InlineKeyboardButton(t(uid, "btn_new"),         callback_data="c_new")],
        [InlineKeyboardButton(t(uid, "btn_filter"),      callback_data="c_filter"),
         InlineKeyboardButton(t(uid, "btn_safety"),      callback_data="c_safety")],
        [InlineKeyboardButton(t(uid, "btn_tips"),        callback_data="c_tips"),
         InlineKeyboardButton(t(uid, "btn_wallet"),      callback_data="c_wallet")],
        [InlineKeyboardButton(t(uid, "btn_leaderboard"), callback_data="c_leaderboard"),
         InlineKeyboardButton(t(uid, "btn_submit"),      callback_data="c_submit")],
        [InlineKeyboardButton(t(uid, "btn_language"),    callback_data="c_language"),
         InlineKeyboardButton(t(uid, "btn_status"),      callback_data="c_status")],
        [InlineKeyboardButton(t(uid, "btn_help"),        callback_data="c_help")],
    ]
    await update.message.reply_text(
        t(uid, "welcome"),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(kb),
    )


# ─── AIRDROPS ─────────────────────────────────────────────────────────────────

async def _send_airdrops(target, user_id: int, new_only: bool = False):
    ud      = get_user(user_id)
    filters = ud.get("filters", PRIORITY_CHAINS)
    lang    = ud.get("language", "en")
    cache   = load_cache()
    drops   = cache.get("airdrops", [])

    if not drops:
        await target.reply_text(
            "⏳ No data yet. Type /refresh to fetch now."
        )
        return

    if new_only:
        new_ids = cache.get("new_ids", [])
        drops   = [a for a in drops if a.get("id") in new_ids]

    if "ALL" not in filters:
        drops = [a for a in drops if a.get("chain") in filters]
    safe = [a for a in drops if calculate_scam_score(a)[0] <= 5]

    if not safe:
        await target.reply_text(
            t(user_id, "no_airdrops"),
            parse_mode=ParseMode.MARKDOWN
        )
        return

    lu = cache.get("last_updated", "")
    try:
        lu_fmt = datetime.fromisoformat(lu).strftime("%b %d %H:%M UTC")
    except Exception:
        lu_fmt = "recently"

    lbl  = ("🆕 *Nuevos Hoy*" if lang == "es" else "🆕 *New Today*") if new_only else ("📋 *Airdrops de Hoy*" if lang == "es" else "📋 *Current Airdrops*")
    msg  = f"{lbl} — {lu_fmt}\n{min(len(safe),10)} of {len(safe)} | Chains: {', '.join(filters)}\n\n"
    chunks, current = [], msg
    for i, a in enumerate(safe[:10], 1):
        record_click(a.get("id", ""), a.get("name", ""))
        card = fmt_card(a, index=i) + "\n\n"
        if len(current) + len(card) > 3800:
            chunks.append(current); current = card
        else:
            current += card
    current += "─────────────────\n/new  /filter  /refresh  /help"
    chunks.append(current)
    for chunk in chunks:
        await target.reply_text(chunk, parse_mode=ParseMode.MARKDOWN,
                                 disable_web_page_preview=True)


async def cmd_airdrops(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_airdrops(update.message, update.effective_user.id)


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or (update.callback_query and update.callback_query.message)
    await _send_airdrops(msg, update.effective_user.id, new_only=True)


# ─── FILTER ───────────────────────────────────────────────────────────────────

async def cmd_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid        = update.effective_user.id
    ud         = get_user(uid)
    current    = ud.get("filters", PRIORITY_CHAINS)
    all_chains = PRIORITY_CHAINS + ["BASE", "ARB", "MATIC", "AVAX", "ALL"]
    kb, row = [], []
    for chain in all_chains:
        em  = CHAIN_EMOJIS.get(chain, "🪙")
        chk = "✅" if chain in current else "⬜"
        row.append(InlineKeyboardButton(f"{chk}{em}{chain}", callback_data=f"f_{chain}"))
        if len(row) == 3:
            kb.append(row); row = []
    if row: kb.append(row)
    kb.append([InlineKeyboardButton("💾 Done / Listo", callback_data="f_save")])
    text = f"⚙️ *Chain Filters*\nActive: `{', '.join(current)}`\n\nTap to toggle — ✅ = included:"
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=InlineKeyboardMarkup(kb))
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                                       reply_markup=InlineKeyboardMarkup(kb))


# ─── SAFETY / TIPS ────────────────────────────────────────────────────────────

async def cmd_safety(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    lang   = get_user(uid).get("language", "en")
    target = update.message or update.callback_query.message
    await target.reply_text(SAFETY_GUIDE[lang], parse_mode=ParseMode.MARKDOWN)


async def cmd_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    lang   = get_user(uid).get("language", "en")
    target = update.message or update.callback_query.message
    await target.reply_text(TIPS_GUIDE[lang], parse_mode=ParseMode.MARKDOWN)


# ─── LANGUAGE ─────────────────────────────────────────────────────────────────

async def cmd_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    kb  = [
        [InlineKeyboardButton("🇺🇸 English",  callback_data="lang_en"),
         InlineKeyboardButton("🇪🇸 Español",   callback_data="lang_es")],
    ]
    text   = t(uid, "lang_select")
    target = update.message or update.callback_query.message
    if update.message:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN,
                                                       reply_markup=InlineKeyboardMarkup(kb))


# ─── WALLET ───────────────────────────────────────────────────────────────────

async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    target = update.message or update.callback_query.message
    update_user(uid, {"awaiting": "wallet"})
    await target.reply_text(t(uid, "wallet_prompt"), parse_mode=ParseMode.MARKDOWN)


# ─── LEADERBOARD ──────────────────────────────────────────────────────────────

async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    lang   = get_user(uid).get("language", "en")
    target = update.message or update.callback_query.message
    await target.reply_text(fmt_leaderboard(lang), parse_mode=ParseMode.MARKDOWN)


# ─── SUBMIT AIRDROP ───────────────────────────────────────────────────────────

async def cmd_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid    = update.effective_user.id
    lang   = get_user(uid).get("language", "en")
    target = update.message or update.callback_query.message
    msg    = STRINGS[lang]["submit_prompt"].format(url=SUBMISSIONS_SHEET)
    await target.reply_text(msg, parse_mode=ParseMode.MARKDOWN,
                             disable_web_page_preview=True)


# ─── STATUS ───────────────────────────────────────────────────────────────────

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cache  = load_cache()
    users  = load_users()
    drops  = cache.get("airdrops", [])
    safe_n = sum(1 for a in drops if calculate_scam_score(a)[0] <= 5)
    lu     = cache.get("last_updated", "Never")
    try:
        lu_fmt = datetime.fromisoformat(lu).strftime("%b %d, %Y %H:%M UTC")
    except Exception:
        lu_fmt = "Never"
    chain_counts = {}
    for a in drops:
        c = a.get("chain", "OTHER")
        chain_counts[c] = chain_counts.get(c, 0) + 1
    top       = sorted(chain_counts.items(), key=lambda x: -x[1])[:5]
    chain_str = " | ".join(f"{CHAIN_EMOJIS.get(c,'🪙')}{c}:{n}" for c, n in top)
    msg = (
        f"📊 *MantisTrackerBot Status*\n\n"
        f"🕐 Last updated: {lu_fmt}\n"
        f"🪂 Total cached: {len(drops)}\n"
        f"✅ Safe drops: {safe_n}\n"
        f"👥 Total users: {len(users)}\n\n"
        f"*By chain:*\n{chain_str}\n\n"
        f"⏰ Next auto-update: 8:00 AM UTC\n"
        f"Priority: SOL ◎ BTC ₿ ETH Ξ BNB 🔶"
    )
    target = update.message or update.callback_query.message
    await target.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def cmd_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    await update.message.reply_text(t(uid, "refreshing"))
    await _do_update(context)
    await update.message.reply_text(t(uid, "refresh_done"))


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    lang = get_user(uid).get("language", "en")
    if lang == "es":
        msg = (
            "🦗 *MantisTrackerBot — Comandos*\n\n"
            "/start — Menú principal\n"
            "/airdrops — Lista de hoy\n"
            "/new — Nuevos desde la última actualización\n"
            "/filter — Filtros de cadena\n"
            "/safety — Guía de seguridad\n"
            "/tips — Guía completa de seguridad\n"
            "/wallet — Rastrear elegibilidad de billetera\n"
            "/leaderboard — Airdrops más populares esta semana\n"
            "/submit — Enviar un airdrop para listado\n"
            "/language — Cambiar idioma\n"
            "/status — Estadísticas del bot\n"
            "/refresh — Actualizar datos ahora\n"
            "/help — Esta lista\n\n"
            "📅 Resumen automático: *8AM UTC diariamente*"
        )
    else:
        msg = (
            "🦗 *MantisTrackerBot — Commands*\n\n"
            "/start — Main menu\n"
            "/airdrops — Today's safe list\n"
            "/new — New drops since last update\n"
            "/filter — Set chain filters\n"
            "/safety — Scam safety guide\n"
            "/tips — Full security guide\n"
            "/wallet — Check wallet eligibility\n"
            "/leaderboard — Most popular airdrops this week\n"
            "/submit — Submit an airdrop for listing\n"
            "/language — Change language\n"
            "/status — Bot stats\n"
            "/refresh — Force-fetch fresh data\n"
            "/help — This list\n\n"
            "📅 Auto-digest: *8AM UTC daily*"
        )
    target = update.message or update.callback_query.message
    await target.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


# ─── MESSAGE HANDLER (wallet input) ───────────────────────────────────────────

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    ud   = get_user(uid)
    text = update.message.text.strip()

    if ud.get("awaiting") == "wallet":
        update_user(uid, {"awaiting": None, "wallet": text})
        result = check_wallet_eligibility(text)
        await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN,
                                         disable_web_page_preview=True)
    else:
        await update.message.reply_text(
            "Use /start to see the menu or /help for all commands.",
            parse_mode=ParseMode.MARKDOWN
        )


# ─── CALLBACK HANDLER ─────────────────────────────────────────────────────────

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    data = q.data
    await q.answer()
    uid  = q.from_user.id

    if data == "c_airdrops":
        await _send_airdrops(q.message, uid)
    elif data == "c_new":
        await _send_airdrops(q.message, uid, new_only=True)
    elif data == "c_filter":
        update._effective_user = q.from_user
        update._message = None
        await cmd_filter(update, context)
    elif data == "c_safety":
        lang = get_user(uid).get("language", "en")
        await q.message.reply_text(SAFETY_GUIDE[lang], parse_mode=ParseMode.MARKDOWN)
    elif data == "c_tips":
        lang = get_user(uid).get("language", "en")
        await q.message.reply_text(TIPS_GUIDE[lang], parse_mode=ParseMode.MARKDOWN)
    elif data == "c_wallet":
        update_user(uid, {"awaiting": "wallet"})
        await q.message.reply_text(t(uid, "wallet_prompt"), parse_mode=ParseMode.MARKDOWN)
    elif data == "c_leaderboard":
        lang = get_user(uid).get("language", "en")
        await q.message.reply_text(fmt_leaderboard(lang), parse_mode=ParseMode.MARKDOWN)
    elif data == "c_submit":
        lang = get_user(uid).get("language", "en")
        msg  = STRINGS[lang]["submit_prompt"].format(url=SUBMISSIONS_SHEET)
        await q.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN,
                                    disable_web_page_preview=True)
    elif data == "c_language":
        update._effective_user = q.from_user
        update._message = None
        await cmd_language(update, context)
    elif data == "c_status":
        await cmd_status(update, context)
    elif data == "c_help":
        await cmd_help(update, context)
    elif data.startswith("lang_"):
        lang = data[5:]
        update_user(uid, {"language": lang})
        await q.edit_message_text(
            STRINGS[lang]["lang_set"],
            parse_mode=ParseMode.MARKDOWN
        )
    elif data.startswith("f_"):
        chain   = data[2:]
        ud      = get_user(uid)
        filters = list(ud.get("filters", PRIORITY_CHAINS))
        if chain == "save":
            await q.edit_message_text(
                t(uid, "filters_saved"),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        if chain == "ALL":
            filters = ["ALL"]
        else:
            if "ALL" in filters: filters = []
            if chain in filters: filters.remove(chain)
            else:                filters.append(chain)
            if not filters:      filters = PRIORITY_CHAINS.copy()
        update_user(uid, {"filters": filters})
        update._effective_user = q.from_user
        update._message = None
        await cmd_filter(update, context)


# ─── SCHEDULED JOBS ───────────────────────────────────────────────────────────

async def _do_update(context: ContextTypes.DEFAULT_TYPE):
    cache   = load_cache()
    old_ids = set(a["id"] for a in cache.get("airdrops", []))
    fresh   = fetch_all_airdrops()
    new_ids = [a["id"] for a in fresh if a["id"] not in old_ids]
    cache.update({"airdrops": fresh, "last_updated": datetime.now().isoformat(),
                  "new_ids": new_ids})
    save_cache(cache)
    logger.info(f"✅ Update done: {len(fresh)} total, {len(new_ids)} new")

    users  = load_users()
    sent   = 0
    for uid_str, ud in users.items():
        if not ud.get("notifications", True):
            continue
        lang   = ud.get("language", "en")
        digest = fmt_digest(fresh, new_ids, lang)
        try:
            await context.bot.send_message(
                chat_id=int(uid_str), text=digest,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Could not message {uid_str}: {e}")
    logger.info(f"📨 Digest sent to {sent}/{len(users)} users")

    # Also post to channel if configured
    if CHANNEL_ID:
        try:
            digest = fmt_digest(fresh, new_ids, "en")
            await context.bot.send_message(
                chat_id=CHANNEL_ID, text=digest,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            logger.info(f"📢 Posted to channel {CHANNEL_ID}")
        except Exception as e:
            logger.warning(f"Channel post failed: {e}")


async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    await _do_update(context)


async def weekly_leaderboard_job(context: ContextTypes.DEFAULT_TYPE):
    """Post weekly leaderboard every Sunday then reset counts."""
    users = load_users()
    board = fmt_leaderboard("en")
    for uid_str, ud in users.items():
        if not ud.get("notifications", True):
            continue
        lang  = ud.get("language", "en")
        board = fmt_leaderboard(lang)
        try:
            await context.bot.send_message(
                chat_id=int(uid_str), text=board,
                parse_mode=ParseMode.MARKDOWN,
            )
            await asyncio.sleep(0.05)
        except Exception:
            pass
    if CHANNEL_ID:
        try:
            await context.bot.send_message(
                chat_id=CHANNEL_ID, text=fmt_leaderboard("en"),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception:
            pass
    reset_weekly_clicks()
    logger.info("🏆 Weekly leaderboard posted and reset")


# ─── STARTUP ──────────────────────────────────────────────────────────────────

async def post_init(app: Application):
    await app.bot.set_my_commands([
        BotCommand("start",       "Main menu / Menú principal"),
        BotCommand("airdrops",    "Today's airdrop list"),
        BotCommand("new",         "New drops today"),
        BotCommand("filter",      "Set chain filters"),
        BotCommand("safety",      "Scam safety guide"),
        BotCommand("tips",        "Security tips"),
        BotCommand("wallet",      "Check wallet eligibility"),
        BotCommand("leaderboard", "Most popular airdrops"),
        BotCommand("submit",      "Submit an airdrop"),
        BotCommand("language",    "Change language / Cambiar idioma"),
        BotCommand("status",      "Bot stats"),
        BotCommand("refresh",     "Force refresh data"),
        BotCommand("help",        "All commands"),
    ])
    logger.info("✅ Commands registered")
    cache = load_cache()
    if not cache.get("airdrops"):
        logger.info("🌱 Seeding initial data...")
        drops = fetch_all_airdrops()
        cache.update({"airdrops": drops,
                      "last_updated": datetime.now().isoformat(),
                      "new_ids": [a["id"] for a in drops]})
        save_cache(cache)
        logger.info(f"✅ Seeded {len(drops)} airdrops")


def main():
    logger.info("🦗 Starting MantisTrackerBot...")
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    for cmd, fn in [
        ("start",       cmd_start),
        ("airdrops",    cmd_airdrops),
        ("new",         cmd_new),
        ("filter",      cmd_filter),
        ("safety",      cmd_safety),
        ("tips",        cmd_tips),
        ("wallet",      cmd_wallet),
        ("leaderboard", cmd_leaderboard),
        ("submit",      cmd_submit),
        ("language",    cmd_language),
        ("status",      cmd_status),
        ("refresh",     cmd_refresh),
        ("help",        cmd_help),
    ]:
        app.add_handler(CommandHandler(cmd, fn))

    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    jq = app.job_queue
    jq.run_daily(daily_job,
                 time=dtime(hour=DAILY_HOUR, minute=DAILY_MINUTE),
                 name="daily_digest")
    jq.run_daily(weekly_leaderboard_job,
                 time=dtime(hour=9, minute=0),
                 days=(WEEKLY_DAY,),
                 name="weekly_leaderboard")

    logger.info(f"⏰ Daily digest: {DAILY_HOUR:02d}:{DAILY_MINUTE:02d} UTC")
    logger.info("⏰ Weekly leaderboard: Sunday 9:00 UTC")
    logger.info("🚀 Bot running — Ctrl+C to stop")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
