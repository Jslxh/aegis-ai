import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";

export function ToolBarChart({ data, height = 260, colorKey = "block_rate_pct", labelKey = "tool" }) {
  const rows = (data || [])
    .map((d) => ({ name: d[labelKey] || "—", value: Number(d[colorKey] ?? 0) }))
    .slice(0, 10);

  if (rows.length === 0) {
    return (
      <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">
        No tool data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={90}
          tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          cursor={{ fill: "hsl(var(--muted)/0.4)" }}
          contentStyle={{
            borderRadius: 8,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--card))",
            color: "hsl(var(--foreground))",
          }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]}>
          {rows.map((_, index) => (
            <Cell key={index} fill={index < 3 ? "#dc2626" : "hsl(var(--primary))"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
