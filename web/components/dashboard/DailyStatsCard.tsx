"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { formatAmountInt } from "@/lib/formatters";

interface DailyStatsCardProps {
  title: string;
  income: number;
  expense: number;
  total: number;
  loading?: boolean;
}

export function DailyStatsCard({
  title,
  income,
  expense,
  total,
  loading,
}: DailyStatsCardProps) {
  if (loading) {
    return <CardSkeleton />;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
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
                total >= 0 ? "text-kesha-income" : "text-kesha-expense"
              }`}
            >
              {total >= 0 ? "+" : ""}
              {formatAmountInt(total)} ₴
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
