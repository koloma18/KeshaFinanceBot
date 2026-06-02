"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { CardSkeleton } from "@/components/ui/Skeleton";

interface MonoAccount {
  id: string;
  balance: number;
  creditLimit: number;
  currency: string;
  maskedPan: string;
  type: string;
  iban: string;
}

function formatBalance(amount: number, currency: string): string {
  const sym = currency === "UAH" ? "₴" : currency === "USD" ? "$" : currency === "EUR" ? "€" : currency;
  const sign = amount < 0 ? "-" : "";
  return `${sign}${Math.abs(amount).toLocaleString("uk-UA", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${sym}`;
}

export function MonoAccountsCard() {
  const [accounts, setAccounts] = useState<MonoAccount[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch("/api/mono/accounts")
      .then((r) => r.json())
      .then((data) => {
        if (data.error) { setError(true); return; }
        setAccounts(Array.isArray(data) ? data : []);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <CardSkeleton />;
  if (error || !accounts || accounts.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>💳 Счета Monobank</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {accounts.map((acc) => (
          <div key={acc.id} className="flex justify-between items-center py-2 border-b border-kesha-border last:border-0">
            <div>
              <p className="text-sm font-medium text-kesha-text-primary">{acc.maskedPan}</p>
              <p className="text-xs text-kesha-text-tertiary">
                {acc.type} · {acc.currency}
                {acc.creditLimit > 0 ? ` · кредит ${formatBalance(acc.creditLimit, acc.currency)}` : ""}
              </p>
            </div>
            {(() => {
              const available = acc.balance - acc.creditLimit;
              return (
                <p className={`text-sm font-bold tabular-nums ${available >= 0 ? "text-kesha-income" : "text-kesha-expense"}`}>
                  {formatBalance(available, acc.currency)}
                </p>
              );
            })()}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
