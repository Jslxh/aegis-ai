import { forwardRef } from "react";
import { cn } from "../../lib/utils";

export const Table = forwardRef(function Table({ className, ...props }, ref) {
  return (
    <div className="relative w-full overflow-auto">
      <table ref={ref} className={cn("w-full caption-bottom text-sm", className)} {...props} />
    </div>
  );
});

export const TableHeader = forwardRef(function TableHeader({ className, ...props }, ref) {
  return <thead ref={ref} className={cn("[&_tr]:border-b", className)} {...props} />;
});

export const TableBody = forwardRef(function TableBody({ className, ...props }, ref) {
  return <tbody ref={ref} className={cn("[&_tr:last-child]:border-0", className)} {...props} />;
});

export const TableRow = forwardRef(function TableRow({ className, ...props }, ref) {
  return (
    <tr
      ref={ref}
      className={cn(
        "border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted",
        className
      )}
      {...props}
    />
  );
});

export const TableHead = forwardRef(function TableHead({ className, ...props }, ref) {
  return (
    <th
      ref={ref}
      className={cn(
        "h-10 px-3 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  );
});

export const TableCell = forwardRef(function TableCell({ className, ...props }, ref) {
  return (
    <td
      ref={ref}
      className={cn("p-3 align-middle [&:has([role=checkbox])]:pr-0", className)}
      {...props}
    />
  );
});
