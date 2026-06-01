import { NextResponse } from "next/server";
import { getClientInfo, currencyCodeToName, monoAmountToFloat } from "@/lib/mono";

export async function GET() {
  const token = process.env.MONOBANK_X_TOKEN;
  if (!token) {
    return NextResponse.json({ error: "Monobank token not configured" }, { status: 500 });
  }

  try {
    const { accounts } = await getClientInfo(token);
    const formatted = accounts.map((a) => ({
      id: a.id,
      balance: monoAmountToFloat(a.balance),
      creditLimit: monoAmountToFloat(a.creditLimit),
      currency: currencyCodeToName(a.currencyCode),
      maskedPan: a.maskedPan?.[0] ?? "***",
      type: a.type,
      iban: a.iban,
    }));
    return NextResponse.json(formatted);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
