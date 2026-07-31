import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, Ban, CheckCircle2, LoaderCircle } from "lucide-react";
import { api } from "../lib/api";
import { formatDate, formatDuration } from "../lib/utils";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { StatCard } from "../components/shared/StatCard.jsx";
import { EmptyState } from "../components/shared/EmptyState.jsx";
import { CardSkeleton } from "../components/shared/LoadingSkeleton.jsx";
import { JsonView } from "../components/shared/JsonView.jsx";
import { TrendChart } from "../components/charts/TrendChart.jsx";
import { StatusBadge, RiskBadge, DecisionBadge } from "../components/shared/StatusBadge.jsx";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Select } from "../components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogCloseButton } from "../components/ui/dialog";

const RANGES = [
  { value: "1h", label: "Last hour" },
  { value: "24h", label: "Last 24 hours" },
  { value: "7d", label: "Last 7 days" },
  { value: "30d", label: "Last 30 days" },
  { value: "all", label: "All time" },
];

export default function RuntimeMonitor() {
  const [range, setRange] = useState("24h");
  const [decisionFilter, setDecisionFilter] = useState("");
  const [selected, setSelected] = useState(null);

  const metrics = useQuery({
    queryKey: ["metrics", range],
    queryFn: async () => (await api.get(`/monitoring/metrics?time_range=${range}`)).data,
  });

  const timeline = useQuery({
    queryKey: ["metrics", "timeline", range],
    queryFn: async () => (await api.get(`/monitoring/metrics/timeline?time_range=${range}&granularity=hour`)).data,
  });

  const activity = useQuery({
    queryKey: ["activity", range],
    queryFn: async () => (await api.get(`/monitoring/activity?limit=200&time_range=${range}`)).data,
  });

  const filtered = useMemo(
    () => (activity.data || []).filter((a) => !decisionFilter || a.decision === decisionFilter),
    [activity.data, decisionFilter]
  );

  if (metrics.isLoading || timeline.isLoading || activity.isLoading) {
    return <div className="space-y-6"><PageHeader title="Runtime Monitor" description="Live execution and enforcement telemetry" icon={Activity} /><CardSkeleton rows={8} /></div>;
  }

  const m = metrics.data || {};

  return (
    <div className="space-y-6">
      <PageHeader
        title="Runtime Monitor"
        description="Live execution and enforcement telemetry"
        icon={Activity}
        actions={
          <Select value={range} onChange={(e) => setRange(e.target.value)} className="w-44">
            {RANGES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </Select>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Total Requests" value={m.total_requests ?? 0} icon={Activity} accent="primary" />
        <StatCard title="Blocked" value={m.blocked_count ?? 0} icon={Ban} accent="danger" />
        <StatCard title="Success" value={m.success_count ?? 0} icon={CheckCircle2} accent="success" />
        <StatCard
          title="Avg Execution Time"
          value={formatDuration(m.avg_execution_time_ms)}
          icon={LoaderCircle}
          accent="warning"
          subtitle={m.avg_tool_latency_ms ? `tool latency ${formatDuration(m.avg_tool_latency_ms)}` : undefined}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Execution Timeline</CardTitle>
          <CardDescription>Total, blocked, allowed and failed requests</CardDescription>
        </CardHeader>
        <CardContent>
          <TrendChart data={timeline.data?.points} />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="flex items-center justify-between gap-3 border-b p-4">
            <div>
              <p className="text-sm font-semibold">Recent activity</p>
              <p className="text-xs text-muted-foreground">{filtered.length} records</p>
            </div>
            <Select value={decisionFilter} onChange={(e) => setDecisionFilter(e.target.value)} className="w-44">
              <option value="">All decisions</option>
              <option value="allow">allow</option>
              <option value="block">block</option>
              <option value="require_hitl">require_hitl</option>
              <option value="log_and_allow">log_and_allow</option>
            </Select>
          </div>
          {filtered.length === 0 ? (
            <div className="p-6"><EmptyState title="No activity" description="Execute actions to populate runtime telemetry." /></div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Tool / Action</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Matched Rule</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.slice(0, 100).map((item) => (
                  <TableRow key={item.id} onClick={() => setSelected(item)} className="cursor-pointer">
                    <TableCell><span className="text-xs text-muted-foreground">{formatDate(item.timestamp)}</span></TableCell>
                    <TableCell>
                      <span className="font-mono text-xs">{item.tool}</span>
                      <span className="text-muted-foreground"> / </span>
                      <span className="font-mono text-xs">{item.action}</span>
                    </TableCell>
                    <TableCell><DecisionBadge decision={item.decision} /></TableCell>
                    <TableCell><span className="font-mono text-xs">{item.matched_rule || "—"}</span></TableCell>
                    <TableCell><StatusBadge status={item.execution_status} /></TableCell>
                    <TableCell><RiskBadge risk={item.risk_level} /></TableCell>
                    <TableCell><span className="text-xs">{formatDuration(item.execution_time_ms)}</span></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={Boolean(selected)} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogCloseButton onClose={() => setSelected(null)} />
        <DialogHeader>
          <DialogTitle>Execution detail</DialogTitle>
        </DialogHeader>
        <DialogContent className="space-y-4">
          {selected && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{selected.tool} / {selected.action}</Badge>
                <DecisionBadge decision={selected.decision} />
                <StatusBadge status={selected.execution_status} />
                <RiskBadge risk={selected.risk_level} />
              </div>
              {selected.matched_rule && (
                <p className="text-sm"><span className="text-muted-foreground">Matched rule:</span> <span className="font-mono text-xs">{selected.matched_rule}</span></p>
              )}
              {selected.reason && <p className="text-sm text-muted-foreground">{selected.reason}</p>}
              <div className="grid gap-2 text-xs text-muted-foreground sm:grid-cols-2">
                <span>Execution time: {formatDuration(selected.execution_time_ms)}</span>
                {selected.tool_latency_ms != null && <span>Tool latency: {formatDuration(selected.tool_latency_ms)}</span>}
              </div>
              {selected.request_data && (
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Request</p>
                  <JsonView data={selected.request_data} />
                </div>
              )}
              {selected.tool_output && (
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Tool output</p>
                  <JsonView data={selected.tool_output} />
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
