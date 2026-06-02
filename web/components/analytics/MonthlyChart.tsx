"use client";

import { useMemo } from "react";
import { Transaction } from "@/lib/types";
import { formatMonth } from "@/lib/formatters";
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

function formatTick(v: number): string {
  if (v >= 1000000) return `${(v / 1000000).toFixed(1)}M`;
  if (v >= 1000) return `${(v / 1000).toFixed(0)}K`;
  return String(v);
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
      if (!monthly[key]) monthly[key] = { income: 0, expense: 0 };
      const amount =
        tx.amountUah !== ""
          ? tx.amountUah
          : tx.amountUsd !== ""
            ? tx.amountUsd
            : tx.amountEur !== ""
              ? tx.amountEur
              : 0;
      if (tx.type === "income") monthly[key].income += amount;
      else if (tx.type === "expense") monthly[key].expense += Math.abs(amount);
    }
    return Object.entries(monthly)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, values]) => {
        const [year, monthIdx] = key.split("-");
        const monthName = MONTH_NAMES[parseInt(monthIdx) - 1] || "";
        return {
          month: `${formatMonth(monthName)} ${year}`,
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
          <EmptyState description="Мало данных для графика." icon="📉" />
        </CardContent>
      </Card>
    );
  }

  const W = 600;
  const H = 300;
  const PAD = { top: 20, right: 16, bottom: 40, left: 56 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const maxVal = Math.max(...data.map((d) => Math.max(d.income, d.expense)), 1);
  const xScale = (i: number) =>
    PAD.left + (i / Math.max(data.length - 1, 1)) * plotW;
  const yScale = (v: number) => PAD.top + plotH - (v / maxVal) * plotH;
  const linePath = (vals: number[]) =>
    vals
      .map((v, i) => `${i === 0 ? "M" : "L"}${xScale(i)},${yScale(v)}`)
      .join(" ");
  const incomeVals = data.map((d) => d.income);
  const expenseVals = data.map((d) => d.expense);
  const yTicks = 4;
  const yTickVals = Array.from({ length: yTicks + 1 }, (_, i) =>
    Math.round((maxVal / yTicks) * i),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Динамика за {months} месяцев</CardTitle>
      </CardHeader>
      <CardContent>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full h-auto"
          style={{ minWidth: "280px" }}
        >
          {yTickVals.map((v) => (
            <line
              key={`g-${v}`}
              x1={PAD.left}
              y1={yScale(v)}
              x2={W - PAD.right}
              y2={yScale(v)}
              stroke="var(--color-border)"
              strokeDasharray="3 3"
              strokeWidth={0.5}
            />
          ))}
          {data.map((d, i) => {
            const show =
              data.length <= 6 ||
              i % Math.ceil(data.length / 6) === 0 ||
              i === data.length - 1;
            if (!show) return null;
            return (
              <text
                key={`x-${i}`}
                x={xScale(i)}
                y={H - 10}
                textAnchor="middle"
                fill="var(--color-text-secondary)"
                fontSize={10}
              >
                {d.month.split(" ")[0]}
              </text>
            );
          })}
          {yTickVals.map((v) => (
            <text
              key={`y-${v}`}
              x={PAD.left - 8}
              y={yScale(v) + 4}
              textAnchor="end"
              fill="var(--color-text-secondary)"
              fontSize={10}
            >
              {formatTick(v)}
            </text>
          ))}
          <path
            d={linePath(expenseVals)}
            fill="none"
            stroke="var(--color-expense)"
            strokeWidth={2}
          />
          <path
            d={linePath(incomeVals)}
            fill="none"
            stroke="var(--color-income)"
            strokeWidth={2}
          />
          {expenseVals.map((v, i) => (
            <circle
              key={`ed-${i}`}
              cx={xScale(i)}
              cy={yScale(v)}
              r={3}
              fill="var(--color-expense)"
            />
          ))}
          {incomeVals.map((v, i) => (
            <circle
              key={`id-${i}`}
              cx={xScale(i)}
              cy={yScale(v)}
              r={3}
              fill="var(--color-income)"
            />
          ))}
          <line
            x1={PAD.left}
            y1={H + 14}
            x2={PAD.left + 20}
            y2={H + 14}
            stroke="var(--color-expense)"
            strokeWidth={2}
          />
          <text
            x={PAD.left + 26}
            y={H + 18}
            fill="var(--color-text-secondary)"
            fontSize={11}
          >
            Расходы
          </text>
          <line
            x1={PAD.left + 80}
            y1={H + 14}
            x2={PAD.left + 100}
            y2={H + 14}
            stroke="var(--color-income)"
            strokeWidth={2}
          />
          <text
            x={PAD.left + 106}
            y={H + 18}
            fill="var(--color-text-secondary)"
            fontSize={11}
          >
            Доходы
          </text>
        </svg>
      </CardContent>
    </Card>
  );
}
