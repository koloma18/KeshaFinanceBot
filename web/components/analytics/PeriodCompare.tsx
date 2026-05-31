"use client";

import { useMemo, useState } from "react";
import { Transaction } from "@/lib/types";
import { formatCurrency } from "@/lib/formatters";
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

const MONTH_NAMES_RU: Record<string, string> = {
  January: "январь",
  February: "февраль",
  March: "март",
  April: "апрель",
  May: "май",
  June: "июнь",
  July: "июль",
  August: "август",
  September: "сентябрь",
  October: "октябрь",
  November: "ноябрь",
  December: "декабрь",
};

interface PeriodCompareProps {
  transactions: Transaction[];
}

function getKeshaComment(
  deltaIncome: number,
  deltaExpense: number,
  aIncome: number,
  aExpense: number,
  bIncome: number,
  bExpense: number,
): string {
  const parts: string[] = [];

  if (deltaExpense > 10) {
    parts.push(
      "Расходы подскочили. Кеша осуждает, но понимает — инфляция, однако.",
    );
  } else if (deltaExpense < -10) {
    parts.push(
      "Расходы упали! Ты в режиме экономии или просто не выходила из дома?",
    );
  } else {
    parts.push("По расходам стабильно. Кеша доволен.");
  }

  if (deltaIncome > 10) {
    parts.push("Доход вырос — есть повод для сдержанного оптимизма.");
  } else if (deltaIncome < -10) {
    parts.push(
      "Доход просел. Кеша сочувствует и рекомендует проверить подушку.",
    );
  } else {
    parts.push("Доход на прежнем уровне. Без сюрпризов — уже хорошо.");
  }

  const aNet = aIncome - aExpense;
  const bNet = bIncome - bExpense;

  if (aNet > 0 && bNet <= 0) {
    parts.push("Был плюс — стал минус. Кеша в лёгком недоумении.");
  } else if (aNet <= 0 && bNet > 0) {
    parts.push("Был минус — стал плюс. Кеша аплодирует стоя!");
  } else if (aNet > 0 && bNet > 0 && bNet > aNet) {
    parts.push("Чистый результат улучшился. Так держать!");
  } else if (aNet < 0 && bNet < 0 && bNet < aNet) {
    parts.push("Чистый результат ухудшился. Кеша надеется, что это временно.");
  }

  return parts.join(" ");
}

function getMonthOptions(): { value: string; label: string }[] {
  const options: { value: string; label: string }[] = [];
  const now = new Date();
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const monthName = MONTH_NAMES[d.getMonth()] || "";
    options.push({
      value,
      label: `${MONTH_NAMES_RU[monthName] || monthName} ${d.getFullYear()}`,
    });
  }
  return options;
}

function getMonthStats(
  transactions: Transaction[],
  year: number,
  month: number,
): { income: number; expense: number } {
  let income = 0;
  let expense = 0;

  for (const tx of transactions) {
    const parts = tx.date.split(".");
    if (parts.length !== 3) continue;
    const d = new Date(
      parseInt(parts[2]),
      parseInt(parts[1]) - 1,
      parseInt(parts[0]),
    );
    if (d.getFullYear() !== year || d.getMonth() !== month) continue;

    const amount =
      tx.amountUah !== ""
        ? tx.amountUah
        : tx.amountUsd !== ""
          ? tx.amountUsd
          : tx.amountEur !== ""
            ? tx.amountEur
            : 0;

    if (tx.type === "income") income += amount;
    else expense += amount;
  }

  return { income: Math.round(income), expense: Math.round(expense) };
}

export function PeriodCompare({ transactions }: PeriodCompareProps) {
  const monthOptions = useMemo(getMonthOptions, []);
  const now = new Date();

  const [monthA, setMonthA] = useState(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`,
  );
  const [monthB, setMonthB] = useState(
    `${now.getFullYear()}-${String(now.getMonth()).padStart(2, "0")}`,
  );

  const stats = useMemo(() => {
    const parseMonth = (m: string) => {
      const [y, mo] = m.split("-").map(Number);
      return { year: y, month: mo };
    };

    const a = parseMonth(monthA);
    const b = parseMonth(monthB);

    const statsA = getMonthStats(transactions, a.year, a.month);
    const statsB = getMonthStats(transactions, b.year, b.month);

    const deltaIncome =
      statsB.income > 0
        ? Math.round(((statsA.income - statsB.income) / statsB.income) * 100)
        : statsA.income > 0
          ? 100
          : 0;

    const deltaExpense =
      statsB.expense > 0
        ? Math.round(((statsA.expense - statsB.expense) / statsB.expense) * 100)
        : statsA.expense > 0
          ? 100
          : 0;

    return {
      monthA: statsA,
      monthB: statsB,
      deltaIncome,
      deltaExpense,
      comment: getKeshaComment(
        deltaIncome,
        deltaExpense,
        statsA.income,
        statsA.expense,
        statsB.income,
        statsB.expense,
      ),
    };
  }, [transactions, monthA, monthB]);

  function Delta({ value }: { value: number }) {
    if (value === 0)
      return <span className="text-xs text-kesha-text-tertiary">—</span>;
    const isPositive = value > 0;
    return (
      <span
        className={`text-xs font-medium tabular-nums ${
          isPositive ? "text-kesha-expense" : "text-kesha-income"
        }`}
      >
        {isPositive ? "+" : ""}
        {value}%
      </span>
    );
  }

  if (transactions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Сравнение периодов</CardTitle>
        </CardHeader>
        <CardContent>
          <EmptyState
            description="Нечего сравнивать. Добавь транзакции, и Кеша с радостью укажет на разницу."
            icon="⚖️"
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Сравнение периодов</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
            <div>
              <label className="mb-1 block text-xs text-kesha-text-tertiary">
                Период A
              </label>
              <select
                value={monthA}
                onChange={(e) => setMonthA(e.target.value)}
                className="rounded-lg border border-kesha-border bg-kesha-card px-3 py-1.5 text-sm text-kesha-text-primary outline-none focus:border-kesha-accent/50"
              >
                {monthOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <span className="hidden sm:block text-kesha-text-tertiary mt-5">
              vs
            </span>
            <div>
              <label className="mb-1 block text-xs text-kesha-text-tertiary">
                Период B
              </label>
              <select
                value={monthB}
                onChange={(e) => setMonthB(e.target.value)}
                className="rounded-lg border border-kesha-border bg-kesha-card px-3 py-1.5 text-sm text-kesha-text-primary outline-none focus:border-kesha-accent/50"
              >
                {monthOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <div className="text-xs text-kesha-text-tertiary">Показатель</div>
          <div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <span className="text-kesha-text-tertiary text-center">A</span>
              <span className="text-kesha-text-tertiary text-center">B</span>
            </div>
          </div>

          <div className="col-span-2 border-t border-kesha-border" />

          <div className="text-sm text-kesha-text-primary">Доход</div>
          <div>
            <div className="grid grid-cols-2 gap-2 text-center">
              <span className="text-sm text-kesha-income font-medium tabular-nums">
                {formatCurrency(stats.monthA.income, "UAH")}
              </span>
              <span className="text-sm text-kesha-income font-medium tabular-nums">
                {formatCurrency(stats.monthB.income, "UAH")}
              </span>
            </div>
          </div>

          <div className="text-sm text-kesha-text-primary">Расход</div>
          <div>
            <div className="grid grid-cols-2 gap-2 text-center">
              <span className="text-sm text-kesha-expense font-medium tabular-nums">
                {formatCurrency(stats.monthA.expense, "UAH")}
              </span>
              <span className="text-sm text-kesha-expense font-medium tabular-nums">
                {formatCurrency(stats.monthB.expense, "UAH")}
              </span>
            </div>
          </div>

          <div className="text-sm text-kesha-text-primary">Итог</div>
          <div>
            <div className="grid grid-cols-2 gap-2 text-center">
              <span
                className={`text-sm font-semibold tabular-nums ${
                  stats.monthA.income - stats.monthA.expense >= 0
                    ? "text-kesha-income"
                    : "text-kesha-expense"
                }`}
              >
                {formatCurrency(
                  stats.monthA.income - stats.monthA.expense,
                  "UAH",
                )}
              </span>
              <span
                className={`text-sm font-semibold tabular-nums ${
                  stats.monthB.income - stats.monthB.expense >= 0
                    ? "text-kesha-income"
                    : "text-kesha-expense"
                }`}
              >
                {formatCurrency(
                  stats.monthB.income - stats.monthB.expense,
                  "UAH",
                )}
              </span>
            </div>
          </div>

          <div className="text-sm text-kesha-text-primary">Дельта</div>
          <div>
            <div className="grid grid-cols-2 gap-2 text-center">
              <Delta value={stats.deltaIncome} />
              <Delta value={stats.deltaExpense} />
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-lg bg-kesha-card border border-kesha-border p-3">
          <p className="text-xs text-kesha-text-secondary italic leading-relaxed">
            🐿️ {stats.comment}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
