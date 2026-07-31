import { cn } from "../../lib/utils";

export function Alert({ variant = "default", className, ...props }) {
  return (
    <div
      role="alert"
      className={cn(
        "relative w-full rounded-lg border p-4 text-sm [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg]:h-4 [&>svg]:w-4",
        variant === "destructive" &&
          "border-destructive/50 text-destructive [&>svg]:text-destructive",
        variant === "warning" && "border-warning/50 text-warning",
        variant === "success" && "border-success/50 text-success",
        variant === "info" && "border-primary/50 text-primary",
        className
      )}
      {...props}
    />
  );
}

export function AlertTitle({ className, ...props }) {
  return <h5 className={cn("mb-1 font-medium leading-none tracking-tight", className)} {...props} />;
}

export function AlertDescription({ className, ...props }) {
  return <div className={cn("text-sm opacity-90", className)} {...props} />;
}
