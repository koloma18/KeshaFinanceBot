const monthNamesRu = [
  "январь",
  "февраль",
  "март",
  "апрель",
  "май",
  "июнь",
  "июль",
  "август",
  "сентябрь",
  "октябрь",
  "ноябрь",
  "декабрь",
];

const monthNamesRuGenitive: Record<string, string> = {
  январь: "января",
  февраль: "февраля",
  март: "марта",
  апрель: "апреля",
  май: "мая",
  июнь: "июня",
  июль: "июля",
  август: "августа",
  сентябрь: "сентября",
  октябрь: "октября",
  ноябрь: "ноября",
  декабрь: "декабря",
};

export function formatCurrency(
  amount: number,
  currency: string = "UAH",
): string {
  const symbols: Record<string, string> = {
    UAH: "₴",
    USD: "$",
    EUR: "€",
  };

  const formatted = Math.abs(amount).toLocaleString("uk-UA", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

  const sign = amount < 0 ? "-" : "";

  return `${sign}${formatted} ${symbols[currency] || currency}`;
}

export function formatDate(dateStr: string): string {
  // "01.06.2026" -> "1 июня"
  const parts = dateStr.split(".");
  if (parts.length !== 3) return dateStr;

  const day = parseInt(parts[0], 10);
  const monthIndex = parseInt(parts[1], 10) - 1;

  if (monthIndex < 0 || monthIndex > 11) return dateStr;

  const monthName = monthNamesRu[monthIndex];
  const monthGenitive = monthNamesRuGenitive[monthName] || monthName;

  return `${day} ${monthGenitive}`;
}

export function formatMonth(monthStr: string): string {
  // "June" -> "июнь"
  const monthMap: Record<string, string> = {
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

  return monthMap[monthStr] || monthStr;
}

export function getMonthName(monthIndex: number): string {
  if (monthIndex < 0 || monthIndex > 11) return "";
  return monthNamesRu[monthIndex];
}

export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}

export function formatAmount(amount: number): string {
  return amount.toLocaleString("uk-UA", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatAmountInt(amount: number): string {
  return amount.toLocaleString("uk-UA", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}
