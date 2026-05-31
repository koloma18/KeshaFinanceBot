"use client";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "income" | "expense" | "warning";
  className?: string;
}

const variantStyles = {
  income: "bg-kesha-income-bg text-kesha-income border-kesha-income-border",
  expense: "bg-kesha-expense-bg text-kesha-expense border-kesha-expense-border",
  warning: "bg-kesha-accent-bg text-kesha-accent border-kesha-accent-border",
};

export function Badge({
  children,
  variant = "warning",
  className = "",
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
