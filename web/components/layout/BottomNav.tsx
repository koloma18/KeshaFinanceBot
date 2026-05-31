"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  {
    href: "/",
    label: "Dashboard",
    icon: "📊",
  },
  {
    href: "/transactions",
    label: "Транзакции",
    icon: "💳",
  },
  {
    href: "/analytics",
    label: "Аналитика",
    icon: "📈",
  },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-kesha-page border-t border-kesha-border pb-safe lg:hidden">
      <div className="mx-auto max-w-lg">
        <div className="flex items-center justify-around">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex flex-col items-center gap-0.5 py-2 px-4 min-w-[72px] transition-colors ${
                  isActive
                    ? "text-kesha-accent"
                    : "text-kesha-text-tertiary hover:text-kesha-text-secondary"
                }`}
              >
                <span className="text-xl" role="img" aria-label={item.label}>
                  {item.icon}
                </span>
                <span className="text-[10px] font-medium leading-tight">
                  {item.label}
                </span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
