"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { formatAmountInt } from "@/lib/formatters";

interface MonthlyReportCardProps {
  monthLabel: string;
  income: number;
  expense: number;
  loading?: boolean;
  empty?: boolean;
}

function keshaComment(net: number): string {
  if (net > 10000) return "Кеша гордится тобой. Шикарный месяц!";
  if (net > 0) return "Кеша доволен. Так держать.";
  if (net === 0) return "Месяц в ноль. Стабильность.";
  if (net > -5000) return "Кеша замечает утечку орехов.";
  return "Кеша в шоке от таких трат.";
}

export function MonthlyReportCard({
  monthLabel,
  income,
  expense,
  loading,
  empty,
}: MonthlyReportCardProps) {
  if (loading) {
    return <SkeletonCard />;
  }

  if (empty) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{monthLabel}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-kesha-text-secondary text-sm text-center py-4">
            Нет данных за этот месяц
          </p>
        </CardContent>
      </Card>
    );
  }

  const net = income - expense;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{monthLabel}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-kesha-text-secondary">Доход</span>
          <span className="text-kesha-income font-semibold tabular-nums">
            +{formatAmountInt(income)} ₴
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-kesha-text-secondary">Расход</span>
          <span className="text-kesha-expense font-semibold tabular-nums">
            -{formatAmountInt(expense)} ₴
          </span>
        </div>
        <div className="border-t border-kesha-border pt-2 mt-1">
          <div className="flex justify-between items-center">
            <span className="text-sm text-kesha-text-secondary">Итог</span>
            <span
              className={`font-bold tabular-nums ${
                net >= 0 ? "text-kesha-income" : "text-kesha-expense"
              }`}
            >
              {net >= 0 ? "+" : ""}
              {formatAmountInt(net)} ₴
            </span>
          </div>
        </div>
        <p className="text-xs text-kesha-accent italic pt-1">
          🐿️ {keshaComment(net)}
        </p>
      </CardContent>
    </Card>
  );
}
