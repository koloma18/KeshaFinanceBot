"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import type { FormattedRates } from "@/lib/mono";

interface RatesCardProps {
  rates: FormattedRates | null;
}

export function RatesCard({ rates }: RatesCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>💱 Курсы Monobank</CardTitle>
      </CardHeader>
      <CardContent>
        {!rates ? (
          <div className="flex items-center gap-2 text-sm text-kesha-text-tertiary">
            <span className="h-3 w-20 bg-kesha-border animate-pulse rounded" />
            <span className="h-3 w-20 bg-kesha-border animate-pulse rounded" />
          </div>
        ) : (
          <div className="flex flex-col sm:flex-row sm:justify-between gap-2 text-sm">
            <div>
              🇺🇸 USD{" "}
              <span className="text-kesha-text-tertiary">
                {rates.USD_UAH
                  ? `${rates.USD_UAH.buy.toFixed(2)} / ${rates.USD_UAH.sell.toFixed(2)}`
                  : "—"}
              </span>
            </div>
            <div>
              🇪🇺 EUR{" "}
              <span className="text-kesha-text-tertiary">
                {rates.EUR_UAH
                  ? `${rates.EUR_UAH.buy.toFixed(2)} / ${rates.EUR_UAH.sell.toFixed(2)}`
                  : "—"}
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
