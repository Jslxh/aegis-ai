import { cn } from "../../lib/utils";

export function Tabs({ value, children, className }) {
  return (
    <div className={cn("w-full", className)}>
      {children}
      <input type="hidden" value={value} readOnly aria-hidden />
    </div>
  );
}

export function TabsList({ items, value, onValueChange, className }) {
  return (
    <div
      className={cn(
        "inline-flex h-9 items-center justify-center rounded-lg bg-muted p-1 text-muted-foreground",
        className
      )}
    >
      {items.map((item) => (
        <button
          key={item.value}
          type="button"
          onClick={() => onValueChange(item.value)}
          className={cn(
            "inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none",
            value === item.value && "bg-background text-foreground shadow"
          )}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function TabsContent({ value, activeValue, children, className }) {
  if (value !== activeValue) return null;
  return <div className={cn("mt-2", className)}>{children}</div>;
}
