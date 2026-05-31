"""Стикеры для Кеши — 312 стикеров из 5 паков.

Стикеры сгруппированы по эмоциональному типу.
Каждый пул содержит 11-12 реальных file_id.
Выбирается случайный при каждой отправке.

Паки:
- Webp_15 (@stjckers) — 120 стикеров
- catsunicmass (Cats @fixfox) — 120 стикеров
- HANGSEED_Stitch (💥Stitcʜ) — 27 стикеров
- LilDiablo — 25 стикеров
- ShadowKitty — статистика в общем пуле
"""

import logging
import random

logger = logging.getLogger(__name__)

STICKER_POOL: dict[str, list[str]] = {
    "angry": [
        "CAACAgQAAxUAAWocRKdFkPLbSXzBr8wr_N-UdmZPAAIFDAACPzLwUW70DzUUhPlTOwQ",
        "CAACAgQAAxUAAWocRKcu4UTKFfCJHftBO0wYpO9lAALCDAACm71gU62jht_Y8G-OOwQ",
        "CAACAgQAAxUAAWocRKerMpzUsaFLuO6fy7T_UCTKAALcFQACE3HxUbaiwwuBYGtXOwQ",
        "CAACAgQAAxUAAWocRKcFJjp1KKyRbegG0N4kDb92AALnCgACRBvZUVeME43DUhD7OwQ",
        "CAACAgQAAxUAAWocRKetawABIi4oq-PoSUv31DOG1AACZxwAApuFEVKYZZS7vFpNOwQ",
        "CAACAgQAAxUAAWocRKdR2xdFy6nWhXiF4QxEzYyTAALvFgACcEYAAVG9OkMPhBvbnzsE",
        "CAACAgQAAxUAAWocRKegqFyNXGQMZl7y1Mrc5RxSAAI1GwAC47wZUWqk7kQSpGOiOwQ",
        "CAACAgQAAxUAAWocRKfWf9M96XAlgTvL-JacbpN_AAKRFgACUvSZUoqNdW2xIXdvOwQ",
        "CAACAgQAAxUAAWocRKez2cAaXj-Dh3G6hBcjoHYMAAIrEAACTXPAU8aVpXVBmNOROwQ",
        "CAACAgQAAxUAAWocRKf7JmlvdAivj77mnareVylRAAIwFAACBEORU3SFIc3l7wnVOwQ",
        "CAACAgIAAxUAAWocRKixFI6B6QGxWJAR3HwfxIWVAALxjgACCos5SdG3ORiVN2wVOwQ",
        "CAACAgIAAxUAAWocRKgg2314ixVPzOHkUAABWAtrIgACdIcAAripKUustXlqV2VPwzsE",
    ],
    "approve": [
        "CAACAgQAAxUAAWocRKe8Pfc2GyoQng5l2Czc0g79AAJwFwACaZ4YUjjGSlpLfIUsOwQ",
        "CAACAgQAAxUAAWocRKcyj40ysIzcrB1_FPs4bydeAAK6FAAC_zvwUWKz1gkRWahrOwQ",
        "CAACAgQAAxUAAWocRKcSYJLORmYUmxZiPxK_8fvdAALbEwACVbfwUHrtv7J-Z_9NOwQ",
        "CAACAgQAAxUAAWocRKfHbXndxVnAs3tCRf3VeOXxAAIBFQACcAdBU-Le7xAFbSmPOwQ",
        "CAACAgQAAxUAAWocRKegwxuczgm9htGUh4NltN7YAAJXFwAC0llAU5cfQ8LAYLVtOwQ",
        "CAACAgQAAxUAAWocRKe7vrKrL-8aPh4fVvwleApMAAJzHAACVzm5UOgAAVhEGTmlAjsE",
        "CAACAgQAAxUAAWocRKdBFfvEDU9pAAGGDqLOcm6InQACqgoAAnZr4FMPUGZeiWkAAcQ7BA",
        "CAACAgQAAxUAAWocRKd7h8hLZhBEYwqr5C0pn3V8AAKjFwACnxAxU5kIEt1UKmSYOwQ",
        "CAACAgQAAxUAAWocRKex32_VEAqA1RMS1JMIsgXUAAIaFwACoY0IUgS3QORtxloGOwQ",
        "CAACAgQAAxUAAWocRKevjzFR0hBi25gevfexiegfAALNFQACmk7ZUqX2aZnQIbaNOwQ",
        "CAACAgQAAxUAAWocRKeizrGRV2sYIU6OMItAjiafAAKbGAACoBzgUwjeP1AZMnKROwQ",
        "CAACAgQAAxUAAWocRKdnKkCHfpy0VbpKQD5Px7U1AALoCQACbQXpU3f0VcR0LKO4OwQ",
    ],
    "cry": [
        "CAACAgQAAxUAAWocRKdb2UKUdNsburT7pPmkrLNMAAJuGwACm9TgUXa5CJ8zVpQmOwQ",
        "CAACAgQAAxUAAWocRKfHgQjFqDXu7Y4go_AOOWLXAAJsFgACmFsxU2f5ivPPxge_OwQ",
        "CAACAgQAAxUAAWocRKfNmk6XpiPaYlv3L2a0BtXqAAI9DAACPMNRURr46fvy5fUkOwQ",
        "CAACAgQAAxUAAWocRKdTZJuBr-deyefAoqMb2hUbAALuEwACHEypUzesPey4sgEqOwQ",
        "CAACAgQAAxUAAWocRKfCZWzVUq0m2KJExz4c6Xz3AAJzEwAC1rGgUF2Yv7Oe4IwKOwQ",
        "CAACAgQAAxUAAWocRKeONjB4FWi5oYEXBOxxxW61AALEEQAChd4QUdIFoVgXNPo2OwQ",
        "CAACAgQAAxUAAWocRKeBjh6G0jITdHoHx9lD-SyWAAIbEQACe7uAUNn8KUopzVVlOwQ",
        "CAACAgQAAxUAAWocRKdnDUsoZ41xeTKWjmvhmcLIAAKXFgACBsYwU54x0AABtJ3l6TsE",
        "CAACAgQAAxUAAWocRKeqv1dQI3uca1VM4IAK3tFjAAINDQACU39YU5pUwip8wD7bOwQ",
        "CAACAgQAAxUAAWocRKciN89NfW_rQ3FCqxLzq62ZAAKiCwACq7LpU0lmBn_52qa_OwQ",
        "CAACAgQAAxUAAWocRKeR7S8B3Idnhwfhj1xr588oAAIqDAACwHzQUvDuXzLhUztROwQ",
        "CAACAgQAAxUAAWocRKckusr-t0COkXuAGqME_60HAAKBEwAC38jZU4qZMc51uq1NOwQ",
    ],
    "disapprove": [
        "CAACAgQAAxUAAWocRKfNT2oKEJv4VTH1Z757gnmTAAJLEwAC4nPRUFFw9X1DZ-KAOwQ",
        "CAACAgQAAxUAAWocRKdRp9VtP5kNnQl7MbsSuBd7AALcEQACmO7BUWJ9C6WPNNqWOwQ",
        "CAACAgQAAxUAAWocRKexy0wYT9l9g4Cbfh2l0yDcAAImFQACOFWpU-V6QhbRUzwiOwQ",
        "CAACAgQAAxUAAWocRKfD-QwqCUgelTVyyNrhHXt8AAKMDQACCfJRUYYcyo8gIgtkOwQ",
        "CAACAgIAAxUAAWocRKhhKVMxVUlHYmEzpskGNh5sAAI5jAACHk84SQ0j0odhwfONOwQ",
        "CAACAgIAAxUAAWocRKgbzJbZGZgCJT9XKGKifvtEAALXZwACypnhSS3SmfIaZFiMOwQ",
        "CAACAgQAAxUAAWocRKid6Zpumk9ct4R65jCdltrDAAJlCwACjogZUl-UlO4HwkPwOwQ",
        "CAACAgQAAxUAAWocRKgua2nqYZYVMq7qqVpDwcwsAAJnCwACKGkZUqHTCE95y8i5OwQ",
        "CAACAgIAAxUAAWocRKiGyNTqPwpxyeAxJL-nhtNEAAJXEgACvpbpSm2CjXWENiKKOwQ",
        "CAACAgIAAxUAAWocRKicQFM6_HaPU1h0cZILy5N2AAIYFQACzV8oSBA_2jjmeFfmOwQ",
        "CAACAgIAAxUAAWocRKiEX0EAAe_AAnHlOxOadMT5ZgACmBAAAtX9AUh3EHZ0V_ClKzsE",
        "CAACAgIAAxUAAWocRKipriO5AAFjuOWcZ36U8GubtQACBmIAApL4MUprCRwJsEmYzjsE",
    ],
    "money": [
        "CAACAgIAAxUAAWocRKgUmIXJhDz3fISQ5hROoqWaAALuPQACkhZpSxMWB6aTq90jOwQ",
        "CAACAgQAAxUAAWocRKiLtq3je_IkUMUOCWki3eh6AAJcCwACesgZUvMXWo9VGo17OwQ",
        "CAACAgIAAxUAAWocRKiITrvOR2gSJXDdIh1aR02TAAMUAAKc1IlLpcfWodS-CQ47BA",
        "CAACAgIAAxUAAWocRKgRqIbB1UT6aZg6c9m81WPCAAIbagAC20fpSRitgLNMODeEOwQ",
        "CAACAgQAAxUAAWocRKfcDsg7d1tf0ywcwJxprxX3AAKWGgACNWORUsCc_GAx8bYKOwQ",
        "CAACAgQAAxUAAWocRKcmRRImhaIVawnfMSCCA4GMAAKyFwAC0ssIUvbzDKXhMsEpOwQ",
        "CAACAgIAAxUAAWocRKiO0raTeyJIl0cMqn23BjCGAAKhEAACaNsAAUjx39GtlPykMDsE",
        "CAACAgQAAxUAAWocRKd_2opKE3Jmmih_MdFFMdzoAAIHHwACZzLRU_PDPjibR7cLOwQ",
        "CAACAgIAAxUAAWocRKgDdOpCMlwxzywhJ0P7JSmDAAK5EQACyZBISgJmi1FnbDkYOwQ",
        "CAACAgQAAxUAAWocRKdaVDJ8708d-4gnct7g8Q-rAALLGAADLvhRjT_YoxVsM4g7BA",
        "CAACAgQAAxUAAWocRKcmwAxj-ax2gMNlZBOFj_CMAALBCwACSl-wUS7YsVA34l0hOwQ",
    ],
    "smirk": [
        "CAACAgQAAxUAAWocRKeMDgQJeRorxzfm4eFgxC1kAAJWGQACetwRUqid6RyqHvtSOwQ",
        "CAACAgQAAxUAAWocRKfaDmmhbZqA5tYL3-OWTeDjAALSCwACFvSxUedl2S_ZX9ODOwQ",
        "CAACAgQAAxUAAWocRKeQKESY888G09tlEftq5rIEAAJBEAACLKlAUJN8TrilxB5kOwQ",
        "CAACAgQAAxUAAWocRKe77RIYecPYhszS6t7YIHOOAAL0FwACTItwUKtD8MO-CMnbOwQ",
        "CAACAgQAAxUAAWocRKeKI8saQ2iFVDTu6t0qj2bcAALQCwACYKIwULKPoaix-Wp1OwQ",
        "CAACAgQAAxUAAWocRKf6n5tMCy2NiT-ppVt8YYIqAAItDwACWpKpUz5kYJ1JkFeZOwQ",
        "CAACAgQAAxUAAWocRKdc_THrKSrYRYovfVh_N0OIAALWEgACXOUJUS7wkeqCjXzBOwQ",
        "CAACAgQAAxUAAWocRKd4PhOMIo5zSlDQuEP8XBllAAJQTQACuBWoU6bttmJXdKTBOwQ",
        "CAACAgQAAxUAAWocRKen5vHxitK_DY-gf_hAp9emAALbEwACGv1pUAeJ8lIFPCSFOwQ",
        "CAACAgQAAxUAAWocRKeuq_8cu9Bn736cmLwtx-U4AAJdEAACA8gxUv-FM4SMkb0JOwQ",
        "CAACAgQAAxUAAWocRKeIQxdL3IMpJtmvlj0llKIJAAJlEQACwUdZUJ1XSi0YVmVpOwQ",
        "CAACAgQAAxUAAWocRKfanVkViw3zULn91VC6_gmKAAJSFAAC1hNoUO0l98dQ1-_GOwQ",
    ],
}

STICKER_EMOJI = {
    "approve": "👍",
    "disapprove": "👎",
    "money": "💰",
    "cry": "😭",
    "angry": "😤",
    "smirk": "😏",
}


async def send_sticker(update, context, sticker_type: str, amount: float = 0):
    """Отправить случайный стикер из пула."""
    user_data = context.user_data

    if not user_data.get("stickers_enabled", True):
        return

    freq = user_data.get("sticker_frequency", "always")
    if freq == "off":
        return
    if freq == "large_only" and amount < 2000:
        return

    pool = STICKER_POOL.get(sticker_type, [])
    if pool:
        sticker_id = random.choice(pool)
        try:
            await update.message.reply_sticker(sticker=sticker_id)
            return
        except Exception as e:
            logger.warning("Sticker %s failed: %s", sticker_type, e)

    emoji = STICKER_EMOJI.get(sticker_type, "")
    if emoji and user_data.get("emoji_enabled", True):
        await update.message.reply_text(emoji)


def get_sticker_for_amount(amount: float) -> str:
    if amount > 2000:
        return "cry"
    elif amount > 500:
        return "angry"
    else:
        return "smirk"


def get_sticker_for_income(amount: float) -> str:
    if amount > 10000:
        return "money"
    else:
        return "approve"
