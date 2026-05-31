export interface Transaction {
  month: string;
  date: string;
  type: "income" | "expense";
  amountUah: number | "";
  amountUsd: number | "";
  amountEur: number | "";
  category: string;
  comment: string;
  source: string;
}

export interface Balance {
  UAH: number;
  USD: number;
  EUR: number;
}

export interface BudgetStatus {
  budget: number;
  spent: number;
  remaining: number;
  percent: number;
  bar: string;
}

export interface DailyStats {
  income: number;
  expense: number;
  total: number;
}

export interface CategoryLimit {
  category: string;
  limit: number;
  spent: number;
  percent: number;
  bar: string;
}

export interface SheetRow {
  month: string;
  date: string;
  type: string;
  amountUah: string;
  amountUsd: string;
  amountEur: string;
  category: string;
  comment: string;
  source: string;
}

export interface SpendingByCategory {
  category: string;
  amount: number;
  percentage: number;
  currency: string;
}

export interface MonthlySummary {
  month: string;
  income: number;
  expense: number;
  balance: number;
}
