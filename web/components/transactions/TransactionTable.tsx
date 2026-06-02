"use client";

import { Transaction } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/formatters";
import { getCategoryEmoji } from "@/lib/category-emoji";
import { Badge } from "@/components/ui/Badge";

function getAmount(transaction: Transaction): {
  value: number;
  label: string;
} {
  // Amounts in sheet are negative for expenses — use abs for display
  if (transaction.amountUah !== "")
    return {
      value: Math.abs(transaction.amountUah),
      label: formatCurrency(Math.abs(transaction.amountUah), "UAH"),
    };
  if (transaction.amountUsd !== "")
    return {
      value: Math.abs(transaction.amountUsd),
      label: formatCurrency(Math.abs(transaction.amountUsd), "USD"),
    };
  if (transaction.amountEur !== "")
    return {
      value: Math.abs(transaction.amountEur),
      label: formatCurrency(Math.abs(transaction.amountEur), "EUR"),
    };
  return { value: 0, label: "—" };
}

interface SortConfig {
  column: string;
  direction: "asc" | "desc";
}

interface TransactionTableProps {
  transactions: Transaction[];
  sortConfig: SortConfig;
  onSort: (column: string) => void;
}

function SortIcon({ column, config }: { column: string; config: SortConfig }) {
  if (config.column !== column) {
    return <span className="ml-1 text-kesha-text-tertiary">↕</span>;
  }
  return (
    <span className="ml-1 text-kesha-accent">
      {config.direction === "asc" ? "↑" : "↓"}
    </span>
  );
}

export function TransactionTable({
  transactions,
  sortConfig,
  onSort,
}: TransactionTableProps) {
  if (transactions.length === 0) {
    return (
      <div className="py-8 text-center text-sm text-kesha-text-tertiary">
        Нет транзакций по выбранным фильтрам. Кеша одобряет экономию… или
        подозревает, что ты что-то скрываешь. 🐿️
      </div>
    );
  }

  const sortable = (col: string) =>
    ["date", "category"].includes(col) ? "cursor-pointer select-none" : "";

  return (
    <>
      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-kesha-border text-left text-xs uppercase tracking-wider text-kesha-text-tertiary">
              <th
                className={`pb-2 pr-3 font-medium ${sortable("date")}`}
                onClick={() => onSort("date")}
              >
                Дата
                <SortIcon column="date" config={sortConfig} />
              </th>
              <th className="pb-2 pr-3 font-medium">Тип</th>
              <th
                className={`pb-2 pr-3 font-medium ${sortable("category")}`}
                onClick={() => onSort("category")}
              >
                Категория
                <SortIcon column="category" config={sortConfig} />
              </th>
              <th className="pb-2 pr-3 text-right font-medium">Сумма</th>
              <th className="pb-2 font-medium">Комментарий</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx, i) => {
              const amount = getAmount(tx);
              return (
                <tr
                  key={`${tx.date}-${tx.category}-${tx.amountUah}-${i}`}
                  className="border-b border-kesha-border transition-colors hover:bg-kesha-card-hover"
                >
                  <td className="py-2.5 pr-3 text-kesha-text-primary whitespace-nowrap">
                    {formatDate(tx.date)}
                  </td>
                  <td className="py-2.5 pr-3">
                    <Badge variant={tx.type}>
                      {tx.type === "income" ? "Доход" : "Расход"}
                    </Badge>
                  </td>
                  <td className="py-2.5 pr-3 text-kesha-text-primary whitespace-nowrap">
                    <span className="mr-1.5">
                      {getCategoryEmoji(tx.category)}
                    </span>
                    {tx.category}
                  </td>
                  <td
                    className={`py-2.5 pr-3 text-right font-medium tabular-nums whitespace-nowrap ${
                      tx.type === "income"
                        ? "text-kesha-income"
                        : "text-kesha-expense"
                    }`}
                  >
                    {tx.type === "income" ? "+" : "-"}
                    {amount.label}
                  </td>
                  <td className="py-2.5 text-kesha-text-secondary max-w-[200px] truncate">
                    {tx.comment || "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile list */}
      <div className="space-y-px md:hidden">
        {transactions.map((tx, i) => {
          const amount = getAmount(tx);
          return (
            <div
              key={`${tx.date}-${tx.category}-${tx.amountUah}-${i}`}
              className="flex items-center gap-3 py-3 border-b border-kesha-border last:border-0"
            >
              <span className="text-lg flex-shrink-0">
                {getCategoryEmoji(tx.category)}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-kesha-text-primary truncate">
                  {tx.category}
                </p>
                <p className="text-xs text-kesha-text-tertiary">
                  {formatDate(tx.date)}
                  {tx.comment ? ` · ${tx.comment}` : ""}
                </p>
              </div>
              <div className="flex flex-col items-end flex-shrink-0">
                <span
                  className={`text-sm font-semibold tabular-nums ${
                    tx.type === "income"
                      ? "text-kesha-income"
                      : "text-kesha-expense"
                  }`}
                >
                  {tx.type === "income" ? "+" : "-"}
                  {amount.label}
                </span>
                <Badge variant={tx.type} className="mt-1">
                  {tx.type === "income" ? "Доход" : "Расход"}
                </Badge>
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}
