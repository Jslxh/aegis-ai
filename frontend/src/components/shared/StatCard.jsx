import { motion } from "framer-motion";
import { Card, CardContent } from "../ui/card";
import { cn } from "../../lib/utils";

export function StatCard({
  title,
  value,
  icon: Icon,
  subtitle,
  trend,
  accent = "primary",
  loading,
}) {
  const accentClasses = {
    primary: "text-primary bg-primary/10",
    success: "text-success bg-success/10",
    warning: "text-warning bg-warning/10",
    danger: "text-danger bg-danger/10",
    muted: "text-muted-foreground bg-muted",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
    >
      <Card>
        <CardContent className="p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <p className="text-sm font-medium text-muted-foreground">{title}</p>
              {loading ? (
                <div className="h-7 w-20 animate-pulse rounded bg-muted" />
              ) : (
                <p className="truncate text-2xl font-semibold tracking-tight">{value}</p>
              )}
              {subtitle && <p className="truncate text-xs text-muted-foreground">{subtitle}</p>}
              {trend !== undefined && (
                <p
                  className={cn(
                    "text-xs font-medium",
                    trend > 0 ? "text-success" : trend < 0 ? "text-danger" : "text-muted-foreground"
                  )}
                >
                  {trend > 0 ? "▲" : trend < 0 ? "▼" : "—"} {Math.abs(trend).toFixed(1)}%
                </p>
              )}
            </div>
            {Icon && (
              <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg", accentClasses[accent])}>
                <Icon className="h-4.5 w-4.5" />
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
