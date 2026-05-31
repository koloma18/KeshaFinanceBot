"use client";

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = "" }: SkeletonProps) {
  return (
    <div className={`bg-kesha-border animate-pulse rounded ${className}`} />
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-kesha-card rounded-xl border border-kesha-border p-4 space-y-3">
      <Skeleton className="h-4 w-2/5" />
      <Skeleton className="h-8 w-3/5" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-4/5" />
    </div>
  );
}

export function SkeletonList({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-full shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/5" />
            <Skeleton className="h-3 w-2/5" />
          </div>
          <Skeleton className="h-4 w-16" />
        </div>
      ))}
    </div>
  );
}

/** @deprecated Use SkeletonCard. Kept for backward compat */
export function CardSkeleton() {
  return <SkeletonCard />;
}

export function RowSkeleton() {
  return (
    <div className="flex items-center gap-3 py-3">
      <Skeleton className="h-8 w-8 rounded-full" />
      <div className="flex-1 space-y-1.5">
        <Skeleton className="h-3.5 w-28" />
        <Skeleton className="h-3 w-20" />
      </div>
      <Skeleton className="h-4 w-16" />
    </div>
  );
}

export function BalanceSkeleton() {
  return (
    <div className="bg-kesha-card rounded-xl border border-kesha-border p-5 space-y-3">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="h-10 w-40" />
      <Skeleton className="h-3 w-56" />
    </div>
  );
}
