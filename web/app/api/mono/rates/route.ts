import { NextResponse } from 'next/server';
import { getCurrencyRates, formatRates } from '@/lib/mono';

export async function GET() {
  try {
    const rates = await getCurrencyRates();
    return NextResponse.json(formatRates(rates));
  } catch {
    return NextResponse.json({ error: 'Monobank unavailable' }, { status: 502 });
  }
}
