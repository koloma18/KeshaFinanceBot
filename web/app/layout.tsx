import type { Metadata, Viewport } from "next";
import { Header } from "@/components/layout/Header";
import { BottomNav } from "@/components/layout/BottomNav";
import { ThemeScript } from "@/components/ui/ThemeProvider";
import { ToastProvider } from "@/components/ui/Toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "Кеша — Финансовый трекер",
  description: "Персональный трекер доходов и расходов с характером",
  manifest: "/manifest.json",
  icons: {
    icon: "/favicon.svg",
    apple: "/icons/icon-192x192.svg",
  },
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Кеша",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#020617",
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: ThemeScript }} />
      </head>
      <body className="min-h-dvh bg-kesha-page text-kesha-text-primary antialiased">
        <ToastProvider>
          <Header />
          <main className="mx-auto max-w-lg md:max-w-2xl px-4 py-4 pb-20">
            {children}
          </main>
          <BottomNav />
        </ToastProvider>
      </body>
    </html>
  );
}
