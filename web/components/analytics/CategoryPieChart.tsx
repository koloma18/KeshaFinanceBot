"use client";

import { useMemo } from "react";
import { Transaction } from "@/lib/types";
import { formatCurrency } from "@/lib/formatters";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

const PIE_COLORS = [
  "#f87171", // red
  "#fb923c", // orange
  "#fbbf24", // amber
  "#a3e635", // lime
  "#34d399", // emerald
  "#2dd4bf", // teal
  "#38bdf8", // sky
  "#818cf8", // indigo
  "#a78bfa", // violet
  "#e879f9", // fuchsia
  "#f472b6", // pink
  "#94a3b8", // slate
];

interface CategoryPieChartProps {
  transactions: Transaction[];
}

export function CategoryPieChart({ transactions }: CategoryPieChartProps) {
  const data = useMemo(() => {
    const expenseByCategory: Record<string, number> = {};

    for (const tx of transactions) {
      if (tx.type !== "expense") continue;

      const amount =
        tx.amountUah !== ""
          ? tx.amountUah
          : tx.amountUsd !== ""
            ? tx.amountUsd
            : tx.amountEur !== ""
              ? tx.amountEur
              : 0;

      expenseByCategory[tx.category] =
        (expenseByCategory[tx.category] || 0) + amount;
    }

    const total = Object.values(expenseByCategory).reduce((s, v) => s + v, 0);

    return Object.entries(expenseByCategory)
      .map(([name, value]) => ({
        name,
        value: Math.round(value),
        percent: total > 0 ? ((value / total) * 100).toFixed(1) : "0",
      }))
      .sort((a, b) => b.value - a.value);
  }, [transactions]);

  if (data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Расходы по категориям</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            description="Нет расходов для анализа. Кеша подозревает, что ты живёшь за счёт воздуха."
            icon="🥧"
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Расходы по категориям</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={100}
                paddingAngle={2}
                dataKey="value"
                nameKey="name"
              >
                {data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={PIE_COLORS[index % PIE_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--color-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  fontSize: "13px",
                }}
                labelStyle={{ color: "var(--color-text-primary)" }}
                formatter={(value, _name) => {
                  const v = typeof value === "number" ? value : 0;
                  const n = typeof _name === "string" ? _name : "";
                  return [formatCurrency(v, "UAH"), n];
                }}
              />
              <Legend
                verticalAlign="bottom"
                height={36}
                iconSize={10}
                formatter={(value: string) => (
                  <span
                    className="text-xs"
                    style={{ color: "var(--color-text-primary)" }}
                  >
                    {value}
                  </span>
                )}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Table breakdown for small screens */}
        <div className="mt-4 space-y-1.5 md:hidden">
          {data.slice(0, 8).map((item) => (
            <div
              key={item.name}
              className="flex items-center justify-between text-sm"
            >
              <span className="text-kesha-text-primary">{item.name}</span>
              <span className="text-kesha-text-secondary tabular-nums">
                {formatCurrency(item.value, "UAH")}
                <span className="ml-1 text-xs text-kesha-text-tertiary">
                  ({item.percent}%)
                </span>
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
