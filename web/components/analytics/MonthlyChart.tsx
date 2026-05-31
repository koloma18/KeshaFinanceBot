"use client";

import { useMemo } from "react";
import { Transaction } from "@/lib/types";
import { formatMonth } from "@/lib/formatters";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

interface MonthlyChartProps {
  transactions: Transaction[];
  months?: number;
}

export function MonthlyChart({ transactions, months = 12 }: MonthlyChartProps) {
  const data = useMemo(() => {
    const now = new Date();
    const cutOff = new Date(now.getFullYear(), now.getMonth() - months + 1, 1);

    const monthly: Record<string, { income: number; expense: number }> = {};

    for (const tx of transactions) {
      const parts = tx.date.split(".");
      if (parts.length !== 3) continue;
      const d = new Date(
        parseInt(parts[2]),
        parseInt(parts[1]) - 1,
        parseInt(parts[0]),
      );
      if (d < cutOff) continue;

      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;

      if (!monthly[key]) {
        monthly[key] = { income: 0, expense: 0 };
      }

      const amount =
        tx.amountUah !== ""
          ? tx.amountUah
          : tx.amountUsd !== ""
            ? tx.amountUsd
            : tx.amountEur !== ""
              ? tx.amountEur
              : 0;

      if (tx.type === "income") {
        monthly[key].income += amount;
      } else {
        monthly[key].expense += amount;
      }
    }

    return Object.entries(monthly)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, values]) => {
        const [year, monthIdx] = key.split("-");
        const monthName = MONTH_NAMES[parseInt(monthIdx) - 1] || "";
        const label = `${formatMonth(monthName)} ${year}`;
        return {
          month: label,
          income: Math.round(values.income),
          expense: Math.round(values.expense),
        };
      });
  }, [transactions, months]);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Динамика за {months} месяцев</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            description="Мало данных для графика. Добавь больше транзакций, и Кеша нарисует красивую картинку."
            icon="📉"
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Динамика за {months} месяцев</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--color-border)"
              />
              <XAxis
                dataKey="month"
                stroke="var(--color-text-secondary)"
                tick={{ fontSize: 11 }}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="var(--color-text-secondary)"
                tick={{ fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
                labelStyle={{ color: "var(--color-text-primary)" }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="expense"
                name="Расходы"
                stroke="var(--color-expense)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--color-expense)" }}
                activeDot={{ r: 5 }}
              />
              <Line
                type="monotone"
                dataKey="income"
                name="Доходы"
                stroke="var(--color-income)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--color-income)" }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
