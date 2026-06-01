"use client";

import { useMemo } from "react";
import { Transaction } from "@/lib/types";
import { formatCurrency } from "@/lib/formatters";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";

interface CategoryPieChartProps {
  transactions: Transaction[];
}

function polar(cx: number, cy: number, r: number, angle: number) {
  const rad = ((angle - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function donutSlice(
  cx: number,
  cy: number,
  ir: number,
  or: number,
  start: number,
  end: number,
): string {
  const so = polar(cx, cy, or, end);
  const eo = polar(cx, cy, or, start);
  const si = polar(cx, cy, ir, end);
  const ei = polar(cx, cy, ir, start);
  const la = end - start > 180 ? 1 : 0;
  return [
    `M ${so.x} ${so.y}`,
    `A ${or} ${or} 0 ${la} 0 ${eo.x} ${eo.y}`,
    `L ${ei.x} ${ei.y}`,
    `A ${ir} ${ir} 0 ${la} 1 ${si.x} ${si.y}`,
    "Z",
  ].join(" ");
}

const PIE = [
  "var(--color-expense)",
  "var(--chart-2, #fb923c)",
  "var(--color-accent)",
  "var(--chart-4, #a3e635)",
  "var(--color-income)",
  "var(--chart-6, #2dd4bf)",
  "var(--chart-7, #38bdf8)",
  "var(--chart-8, #818cf8)",
  "var(--chart-9, #a78bfa)",
  "var(--chart-10, #e879f9)",
  "var(--chart-11, #f472b6)",
  "var(--chart-12, #94a3b8)",
];

export function CategoryPieChart({ transactions }: CategoryPieChartProps) {
  const data = useMemo(() => {
    const m: Record<string, number> = {};
    for (const tx of transactions) {
      if (tx.type !== "expense") continue;
      const a =
        tx.amountUah !== ""
          ? tx.amountUah
          : tx.amountUsd !== ""
            ? tx.amountUsd
            : tx.amountEur !== ""
              ? tx.amountEur
              : 0;
      m[tx.category] = (m[tx.category] || 0) + a;
    }
    const total = Object.values(m).reduce((s, v) => s + v, 0);
    return Object.entries(m)
      .map(([name, value]) => ({
        name,
        value: Math.round(value),
        pct: total > 0 ? (value / total) * 100 : 0,
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
          <EmptyState description="Нет расходов для анализа." icon="🥧" />
        </CardContent>
      </Card>
    );
  }

  const cx = 140;
  const cy = 140;
  const or = 100;
  const ir = 55;
  const total = data.reduce((s, d) => s + d.value, 0);
  let angle = 0;
  const slices = data.map((item) => {
    const a = (item.value / total) * 360;
    const s = angle;
    angle += a;
    return { ...item, start: s, end: angle };
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Расходы по категориям</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col items-center">
          <svg viewBox="0 0 280 280" className="w-full max-w-[280px] h-auto">
            {slices.map((s, i) => (
              <path
                key={s.name}
                d={donutSlice(cx, cy, ir, or, s.start, s.end)}
                fill={PIE[i % PIE.length]}
                stroke="transparent"
                strokeWidth={1}
              />
            ))}
            <text
              x={cx}
              y={cy - 6}
              textAnchor="middle"
              fill="var(--color-text-secondary)"
              fontSize={11}
            >
              Всего
            </text>
            <text
              x={cx}
              y={cy + 14}
              textAnchor="middle"
              fill="var(--color-text-primary)"
              fontSize={15}
              fontWeight={600}
            >
              {formatCurrency(total, "UAH")}
            </text>
          </svg>
          <div className="w-full mt-4 grid grid-cols-2 gap-x-4 gap-y-1.5">
            {slices.slice(0, PIE.length).map((s, i) => (
              <div key={s.name} className="flex items-center gap-2 text-xs">
                <span
                  className="w-2.5 h-2.5 rounded-sm shrink-0"
                  style={{ backgroundColor: PIE[i % PIE.length] }}
                />
                <span className="text-kesha-text-primary truncate">
                  {s.name}
                </span>
                <span className="text-kesha-text-tertiary tabular-nums ml-auto">
                  {s.pct.toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
