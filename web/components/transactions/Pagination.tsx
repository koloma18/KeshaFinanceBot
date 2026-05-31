"use client";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) return null;

  function range() {
    const pages: (number | "ellipsis")[] = [];
    const delta = 1;

    for (let i = 1; i <= totalPages; i++) {
      if (
        i === 1 ||
        i === totalPages ||
        (i >= currentPage - delta && i <= currentPage + delta)
      ) {
        pages.push(i);
      } else if (pages[pages.length - 1] !== "ellipsis") {
        pages.push("ellipsis");
      }
    }

    return pages;
  }

  return (
    <div className="flex items-center justify-center gap-1 pt-4">
      {/* Prev */}
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="flex h-9 w-9 items-center justify-center rounded-lg text-sm text-kesha-text-secondary transition-colors hover:bg-kesha-card-hover disabled:opacity-30 disabled:cursor-not-allowed"
      >
        ‹
      </button>

      {range().map((item, idx) =>
        item === "ellipsis" ? (
          <span
            key={`e-${idx}`}
            className="flex h-9 w-9 items-center justify-center text-xs text-kesha-text-tertiary"
          >
            …
          </span>
        ) : (
          <button
            key={item}
            onClick={() => onPageChange(item)}
            className={`flex h-9 w-9 items-center justify-center rounded-lg text-sm font-medium transition-colors ${
              item === currentPage
                ? "bg-kesha-accent-bg text-kesha-accent"
                : "text-kesha-text-secondary hover:bg-kesha-card-hover"
            }`}
          >
            {item}
          </button>
        ),
      )}

      {/* Next */}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="flex h-9 w-9 items-center justify-center rounded-lg text-sm text-kesha-text-secondary transition-colors hover:bg-kesha-card-hover disabled:opacity-30 disabled:cursor-not-allowed"
      >
        ›
      </button>
    </div>
  );
}
