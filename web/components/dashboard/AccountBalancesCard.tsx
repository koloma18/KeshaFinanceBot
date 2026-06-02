"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { CardSkeleton } from "@/components/ui/Skeleton";
import type { AccountBalance } from "@/lib/types";

function formatBalance(amount: number, currency: string): string {
  const sym =
    currency === "UAH"
      ? "₴"
      : currency === "USD"
        ? "$"
        : currency === "EUR"
          ? "€"
          : currency;
  const sign = amount < 0 ? "-" : "";
  return `${sign}${Math.abs(amount).toLocaleString("uk-UA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${sym}`;
}

export function AccountBalancesCard() {
  const [accounts, setAccounts] = useState<AccountBalance[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/sheets/account-balances")
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setAccounts(null);
          return;
        }
        setAccounts(Array.isArray(data) ? data : []);
      })
      .catch(() => setAccounts(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <CardSkeleton />;
  if (!accounts || accounts.length === 0) return null;

  const total = accounts.reduce((sum, a) => sum + a.balance, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>📊 Счета</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {accounts.map((acc) => (
          <div
            key={acc.name}
            className="flex justify-between items-center py-2 border-b border-kesha-border last:border-0"
          >
            <div>
              <p className="text-sm font-medium text-kesha-text-primary">
                {acc.name}
              </p>
              <p className="text-xs text-kesha-text-tertiary">
                {acc.currency}
                {(acc.income > 0 || acc.expense > 0) &&
                  ` · +${acc.income.toLocaleString("uk-UA")} / -${acc.expense.toLocaleString("uk-UA")} (${acc.transactionCount} оп.)`}
              </p>
            </div>
            <p
              className={`text-sm font-bold tabular-nums ${acc.balance >= 0 ? "text-kesha-income" : "text-kesha-expense"}`}
            >
              {formatBalance(acc.balance, acc.currency)}
            </p>
          </div>
        ))}

        {accounts.length > 1 && (
          <div className="flex justify-between items-center pt-2 border-t border-kesha-border">
            <p className="text-sm font-semibold text-kesha-text-primary">
              Итого
            </p>
            <p
              className={`text-sm font-bold tabular-nums ${total >= 0 ? "text-kesha-income" : "text-kesha-expense"}`}
            >
              {formatBalance(total, "UAH")}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
