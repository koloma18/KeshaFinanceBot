import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    status: "ok",
    timestamp: Date.now(),
    env: {
      hasSheets: Boolean(process.env.SPREADSHEET_ID),
      hasGoogleEmail: Boolean(process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL),
      hasGoogleKey: Boolean(process.env.GOOGLE_PRIVATE_KEY),
      hasMono: Boolean(process.env.MONOBANK_X_TOKEN),
    },
  });
}
