"use client";

import { ReactNode } from "react";

interface EmptyStateProps {
  icon?: string;
  title?: string;
  description?: string;
  action?: ReactNode;
  className?: string;
  variant?: "dashboard" | "transactions" | "analytics" | "default";
}

const PRESETS: Record<
  NonNullable<EmptyStateProps["variant"]>,
  { icon: string; title: string; description: string }
> = {
  dashboard: {
    icon: "🐹",
    title: "",
    description: "Ни одной транзакции. Кеша живёт интуитивно.",
  },
  transactions: {
    icon: "🔍",
    title: "",
    description: "Транзакции не найдены. Попробуй изменить фильтры.",
  },
  analytics: {
    icon: "📊",
    title: "",
    description:
      "Недостаточно данных для аналитики. Добавь хотя бы 5 транзакций.",
  },
  default: {
    icon: "📭",
    title: "Ничего нет",
    description: "Здесь пока пусто.",
  },
};

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = "",
  variant = "default",
}: EmptyStateProps) {
  const preset = PRESETS[variant];
  const resolvedIcon = icon || preset.icon;
  const resolvedTitle = title ?? preset.title;
  const resolvedDescription = description ?? preset.description;

  return (
    <div
      className={`flex flex-col items-center justify-center text-center py-12 px-4 ${className}`}
    >
      <span className="text-4xl mb-4 block">{resolvedIcon}</span>
      {resolvedTitle && (
        <h3 className="text-lg font-semibold text-kesha-text-primary mb-1">
          {resolvedTitle}
        </h3>
      )}
      {resolvedDescription && (
        <p className="text-sm text-kesha-text-secondary max-w-xs">
          {resolvedDescription}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
