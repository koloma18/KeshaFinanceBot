"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { formatAmountInt } from "@/lib/formatters";
import type { BudgetStatus } from "@/lib/types";

interface BudgetCardProps {
  budget: BudgetStatus | null;
  loading?: boolean;
}

export function BudgetCard({ budget, loading }: BudgetCardProps) {
  if (loading) {
    return <CardSkeleton />;
  }

  if (!budget) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>📊 Бюджет</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-kesha-text-secondary text-sm">
            Бюджет не установлен. Кеша живёт одним днём.
          </p>
        </CardContent>
      </Card>
    );
  }

  const isOverBudget = budget.percent >= 100;

  return (
    <Card>
      <CardHeader>
        <CardTitle>📊 Бюджет месяца</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex justify-between items-center text-sm">
          <span className="text-kesha-text-secondary">
            Потрачено {formatAmountInt(budget.spent)} ₴
          </span>
          <span className="text-kesha-text-tertiary">
            из {formatAmountInt(budget.budget)} ₴
          </span>
        </div>

        <ProgressBar
          percent={budget.percent}
          color={isOverBudget ? "red" : "yellow"}
        />

        <div className="flex justify-between items-center text-sm">
          {isOverBudget ? (
            <span className="text-kesha-expense font-medium">
              🔥 Превышен на {formatAmountInt(-budget.remaining)} ₴
            </span>
          ) : (
            <span className="text-kesha-income font-medium">
              Осталось {formatAmountInt(budget.remaining)} ₴
            </span>
          )}
          <span className="text-kesha-text-tertiary tabular-nums">
            {budget.percent.toFixed(0)}%
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
