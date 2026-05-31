import "server-only";

import { google, sheets_v4 } from "googleapis";
import { JWT } from "google-auth-library";
import { Transaction, Balance, SheetRow } from "./types";

const SCOPES = ["https://www.googleapis.com/auth/spreadsheets"];

const COL = {
  MONTH: 0,
  DATE: 1,
  TYPE: 2,
  AMOUNT_UAH: 3,
  AMOUNT_USD: 4,
  AMOUNT_EUR: 5,
  CATEGORY: 6,
  COMMENT: 7,
  SOURCE: 8,
} as const;

export class SheetsClient {
  private sheets: sheets_v4.Sheets | null = null;

  private getAuth(): JWT | null {
    const email = process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL;
    const key = process.env.GOOGLE_PRIVATE_KEY;
    const spreadsheetId = process.env.SPREADSHEET_ID;

    if (!email || !key || !spreadsheetId) {
      console.warn("[SheetsClient] Missing Google Sheets credentials");
      return null;
    }

    return new JWT({
      email,
      key: key.replace(/\\n/g, "\n"),
      scopes: SCOPES,
    });
  }

  private getSheets(): sheets_v4.Sheets | null {
    if (this.sheets) return this.sheets;

    const auth = this.getAuth();
    if (!auth) return null;

    this.sheets = google.sheets({ version: "v4", auth });
    return this.sheets;
  }

  private get spreadsheetId(): string {
    return process.env.SPREADSHEET_ID || "";
  }

  async getTransactions(): Promise<Transaction[]> {
    const sheets = this.getSheets();
    if (!sheets) return [];

    try {
      const result = await sheets.spreadsheets.values.get({
        spreadsheetId: this.spreadsheetId,
        range: "Transactions!A:I",
        valueRenderOption: "UNFORMATTED_VALUE",
      });

      const values = result.data.values as string[][] | undefined;
      if (!values || values.length <= 1) return [];

      // Skip header row (index 0)
      return values.slice(1).map((row) => this.rowToTransaction(row));
    } catch (error) {
      console.error("[SheetsClient] Failed to fetch transactions:", error);
      return [];
    }
  }

  async getBalance(): Promise<Balance> {
    const transactions = await this.getTransactions();

    const balance: Balance = { UAH: 0, USD: 0, EUR: 0 };

    for (const t of transactions) {
      const sign = t.type === "income" ? 1 : -1;

      if (t.amountUah !== "") balance.UAH += sign * t.amountUah;
      if (t.amountUsd !== "") balance.USD += sign * t.amountUsd;
      if (t.amountEur !== "") balance.EUR += sign * t.amountEur;
    }

    return balance;
  }

  async getCategoriesSpending(month: string): Promise<Record<string, number>> {
    const transactions = await this.getTransactions();

    const monthNames: Record<string, string> = {
      "01": "January",
      "02": "February",
      "03": "March",
      "04": "April",
      "05": "May",
      "06": "June",
      "07": "July",
      "08": "August",
      "09": "September",
      "10": "October",
      "11": "November",
      "12": "December",
    };

    // Convert "2026-06" to month name
    const parts = month.split("-");
    const monthName = monthNames[parts[1]] || "";

    const spending: Record<string, number> = {};

    for (const t of transactions) {
      if (t.type !== "expense") continue;
      if (t.month !== monthName) continue;

      const amount = t.amountUah !== "" ? t.amountUah : 0;
      spending[t.category] = (spending[t.category] || 0) + amount;
    }

    return spending;
  }

  async getBudgetRows(): Promise<
    Array<{ month: string; category: string; limit: number; type: string }>
  > {
    const sheets = this.getSheets();
    if (!sheets) return [];

    try {
      const result = await sheets.spreadsheets.values.get({
        spreadsheetId: this.spreadsheetId,
        range: "Budgets!A:D",
        valueRenderOption: "UNFORMATTED_VALUE",
      });

      const values = result.data.values as string[][] | undefined;
      if (!values || values.length <= 1) return [];

      return values.slice(1).map((row) => ({
        month: String(row[0] || ""),
        category: String(row[1] || ""),
        limit: Number(row[2]) || 0,
        type: String(row[3] || ""),
      }));
    } catch (err) {
      console.error("[SheetsClient] Failed to fetch budget rows:", err);
      return [];
    }
  }

  private rowToTransaction(row: string[]): Transaction {
    const rawUah = row[COL.AMOUNT_UAH];
    const rawUsd = row[COL.AMOUNT_USD];
    const rawEur = row[COL.AMOUNT_EUR];

    return {
      month: String(row[COL.MONTH] || ""),
      date: String(row[COL.DATE] || ""),
      type:
        String(row[COL.TYPE] || "").toLowerCase() === "income"
          ? "income"
          : "expense",
      amountUah: rawUah !== undefined && rawUah !== "" ? Number(rawUah) : "",
      amountUsd: rawUsd !== undefined && rawUsd !== "" ? Number(rawUsd) : "",
      amountEur: rawEur !== undefined && rawEur !== "" ? Number(rawEur) : "",
      category: String(row[COL.CATEGORY] || ""),
      comment: String(row[COL.COMMENT] || ""),
      source: String(row[COL.SOURCE] || ""),
    };
  }
}

export const sheetsClient = new SheetsClient();
