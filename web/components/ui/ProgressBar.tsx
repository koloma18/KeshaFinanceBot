"use client";

interface ProgressBarProps {
  percent: number;
  color?: "yellow" | "red";
  className?: string;
}

const colorStyles = {
  yellow: "bg-kesha-accent",
  red: "bg-kesha-expense",
};

export function ProgressBar({
  percent,
  color = "yellow",
  className = "",
}: ProgressBarProps) {
  const clampedPercent = Math.min(Math.max(percent, 0), 100);

  return (
    <div
      className={`w-full bg-kesha-border rounded-full h-2.5 overflow-hidden ${className}`}
    >
      <div
        className={`h-full rounded-full transition-all duration-700 ease-out ${
          colorStyles[color]
        } ${clampedPercent >= 100 ? "animate-progress-fill" : ""}`}
        style={{ width: `${clampedPercent}%` }}
      />
    </div>
  );
}
