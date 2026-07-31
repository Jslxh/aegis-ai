import { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

export function Dialog({ open, onOpenChange, children }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") onOpenChange(false);
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <div
        className={cn(
          "relative z-10 w-full max-w-lg rounded-lg border bg-card text-card-foreground shadow-xl"
        )}
        role="dialog"
        aria-modal="true"
      >
        {children}
      </div>
    </div>
  );
}

export function DialogHeader({ children, className }) {
  return <div className={cn("flex flex-col space-y-1.5 p-6 pb-2", className)}>{children}</div>;
}

export function DialogTitle({ children, className }) {
  return <h2 className={cn("text-lg font-semibold leading-none tracking-tight", className)}>{children}</h2>;
}

export function DialogDescription({ children, className }) {
  return <p className={cn("text-sm text-muted-foreground", className)}>{children}</p>;
}

export function DialogContent({ children, className }) {
  return <div className={cn("p-6 pt-2", className)}>{children}</div>;
}

export function DialogFooter({ children, className }) {
  return (
    <div
      className={cn(
        "flex items-center justify-end gap-2 border-t p-4 sm:rounded-b-lg",
        className
      )}
    >
      {children}
    </div>
  );
}

export function DialogCloseButton({ onClose, className }) {
  return (
    <button
      type="button"
      onClick={onClose}
      className={cn(
        "absolute right-4 top-4 rounded-sm opacity-70 transition-opacity hover:opacity-100 focus:outline-none",
        className
      )}
      aria-label="Close"
    >
      <X className="h-4 w-4" />
    </button>
  );
}
