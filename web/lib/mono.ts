const MONOBANK_URL = "https://api.monobank.ua";

export interface MonoRate {
  currencyCodeA: number;
  currencyCodeB: number;
  date: number;
  rateBuy?: number;
  rateSell?: number;
  rateCross?: number;
}

export interface FormattedRates {
  USD_UAH: { buy: number; sell: number } | null;
  EUR_UAH: { buy: number; sell: number } | null;
  updated: number;
}

export interface MonoAccount {
  id: string;
  sendId: string;
  currencyCode: number;
  cashbackType: string;
  balance: number;
  creditLimit: number;
  maskedPan: string[];
  type: string;
  iban: string;
}

export interface MonoTransaction {
  id: string;
  time: number;
  description: string;
  mcc: number;
  originalMcc: number;
  hold: boolean;
  amount: number;
  operationAmount: number;
  currencyCode: number;
  commissionRate: number;
  cashbackAmount: number;
  balance: number;
  comment?: string;
  receiptId?: string;
  invoiceId?: string;
  counterEdrpou?: string;
  counterIban?: string;
}

export async function getCurrencyRates(): Promise<MonoRate[]> {
  const res = await fetch(`${MONOBANK_URL}/bank/currency`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`Monobank API: ${res.status}`);
  return res.json();
}

function resolveBuySell(
  rate: MonoRate | undefined,
): { buy: number; sell: number } | null {
  if (!rate) return null;
  const buy = rate.rateBuy ?? rate.rateCross;
  const sell = rate.rateSell ?? rate.rateCross;
  if (buy == null || sell == null) return null;
  return { buy, sell };
}

export function formatRates(rates: MonoRate[]): FormattedRates {
  const usd_uah = rates.find(
    (r) => r.currencyCodeA === 840 && r.currencyCodeB === 980,
  );
  const eur_uah = rates.find(
    (r) => r.currencyCodeA === 978 && r.currencyCodeB === 980,
  );

  return {
    USD_UAH: resolveBuySell(usd_uah),
    EUR_UAH: resolveBuySell(eur_uah),
    updated: Date.now(),
  };
}

export async function getClientInfo(
  token: string,
): Promise<{ accounts: MonoAccount[] }> {
  const res = await fetch(`${MONOBANK_URL}/personal/client-info`, {
    headers: { "X-Token": token },
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error(`Monobank client info: ${res.status}`);
  return res.json();
}

export async function getStatement(
  token: string,
  accountId: string,
  from: number,
  to: number,
): Promise<MonoTransaction[]> {
  const res = await fetch(
    `${MONOBANK_URL}/personal/statement/${accountId}/${from}/${to}`,
    {
      headers: { "X-Token": token },
      next: { revalidate: 0 },
    },
  );
  if (!res.ok) throw new Error(`Monobank statement: ${res.status}`);
  return res.json();
}

export function currencyCodeToName(code: number): string {
  switch (code) {
    case 980:
      return "UAH";
    case 840:
      return "USD";
    case 978:
      return "EUR";
    default:
      return `CC${code}`;
  }
}

export function monoAmountToFloat(amount: number): number {
  return amount / 100;
}
