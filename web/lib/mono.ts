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
