import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

const COLORS = {
  allow: "#16a34a",
  block: "#dc2626",
  require_hitl: "#f59e0b",
  log_and_allow: "#6366f1",
  other: "#6b7280",
};

export function DecisionDonut({ data, height = 260 }) {
  const rows = (data || []).map((d) => ({
    name: d.decision || "unknown",
    value: d.count ?? d.value ?? 0,
    color: COLORS[d.decision] || COLORS.other,
  }));
  const total = rows.reduce((sum, r) => sum + r.value, 0);

  if (total === 0) {
    return (
      <div className="flex h-[260px] items-center justify-center text-sm text-muted-foreground">
        No decision data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={rows}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={2}
          strokeWidth={0}
        >
          {rows.map((entry, index) => (
            <Cell key={index} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value, name) => [
            `${value} (${total ? ((value / total) * 100).toFixed(1) : 0}%)`,
            name,
          ]}
          contentStyle={{
            borderRadius: 8,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--card))",
            color: "hsl(var(--foreground))",
          }}
        />
        <Legend
          formatter={(value) => <span className="text-xs text-muted-foreground">{value}</span>}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
