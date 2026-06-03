"""Monthly report: /report — income, expense, net, top categories,
recurring spending, spending by account, budget warnings, Kesha comment.

Date parsing strategy (robust against Google Sheets serial numbers):
  1. Try Date column as DD.MM.YYYY string.
  2. Try Date column as Excel serial number (int/float, epoch 1899-12-30).
  3. Fallback: Month column (English name, e.g. "June").
Transactions A:L — no schema changes.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from budget import BudgetManager
from responses import get_report_response
from sheets import COL, get_all_rows
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Google Sheets / Excel date epoch
_GSHEET_EPOCH = datetime(1899, 12, 30)

_MONTH_NAME_TO_NUM: dict[str, str] = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def _parse_row_date(row: list) -> str | None:
    """Extract YYYY-MM from a Transactions row.

    Strategy:
      1. Date column as DD.MM.YYYY string → strptime
      2. Date column as Excel serial number (int/float)
      3. Fallback: Month column (English name) + current year
    Returns None if nothing can be parsed.
    """
    # ── 1. Try Date column as DD.MM.YYYY string ──
    if len(row) > COL["DATE"] and row[COL["DATE"]] is not None:
        date_val = row[COL["DATE"]]
        if isinstance(date_val, str) and date_val.strip():
            try:
                dt = datetime.strptime(date_val.strip(), "%d.%m.%Y")
                return dt.strftime("%Y-%m")
            except (ValueError, OverflowError):
                pass

        # ── 2. Try as Excel/Sheets serial number ──
        if isinstance(date_val, (int, float)):
            try:
                serial = int(date_val)
                if 1 <= serial <= 2958465:  # sensible range
                    dt = _GSHEET_EPOCH + timedelta(days=serial)
                    return dt.strftime("%Y-%m")
            except (OverflowError, ValueError, OSError):
                pass

    # ── 3. Fallback: Month column ──
    if len(row) > COL["MONTH"] and row[COL["MONTH"]]:
        month_str = str(row[COL["MONTH"]]).strip()
        month_num = _MONTH_NAME_TO_NUM.get(month_str.lower())
        if month_num:
            return f"{datetime.now().year}-{month_num}"

    return None


def _filter_period(rows: list[list], year_month: str) -> list[list]:
    """Keep only rows matching YYYY-MM (Date-primary, Month-fallback)."""
    return [r for r in rows if _parse_row_date(r) == year_month]


def _spending_by_account(rows: list[list]) -> list[dict]:
    """Per-account expense for the given rows.

    Excludes transfers (TRANSFER_ID).  Groups by ACCOUNT_NAME.
    Returns [{"name": str, "expense": float}, ...] sorted desc.
    """
    acc: dict[str, float] = {}

    for r in rows:
        if len(r) <= max(COL["TYPE"], COL["AMOUNT_UAH"]):
            continue
        if str(r[COL["TYPE"]] or "").strip().lower() != "expense":
            continue
        if (
            len(r) > COL["TRANSFER_ID"]
            and r[COL["TRANSFER_ID"]]
            and str(r[COL["TRANSFER_ID"]]).strip()
        ):
            continue

        try:
            amount = abs(float(r[COL["AMOUNT_UAH"]]))
        except (ValueError, TypeError):
            continue

        name = (
            str(r[COL["ACCOUNT_NAME"]]).strip()
            if len(r) > COL["ACCOUNT_NAME"] and r[COL["ACCOUNT_NAME"]]
            else ""
        )
        acc[name or "Без счета"] = acc.get(name or "Без счета", 0.0) + amount

    return sorted(
        ({"name": n, "expense": round(a, 2)} for n, a in acc.items()),
        key=lambda x: -x["expense"],
    )


def _summarize(rows: list[list]) -> dict:
    """Compute income, expense, category breakdown, and recurring total.

    Excludes transfers.  Recurring = Source starts with "recurring:".
    Returns {"income": float, "expense": float,
             "cats": dict[str, float], "recurring": float}
    """
    income = 0.0
    expense = 0.0
    cats: dict[str, float] = {}
    recurring = 0.0

    for r in rows:
        if len(r) <= max(COL["TYPE"], COL["AMOUNT_UAH"]):
            continue
        if (
            len(r) > COL["TRANSFER_ID"]
            and r[COL["TRANSFER_ID"]]
            and str(r[COL["TRANSFER_ID"]]).strip()
        ):
            continue

        t = str(r[COL["TYPE"]] or "").strip().lower()
        if t not in ("income", "expense"):
            continue

        try:
            amount = abs(float(r[COL["AMOUNT_UAH"]]))
        except (ValueError, TypeError):
            continue

        source = (
            str(r[COL["SOURCE"]]).strip()
            if len(r) > COL["SOURCE"] and r[COL["SOURCE"]]
            else ""
        )

        if t == "income":
            income += amount
        else:
            expense += amount
            cat = (
                str(r[COL["CATEGORY"]]).strip()
                if len(r) > COL["CATEGORY"] and r[COL["CATEGORY"]]
                else "Другое"
            )
            cats[cat] = cats.get(cat, 0.0) + amount
            if source.startswith("recurring:"):
                recurring += amount

    return {"income": income, "expense": expense, "cats": cats, "recurring": recurring}


def _top_categories(cats: dict[str, float], n: int = 5):
    """Top-N categories with bar and percent.  Returns (list, total)."""
    total = sum(cats.values())
    ranked = sorted(cats.items(), key=lambda x: -x[1])[:n]
    result = []
    for cat, amt in ranked:
        pct = (amt / total * 100) if total > 0 else 0
        filled = max(1, int(pct // 5))
        bar = "█" * filled + "░" * (20 - filled)
        result.append((cat, round(amt, 2), round(pct, 1), bar))
    return result, round(total, 2)


def _recurring_items(rows: list[list]) -> list[dict]:
    """Extract individual recurring expense transactions.

    Returns [{"title": str, "amount": float}, ...], sorted desc by amount.
    Title from AI Comment column, fallback to Category.
    Excludes transfers.
    """
    items: dict[str, float] = {}

    for r in rows:
        if len(r) <= max(COL["TYPE"], COL["AMOUNT_UAH"]):
            continue
        if str(r[COL["TYPE"]] or "").strip().lower() != "expense":
            continue
        if (
            len(r) > COL["TRANSFER_ID"]
            and r[COL["TRANSFER_ID"]]
            and str(r[COL["TRANSFER_ID"]]).strip()
        ):
            continue

        source = (
            str(r[COL["SOURCE"]]).strip()
            if len(r) > COL["SOURCE"] and r[COL["SOURCE"]]
            else ""
        )
        if not source.startswith("recurring:"):
            continue

        try:
            amount = abs(float(r[COL["AMOUNT_UAH"]]))
        except (ValueError, TypeError):
            continue

        comment = (
            str(r[COL["COMMENT"]]).strip()
            if len(r) > COL["COMMENT"] and r[COL["COMMENT"]]
            else ""
        )
        cat = (
            str(r[COL["CATEGORY"]]).strip()
            if len(r) > COL["CATEGORY"] and r[COL["CATEGORY"]]
            else ""
        )
        title = comment if comment else (cat if cat else "Регулярный платёж")

        items[title] = items.get(title, 0.0) + amount

    return sorted(
        ({"title": t, "amount": round(a, 2)} for t, a in items.items()),
        key=lambda x: -x["amount"],
    )


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Monthly financial report.

    /report              — текущий месяц
    /report 2026-06      — указанный месяц (YYYY-MM)

    Sections: income/expense/net, top-5 categories, budget & limit warnings,
    recurring spending, spending by account, Kesha commentary.
    """
    # ── Parse period argument ──
    now = datetime.now()
    period_ym: str
    period_display: str

    if context.args:
        period_ym = _parse_period_arg(context.args[0])
        if period_ym is None:
            await update.message.reply_html(
                "❌ Неправильный формат месяца.\n"
                "Используй: <code>/report 2026-06</code>"
            )
            return
        year, month = int(period_ym[:4]), int(period_ym[5:7])
        period_display = _month_display_ru(month, year)
    else:
        period_ym = now.strftime("%Y-%m")
        period_display = _month_display_ru(now.month, now.year)

    all_rows = await asyncio.to_thread(get_all_rows)

    if not all_rows:
        await update.message.reply_text(
            "📊 Данных пока нет. Добавь доходы и расходы — будет отчёт."
        )
        return

    rows = _filter_period(all_rows, period_ym)

    if not rows:
        await update.message.reply_html(
            f"📊 За <b>{period_display}</b> данных нет.\n"
            "Либо ты ничего не тратила, либо я что-то пропустил."
        )
        return

    s = _summarize(rows)
    income = s["income"]
    expense = s["expense"]
    net = income - expense
    cats = s["cats"]
    recurring = s["recurring"]

    logger.debug(
        "report period=%s total=%d included=%d income=%.0f expense=%.0f net=%.0f",
        period_ym,
        len(all_rows),
        len(rows),
        income,
        expense,
        net,
    )

    lines = [f"📊 <b>Отчёт за {period_display}</b>", ""]

    # ── Income / Expense / Net ──
    lines.append(f"💰 Доходы:  +{income:,.0f} UAH")
    lines.append(f"💸 Расходы: -{expense:,.0f} UAH")
    sign = "🟢" if net >= 0 else "🔴"
    lines.append(f"{sign} Итого:    {net:+,.0f} UAH")

    # ── Top-5 categories ──
    top, total_exp = _top_categories(cats)
    if top:
        lines.append("")
        lines.append("<b>🏆 Топ трат:</b>")
        for i, (cat, amt, pct, bar) in enumerate(top, 1):
            lines.append(
                f"{i}. {cat} — {amt:,.0f} UAH ({pct:.1f}%)\n   <code>{bar}</code>"
            )

    # ── Budget & limit warnings ──
    budget_pct = 0.0
    try:
        status = BudgetManager.get_budget_status(period_ym)
        if status is not None:
            budget_pct = status["percent"]
            pct100 = budget_pct * 100
            lines.append("")
            lines.append(
                f"<b>🎯 Бюджет:</b> {status['bar']} {pct100:.0f}%  —  "
                f"{status['spent']:,.0f} / {status['budget']:,.0f} UAH"
            )

        limits = BudgetManager.get_limits(period_ym)
        warned = [lim for lim in limits if lim["percent"] >= 0.8]
        if warned:
            lines.append("")
            lines.append("<b>⚠️ Лимиты:</b>")
            for lim in warned:
                p = lim["percent"] * 100
                if p >= 100:
                    over = lim["spent"] - lim["limit"]
                    lines.append(
                        f"  • {lim['category']}: "
                        f"{lim['spent']:,.0f} / {lim['limit']:,.0f} UAH"
                        f" — превышен на {over:,.0f} UAH"
                    )
                else:
                    lines.append(
                        f"  • {lim['category']}: "
                        f"{lim['spent']:,.0f} / {lim['limit']:,.0f} UAH"
                        f" — {p:.0f}%"
                    )
    except Exception as exc:
        logger.warning("Budget section failed in /report: %s", exc)

    # ── Recurring spending ──
    rec_items = _recurring_items(rows)
    if rec_items:
        rec_total = sum(it["amount"] for it in rec_items)
        rpct = rec_total / expense * 100 if expense > 0 else 0
        lines.append("")
        lines.append(
            f"<b>🔁 Регулярные платежи:</b> {rec_total:,.0f} UAH ({rpct:.1f}% расходов)"
        )
        for it in rec_items:
            lines.append(f"  • {it['title']} — {it['amount']:,.0f} UAH")
    else:
        lines.append("")
        lines.append("🔁 Регулярные: нет")

    # ── Spending by account ──
    acc = _spending_by_account(rows)
    if acc:
        lines.append("")
        lines.append("<b>💳 По счетам:</b>")
        for a in acc[:5]:
            name = a["name"]
            short = name[:4] + "..." + name[-4:] if len(name) > 10 else name
            lines.append(f"  • {short} — {a['expense']:,.0f} UAH")

    # ── Comparison with previous month ──
    prev_ym = _previous_month(period_ym)
    prev_rows = _filter_period(all_rows, prev_ym)
    if prev_rows:
        prev = _summarize(prev_rows)
        prev_income = prev["income"]
        prev_expense = prev["expense"]
        prev_net = prev_income - prev_expense
        d_expense = expense - prev_expense
        d_income = income - prev_income
        d_net = net - prev_net
        lines.append("")
        lines.append("<b>📉 Сравнение с прошлым месяцем:</b>")
        lines.append(f"  • Расходы: {d_expense:+,.0f} UAH")
        lines.append(f"  • Доходы: {d_income:+,.0f} UAH")
        lines.append(f"  • Итог: {d_net:+,.0f} UAH")
    else:
        lines.append("")
        lines.append("📉 Сравнение: за прошлый месяц данных нет.")

    # ── Kesha comment ──
    lines.append("")
    lines.append(f"<i>{get_report_response(net, expense, budget_pct)}</i>")

    await update.message.reply_html("\n".join(lines))


def _month_display_ru(month_num: int, year: int) -> str:
    names = [
        "",
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "ноябрь",
        "декабрь",
    ]
    return f"{names[month_num]} {year}"


def _parse_period_arg(arg: str) -> str | None:
    """Parse /report argument into YYYY-MM.  Returns None if invalid.

    Valid:  2026-06, 2025-12
    Invalid: 2026-6, abc, 2026-13, 2026-00
    """
    import re

    m = re.fullmatch(r"(\d{4})-(0[1-9]|1[0-2])", arg.strip())
    if not m:
        return None

    year = int(m.group(1))
    month = int(m.group(2))
    if year < 2000 or year > 2100:
        return None
    return f"{year:04d}-{month:02d}"


def _previous_month(period_ym: str) -> str:
    """Return the previous YYYY-MM.  2026-06 → 2026-05, 2026-01 → 2025-12."""
    year = int(period_ym[:4])
    month = int(period_ym[5:7])
    if month == 1:
        return f"{year - 1:04d}-12"
    return f"{year:04d}-{month - 1:02d}"
