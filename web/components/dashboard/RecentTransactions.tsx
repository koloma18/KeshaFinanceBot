"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { RowSkeleton } from "@/components/ui/Skeleton";
import { getCategoryEmoji } from "@/lib/category-emoji";
import { formatAmountInt } from "@/lib/formatters";
import type { Transaction } from "@/lib/types";

interface RecentTransactionsProps {
  transactions: Transaction[];
  loading?: boolean;
}

function formatDateShort(dateStr: string): string {
  const parts = dateStr.split(".");
  if (parts.length === 3) {
    return `${parts[0]}.${parts[1]}`;
  }
  return dateStr;
}

export function RecentTransactions({
  transactions,
  loading,
}: RecentTransactionsProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>🕐 Последние операции</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="divide-y divide-kesha-border">
            {Array.from({ length: 5 }).map((_, i) => (
              <RowSkeleton key={i} />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!transactions || transactions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>🕐 Последние операции</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState variant="dashboard" />
        </CardContent>
      </Card>
    );
  }

  const recent = transactions.slice(0, 5);

  return (
    <Card>
      <CardHeader>
        <CardTitle>🕐 Последние операции</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-kesha-border">
          {recent.map((tx, idx) => {
            const isIncome = tx.type === "income";
            const rawAmount = tx.amountUah !== "" ? tx.amountUah : 0;
            const displayAmount = Math.abs(rawAmount);

            return (
              <div
                key={`${tx.date}-${tx.category}-${tx.amountUah}-${tx.comment}`}
                className="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
              >
                <span className="text-lg shrink-0 w-8 h-8 flex items-center justify-center">
                  {getCategoryEmoji(tx.category)}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-kesha-text-primary truncate">
                    {tx.category}
                  </p>
                  <p className="text-xs text-kesha-text-tertiary">
                    {formatDateShort(tx.date)}
                    {tx.comment ? ` · ${tx.comment}` : ""}
                  </p>
                </div>
                <span
                  className={`font-semibold tabular-nums text-sm shrink-0 ${
                    isIncome ? "text-kesha-income" : "text-kesha-expense"
                  }`}
                >
                  {isIncome ? "+" : "-"}
                  {formatAmountInt(displayAmount)} ₴
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
