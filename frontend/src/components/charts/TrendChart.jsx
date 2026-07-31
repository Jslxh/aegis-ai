import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const SERIES_COLORS = {
  total: "hsl(var(--primary))",
  blocked: "#dc2626",
  allowed: "#16a34a",
  failed: "#f59e0b",
};

export function TrendChart({ data, height = 280, series = ["total", "blocked", "allowed", "failed"] }) {
  const rows = (data || []).map((point) => ({
    label: point.timestamp || point.bucket || point.label || "",
    total: point.total ?? 0,
    blocked: point.blocked ?? 0,
    allowed: point.allowed ?? 0,
    failed: point.failed ?? 0,
  }));

  if (rows.length === 0) {
    return (
      <div className="flex h-[280px] items-center justify-center text-sm text-muted-foreground">
        No timeline data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={rows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          {Object.entries(SERIES_COLORS).map(([key, color]) => (
            <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={{ stroke: "hsl(var(--border))" }}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
        />
        <Tooltip
          contentStyle={{
            borderRadius: 8,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--card))",
            color: "hsl(var(--foreground))",
          }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {series.map((key) => (
          <Area
            key={key}
            type="monotone"
            dataKey={key}
            stroke={SERIES_COLORS[key]}
            fill={`url(#grad-${key})`}
            strokeWidth={2}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
