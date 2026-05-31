"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { BalanceSkeleton } from "@/components/ui/Skeleton";
import { formatAmount } from "@/lib/formatters";
import type { Balance } from "@/lib/types";

interface BalanceCardProps {
  balance: Balance | null;
  loading?: boolean;
}

export function BalanceCard({ balance, loading }: BalanceCardProps) {
  if (loading || !balance) {
    return <BalanceSkeleton />;
  }

  const isPositive = balance.UAH >= 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>💰 Баланс</CardTitle>
      </CardHeader>
      <CardContent>
        <p
          className={`text-3xl font-bold tabular-nums tracking-tight font-mono animate-count ${
            isPositive ? "text-kesha-income" : "text-kesha-expense"
          }`}
        >
          {isPositive ? "+" : ""}
          {formatAmount(balance.UAH)} ₴
        </p>
        <div className="flex gap-4 mt-2 text-sm text-kesha-text-secondary">
          <span>
            <span className="text-kesha-text-tertiary">USD </span>
            {formatAmount(balance.USD)} $
          </span>
          <span>
            <span className="text-kesha-text-tertiary">EUR </span>
            {formatAmount(balance.EUR)} €
          </span>
        </div>
        <p className="text-xs text-kesha-text-secondary mt-4">
          {isPositive
            ? "Кеша доволен. Пока."
            : "Кеша в шоке. Хомяк, ты серьёзно?"}
        </p>
      </CardContent>
    </Card>
  );
}
