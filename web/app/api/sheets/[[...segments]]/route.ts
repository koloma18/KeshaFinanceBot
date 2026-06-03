import { NextRequest, NextResponse } from "next/server";
import { SimpleCache } from "@/lib/cache";
import { checkRateLimit } from "@/lib/rateLimiter";
import { sheetsClient } from "@/lib/sheets";
import type {
  Transaction,
  Balance,
  BudgetStatus,
  CategoryLimit,
  AccountBalance,
} from "@/lib/types";

const cache = new SimpleCache(30000);

export async function GET(
  request: NextRequest,
  { params }: { params: { segments?: string[] } },
) {
  if (!checkRateLimit()) {
    return NextResponse.json({ error: "Too Many Requests" }, { status: 429 });
  }

  const segments = params.segments ?? [];
  const action = segments[0] ?? "";

  try {
    switch (action) {
      case "transactions": {
        const cached = cache.get("transactions") as Transaction[] | undefined;
        if (cached) return NextResponse.json(cached);

        const transactions = await sheetsClient.getTransactions();
        cache.set("transactions", transactions);
        return NextResponse.json(transactions);
      }

      case "balance": {
        const cached = cache.get("balance") as Balance | undefined;
        if (cached) return NextResponse.json(cached);

        const balance = await sheetsClient.getBalance();
        cache.set("balance", balance);
        return NextResponse.json(balance);
      }

      case "budget": {
        const cached = cache.get("budget") as BudgetStatus | undefined;
        if (cached) return NextResponse.json(cached);

        const budgetRows = await sheetsClient.getBudgetRows();
        const transactions = await sheetsClient.getTransactions();

        const now = new Date();
        const currentMonth = now.toLocaleString("en-US", { month: "long" });

        const generalBudget = budgetRows.find(
          (r) => r.month === currentMonth && r.type === "budget",
        );

        const totalSpent = transactions
          .filter(
            (t) =>
              t.type === "expense" &&
              t.month === currentMonth &&
              !t.transferId?.trim(),
          )
          .reduce((sum, t) => sum + (t.amountUah !== "" ? t.amountUah : 0), 0);

        const budget = generalBudget?.limit || 0;
        const spent = Math.abs(totalSpent);
        const remaining = budget - spent;
        const percent = budget > 0 ? Math.min((spent / budget) * 100, 100) : 0;
        const bar = _getBar(percent);

        const result: BudgetStatus = { budget, spent, remaining, percent, bar };
        cache.set("budget", result);
        return NextResponse.json(result);
      }

      case "limits": {
        const cached = cache.get("limits") as CategoryLimit[] | undefined;
        if (cached) return NextResponse.json(cached);

        const now = new Date();
        const currentMonth = now.toLocaleString("en-US", { month: "long" });

        const budgetRows = await sheetsClient.getBudgetRows();
        const categoryLimits = budgetRows.filter(
          (r) =>
            (r.month === currentMonth || r.month === "") && r.type === "limit",
        );

        const monthStr = now.toISOString().slice(0, 7);
        const spending = await sheetsClient.getCategoriesSpending(monthStr);

        const result: CategoryLimit[] = categoryLimits.map((cl) => {
          const spent = spending[cl.category] || 0;
          const percent =
            cl.limit > 0 ? Math.min((spent / cl.limit) * 100, 100) : 0;
          return {
            category: cl.category,
            limit: cl.limit,
            spent,
            percent,
            bar: _getBar(percent),
          };
        });

        cache.set("limits", result);
        return NextResponse.json(result);
      }

      case "account-balances": {
        const cached = cache.get("account-balances") as
          | AccountBalance[]
          | undefined;
        if (cached) return NextResponse.json(cached);

        const result = await sheetsClient.getAccountBalances();
        cache.set("account-balances", result);
        return NextResponse.json(result);
      }

      default:
        return NextResponse.json(
          { error: `Unknown action: ${action || "empty"}` },
          { status: 400 },
        );
    }
  } catch (error) {
    console.error(`[API] /api/sheets/${action} error:`, error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 },
    );
  }
}

function _getBar(percent: number): string {
  const filled = Math.round(percent / 10);
  const empty = 10 - filled;
  return "█".repeat(filled) + "░".repeat(empty);
}
