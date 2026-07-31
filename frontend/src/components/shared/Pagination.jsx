import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "../ui/button";

function pageWindow(current, pages, width = 2) {
  if (pages <= 1) return [1];
  const start = Math.max(1, current - width);
  const end = Math.min(pages, current + width);
  const pagesArr = [];
  for (let p = start; p <= end; p += 1) pagesArr.push(p);
  return pagesArr;
}

export function Pagination({ page, pages, total, onChange, loading }) {
  if (pages <= 1 && !loading) return null;
  const window = pageWindow(page, pages);
  return (
    <div className="flex items-center justify-between gap-3 pt-4">
      <p className="text-xs text-muted-foreground">
        {total} total · page {page} of {Math.max(pages, 1)}
      </p>
      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon"
          disabled={page <= 1 || loading}
          onClick={() => onChange(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft />
        </Button>
        {window.map((p) => (
          <Button
            key={p}
            variant={p === page ? "default" : "outline"}
            size="icon"
            className="h-8 w-8"
            disabled={loading}
            onClick={() => onChange(p)}
          >
            {p}
          </Button>
        ))}
        <Button
          variant="outline"
          size="icon"
          disabled={page >= pages || loading}
          onClick={() => onChange(page + 1)}
          aria-label="Next page"
        >
          <ChevronRight />
        </Button>
      </div>
    </div>
  );
}
