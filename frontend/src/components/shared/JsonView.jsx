import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "../../lib/utils";

function JsonValue({ value, depth }) {
  const [open, setOpen] = useState(true);

  if (value === null || value === undefined) {
    return <span className="text-muted-foreground">null</span>;
  }
  if (typeof value === "boolean") {
    return <span className="text-warning">{String(value)}</span>;
  }
  if (typeof value === "number") {
    return <span className="text-primary">{value}</span>;
  }
  if (typeof value === "string") {
    return <span className="text-success">"{value}"</span>;
  }
  if (Array.isArray(value) || typeof value === "object") {
    const isArray = Array.isArray(value);
    const entries = Object.entries(value);
    const preview = isArray ? `Array(${entries.length})` : "Object";
    if (entries.length === 0) return <span className="text-muted-foreground">{isArray ? "[]" : "{}"}</span>;
    return (
      <div className="ml-2">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="inline-flex items-center gap-1 font-mono text-xs text-muted-foreground hover:text-foreground"
        >
          {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
          {preview}
        </button>
        {open && (
          <div className="border-l border-muted pl-3">
            {entries.map(([key, val]) => (
              <div key={key} className="py-0.5">
                <span className="font-mono text-xs text-muted-foreground">{key}:</span>{" "}
                <span className="font-mono text-xs">
                  <JsonValue value={val} depth={depth + 1} />
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }
  return <span>{String(value)}</span>;
}

export function JsonView({ data, className }) {
  return (
    <div className={cn("overflow-x-auto rounded-md bg-muted/40 p-3", className)}>
      <JsonValue value={data} depth={0} />
    </div>
  );
}
