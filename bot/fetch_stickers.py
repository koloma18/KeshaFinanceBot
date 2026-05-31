"""Fetch sticker file_ids from Telegram Bot API and build STICKER_POOL.

Usage:
    python fetch_stickers.py [set_name1 set_name2 ...]

If no set names given, tries to discover from known names or prompts.
Outputs ready-to-paste STICKER_POOL Python dict.
"""

import json
import os
import sys
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not set in .env", file=sys.stderr)
    sys.exit(1)

API_BASE = f"https://api.telegram.org/bot{BOT_TOKEN}"


def api_call(method: str, **params) -> dict:
    """Call Bot API method, return JSON result."""
    url = f"{API_BASE}/{method}"
    if params:
        qs = "&".join(f"{k}={urllib.request.quote(str(v))}" for k, v in params.items())
        url += "?" + qs
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if not data.get("ok"):
                print(f"API error: {data.get('description')}", file=sys.stderr)
                return {}
            return data.get("result", {})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Request error: {e}", file=sys.stderr)
        return {}


# ── Emoji → sticker type mapping ──
EMOJI_TYPE = {
    # money
    "💰": "money",
    "💸": "money",
    "🤑": "money",
    "💎": "money",
    "💵": "money",
    "💶": "money",
    "💷": "money",
    "💴": "money",
    "🪙": "money",
    "💲": "money",
    "🧧": "money",
    # approve
    "👍": "approve",
    "👌": "approve",
    "🤝": "approve",
    "🫡": "approve",
    "✅": "approve",
    "✔": "approve",
    "☑": "approve",
    "🆗": "approve",
    "💪": "approve",
    "🙌": "approve",
    "👏": "approve",
    # cry
    "😭": "cry",
    "😢": "cry",
    "🥺": "cry",
    "💔": "cry",
    "😿": "cry",
    "😩": "cry",
    "😫": "cry",
    "😞": "cry",
    "😟": "cry",
    "😥": "cry",
    "😓": "cry",
    # angry
    "😡": "angry",
    "🤬": "angry",
    "😤": "angry",
    "👿": "angry",
    "😠": "angry",
    "💢": "angry",
    "🤯": "angry",
    "😾": "angry",
    # smirk
    "😏": "smirk",
    "😈": "smirk",
    "🤨": "smirk",
    "🙄": "smirk",
    "😼": "smirk",
    "😒": "smirk",
    "🫤": "smirk",
    # disapprove
    "👎": "disapprove",
    "🤦": "disapprove",
    "😒": "disapprove",
    "🗿": "disapprove",
    "❌": "disapprove",
    "⛔": "disapprove",
    "🚫": "disapprove",
    "🤷": "disapprove",
    "🤦‍♂️": "disapprove",
    "🤦‍♀️": "disapprove",
    "🙅": "disapprove",
    "🙅‍♂️": "disapprove",
    "🙅‍♀️": "disapprove",
}


def categorize_sticker(sticker: dict) -> str | None:
    """Map a sticker's emoji to one of our types."""
    emoji = sticker.get("emoji", "")
    return EMOJI_TYPE.get(emoji)


def fetch_set(set_name: str) -> list[dict]:
    """Fetch all stickers from a named sticker set."""
    result = api_call("getStickerSet", name=set_name)
    if not result:
        return []
    stickers = result.get("stickers", [])
    print(f"  {set_name}: {len(stickers)} stickers", file=sys.stderr)
    return stickers


def main():
    set_names = sys.argv[1:] if len(sys.argv) > 1 else None

    if not set_names:
        # Try to discover — ask user to send a sticker from each set to the bot,
        # or provide set names
        print("No sticker set names provided.", file=sys.stderr)
        print(
            "Usage: python fetch_stickers.py set_name1 set_name2 ...", file=sys.stderr
        )
        print("", file=sys.stderr)
        print("You can get set names by:", file=sys.stderr)
        print("  1. Open a sticker in Telegram", file=sys.stderr)
        print("  2. Tap the sticker pack name", file=sys.stderr)
        print("  3. The link looks like: t.me/addstickers/SetName", file=sys.stderr)
        print("  4. Use SetName as the argument", file=sys.stderr)
        sys.exit(1)

    # Collect all stickers
    all_stickers: dict[str, list[str]] = {
        "money": [],
        "approve": [],
        "cry": [],
        "angry": [],
        "smirk": [],
        "disapprove": [],
    }

    total = 0

    for set_name in set_names:
        stickers = fetch_set(set_name)
        for s in stickers:
            stype = categorize_sticker(s)
            if stype and stype in all_stickers:
                all_stickers[stype].append(s["file_id"])
                total += 1

    # ── Output ──
    print()
    print("# === STICKER_POOL (copy to stickers.py) ===")
    print("STICKER_POOL: dict[str, list[str]] = {")
    for stype in ["money", "approve", "cry", "angry", "smirk", "disapprove"]:
        ids = all_stickers[stype]
        print(f'    "{stype}": [')
        for fid in ids:
            print(f'        "{fid}",')
        print("    ],")
    print("}")
    print()
    print(f"# Total classified: {total} stickers from {len(set_names)} sets")

    # Print summary
    for stype in ["money", "approve", "cry", "angry", "smirk", "disapprove"]:
        print(f"#   {stype}: {len(all_stickers[stype])}")


if __name__ == "__main__":
    main()
