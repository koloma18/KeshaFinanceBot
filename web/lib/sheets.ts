import "server-only";

import { google, sheets_v4 } from "googleapis";
import { JWT } from "google-auth-library";
import { Transaction, Balance, AccountBalance } from "./types";

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
  ACCOUNT_ID: 9,
  ACCOUNT_NAME: 10,
  TRANSFER_ID: 11,
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
        range: "Transactions!A:L",
        valueRenderOption: "UNFORMATTED_VALUE",
      });

      const values = result.data.values as string[][] | undefined;
      if (!values || values.length <= 1) return [];

      return values.slice(1).map((row) => this.rowToTransaction(row));
    } catch (error) {
      console.error("[SheetsClient] Failed to fetch transactions:", error);
      return [];
    }
  }

  /**
   * Calculate balance per currency.
   *
   * Expense amounts in the sheet are NEGATIVE (both manual via bot and Monobank).
   * Income amounts are always POSITIVE.
   * We use abs() to avoid double negation: expense type already carries intent.
   */
  async getBalance(): Promise<Balance> {
    const transactions = await this.getTransactions();

    const balance: Balance = { UAH: 0, USD: 0, EUR: 0 };

    for (const t of transactions) {
      if (t.type !== "income" && t.type !== "expense") continue;

      const sign = t.type === "income" ? 1 : -1;

      if (t.amountUah !== "") balance.UAH += sign * Math.abs(t.amountUah);
      if (t.amountUsd !== "") balance.USD += sign * Math.abs(t.amountUsd);
      if (t.amountEur !== "") balance.EUR += sign * Math.abs(t.amountEur);
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

    const parts = month.split("-");
    const monthName = monthNames[parts[1]] || "";

    const spending: Record<string, number> = {};

    for (const t of transactions) {
      if (t.type !== "expense") continue;
      if (t.month !== monthName) continue;

      const amount = t.amountUah !== "" ? Math.abs(t.amountUah) : 0;
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

    const rawType = String(row[COL.TYPE] || "")
      .toLowerCase()
      .trim();
    const txType: "income" | "expense" =
      rawType === "income"
        ? "income"
        : rawType === "expense"
          ? "expense"
          : "expense";

    return {
      month: String(row[COL.MONTH] || ""),
      date: String(row[COL.DATE] || ""),
      type: txType,
      amountUah: rawUah !== undefined && rawUah !== "" ? Number(rawUah) : "",
      amountUsd: rawUsd !== undefined && rawUsd !== "" ? Number(rawUsd) : "",
      amountEur: rawEur !== undefined && rawEur !== "" ? Number(rawEur) : "",
      category: String(row[COL.CATEGORY] || ""),
      comment: String(row[COL.COMMENT] || ""),
      source: String(row[COL.SOURCE] || ""),
      accountId:
        row.length > COL.ACCOUNT_ID ? String(row[COL.ACCOUNT_ID] || "") : "",
      accountName:
        row.length > COL.ACCOUNT_NAME
          ? String(row[COL.ACCOUNT_NAME] || "")
          : "",
      transferId:
        row.length > COL.TRANSFER_ID ? String(row[COL.TRANSFER_ID] || "") : "",
    };
  }

  async getAccountBalances(): Promise<AccountBalance[]> {
    const sheets = this.getSheets();
    if (!sheets) return [];

    try {
      const [accountsResult, txResult] = await Promise.all([
        sheets.spreadsheets.values.get({
          spreadsheetId: this.spreadsheetId,
          range: "Accounts!A:I",
          valueRenderOption: "UNFORMATTED_VALUE",
        }),
        sheets.spreadsheets.values.get({
          spreadsheetId: this.spreadsheetId,
          range: "Transactions!A:L",
          valueRenderOption: "UNFORMATTED_VALUE",
        }),
      ]);

      const accountRows =
        (accountsResult.data.values as string[][] | undefined)?.slice(1) ?? [];
      const txRows =
        (txResult.data.values as string[][] | undefined)?.slice(1) ?? [];

      const accountMap: Record<string, AccountBalance> = {};
      const idToName: Record<string, string> = {};

      for (const row of accountRows) {
        if (!row || !row[1]) continue;
        const name = String(row[1]).trim();
        const active =
          !row[6] || String(row[6]).trim().toLowerCase() !== "false";
        if (!active) continue;
        const id = String(row[0] || "").trim();
        if (id) idToName[id] = name;
        accountMap[name] = {
          name,
          currency: String(row[3] || "UAH")
            .trim()
            .toUpperCase(),
          startingBalance: Number(row[4]) || 0,
          income: 0,
          expense: 0,
          balance: Number(row[4]) || 0,
          transactionCount: 0,
          active: true,
        };
      }

      accountMap["Без счета"] = {
        name: "Без счета",
        currency: "UAH",
        startingBalance: 0,
        income: 0,
        expense: 0,
        balance: 0,
        transactionCount: 0,
        active: true,
      };

      for (const row of txRows) {
        if (row.length <= COL.TYPE) continue;
        const type = String(row[COL.TYPE] || "")
          .trim()
          .toLowerCase();
        if (type !== "income" && type !== "expense") continue;

        const amountUah = Number(row[COL.AMOUNT_UAH]) || 0;

        let accountName = "";
        if (row.length > COL.ACCOUNT_NAME && row[COL.ACCOUNT_NAME]) {
          accountName = String(row[COL.ACCOUNT_NAME]).trim();
        } else if (row.length > COL.ACCOUNT_ID && row[COL.ACCOUNT_ID]) {
          const accId = String(row[COL.ACCOUNT_ID]).trim();
          accountName = idToName[accId] || "";
        }

        const entry =
          accountName && accountMap[accountName]
            ? accountMap[accountName]
            : accountMap["Без счета"];

        entry.transactionCount++;
        const absAmount = Math.abs(amountUah);
        if (type === "income") {
          entry.income += absAmount;
          entry.balance += absAmount;
        } else {
          entry.expense += absAmount;
          entry.balance -= absAmount;
        }
      }

      return Object.values(accountMap).filter(
        (a) => a.transactionCount > 0 || a.name !== "Без счета",
      );
    } catch (error) {
      console.error("[SheetsClient] Failed to fetch account balances:", error);
      return [];
    }
  }
}

export const sheetsClient = new SheetsClient();
