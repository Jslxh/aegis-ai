import { useQuery } from "@tanstack/react-query";
import { BarChart3, FileDown } from "lucide-react";
import { api } from "../lib/api";
import { formatDate, formatDuration } from "../lib/utils";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { CardSkeleton } from "../components/shared/LoadingSkeleton.jsx";
import { EmptyState } from "../components/shared/EmptyState.jsx";
import { ToolBarChart } from "../components/charts/ToolBarChart.jsx";
import { DecisionDonut } from "../components/charts/DecisionDonut.jsx";
import { TrendChart } from "../components/charts/TrendChart.jsx";
import { formatPercent } from "../lib/utils";

export default function Analytics() {
  const effectiveness = useQuery({
    queryKey: ["analytics", "effectiveness"],
    queryFn: async () => (await api.get("/analytics/policy-effectiveness")).data,
  });
  const triggered = useQuery({
    queryKey: ["analytics", "triggered"],
    queryFn: async () => (await api.get("/analytics/most-triggered-rules")).data,
  });
  const dangerous = useQuery({
    queryKey: ["analytics", "dangerous"],
    queryFn: async () => (await api.get("/analytics/most-dangerous-tools")).data,
  });
  const blocked = useQuery({
    queryKey: ["analytics", "blocked"],
    queryFn: async () => (await api.get("/analytics/blocked-requests")).data,
  });
  const hitl = useQuery({
    queryKey: ["analytics", "hitl"],
    queryFn: async () => (await api.get("/analytics/hitl-statistics")).data,
  });
  const latency = useQuery({
    queryKey: ["analytics", "latency"],
    queryFn: async () => (await api.get("/analytics/avg-response-time")).data,
  });
  const risk = useQuery({
    queryKey: ["analytics", "risk"],
    queryFn: async () => (await api.get("/analytics/risk-distribution")).data,
  });
  const reports = useQuery({
    queryKey: ["analytics", "reports"],
    queryFn: async () => (await api.get("/analytics/reports")).data,
  });

  const loading = effectiveness.isLoading || triggered.isLoading || dangerous.isLoading;

  if (loading) {
    return <div className="space-y-6"><PageHeader title="Analytics" description="Policy effectiveness and runtime trends" icon={BarChart3} /><CardSkeleton rows={8} /></div>;
  }

  const latencyData = latency.data || {};
  const blockedData = blocked.data || {};
  const riskItems = risk.data?.items || [];
  const riskDonut = riskItems.map((r) => ({ decision: r.risk_level, count: r.count }));

  async function generateReport(reportType) {
    await api.post(`/analytics/reports/${reportType}`);
    reports.refetch();
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analytics"
        description="Policy effectiveness, risk distribution and execution trends"
        icon={BarChart3}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={() => generateReport("daily")}>
              <FileDown /> Daily report
            </Button>
            <Button variant="outline" size="sm" onClick={() => generateReport("monthly")}>
              <FileDown /> Monthly report
            </Button>
          </>
        }
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Policy Effectiveness</CardTitle>
            <CardDescription>Block rate per enforcement rule</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {effectiveness.data?.items?.length === 0 ? (
              <EmptyState title="No rule activity" />
            ) : (
              (effectiveness.data?.items || []).map((item) => (
                <div key={item.rule_id} className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-mono text-xs font-medium">{item.rule_id}</p>
                    <p className="text-xs text-muted-foreground">
                      {item.total_matches} matches · {item.blocked_count} blocked · {item.allowed_count} allowed · {item.hitl_count} hitl
                    </p>
                  </div>
                  <Badge variant={item.effectiveness_pct > 50 ? "danger" : "outline"}>
                    {formatPercent(item.effectiveness_pct)} blocked
                  </Badge>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Most Triggered Rules</CardTitle>
            <CardDescription>Rules that fire most often</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {triggered.data?.items?.length === 0 ? (
              <EmptyState title="No triggers" />
            ) : (
              (triggered.data?.items || []).slice(0, 8).map((item, i) => (
                <div key={item.rule_id} className="flex items-center gap-3">
                  <Badge variant="outline" className="w-7 justify-center">{i + 1}</Badge>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate font-mono text-xs">{item.rule_id}</p>
                      <span className="text-xs text-muted-foreground">{item.trigger_count}</span>
                    </div>
                    <div className="mt-1 h-1.5 w-full rounded-full bg-muted">
                      <div
                        className="h-1.5 rounded-full bg-primary"
                        style={{ width: `${Math.min(100, (item.trigger_count / (triggered.data?.items?.[0]?.trigger_count || 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Most Dangerous Tools</CardTitle>
            <CardDescription>Block rate by tool</CardDescription>
          </CardHeader>
          <CardContent>
            <ToolBarChart data={dangerous.data?.items} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Risk Distribution</CardTitle>
            <CardDescription>Executions by risk level</CardDescription>
          </CardHeader>
          <CardContent>
            <DecisionDonut data={riskDonut} height={240} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Blocked Requests Trend</CardTitle>
            <CardDescription>Blocked vs total by day</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-3 flex flex-wrap gap-2">
              <Badge variant="danger">Blocked total: {blockedData.total_blocked ?? 0}</Badge>
              <Badge variant="outline">Requests: {blockedData.total_requests ?? 0}</Badge>
              <Badge variant="secondary">Block rate: {formatPercent(blockedData.block_rate_pct)}</Badge>
            </div>
            <TrendChart
              data={(blockedData.breakdown || []).map((b) => ({ timestamp: b.day, total: b.total, blocked: b.blocked }))}
              series={["total", "blocked"]}
              height={220}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Response Time & HITL</CardTitle>
            <CardDescription>Latency summary and approval statistics</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-md border p-3">
                <p className="text-xs text-muted-foreground">Avg execution</p>
                <p className="text-lg font-semibold">{formatDuration(latencyData.avg_execution_time_ms)}</p>
              </div>
              <div className="rounded-md border p-3">
                <p className="text-xs text-muted-foreground">Median</p>
                <p className="text-lg font-semibold">{formatDuration(latencyData.median_execution_time_ms)}</p>
              </div>
              <div className="rounded-md border p-3">
                <p className="text-xs text-muted-foreground">Min</p>
                <p className="text-lg font-semibold">{formatDuration(latencyData.min_execution_time_ms)}</p>
              </div>
              <div className="rounded-md border p-3">
                <p className="text-xs text-muted-foreground">Max</p>
                <p className="text-lg font-semibold">{formatDuration(latencyData.max_execution_time_ms)}</p>
              </div>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-sm font-medium">HITL statistics</p>
              <p className="mt-1 text-xs text-muted-foreground">
                {hitl.data?.total_requests ?? 0} requests · {hitl.data?.approved ?? 0} approved (
                {formatPercent(hitl.data?.approval_rate_pct)} rate) · {hitl.data?.pending ?? 0} pending
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Generated Reports</CardTitle>
          <CardDescription>Daily and monthly analytics reports</CardDescription>
        </CardHeader>
        <CardContent>
          {reports.data?.length === 0 ? (
            <EmptyState title="No reports yet" description="Generate a daily or monthly report above." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Generated at</TableHead>
                  <TableHead>Summary</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(reports.data || []).map((report) => (
                  <TableRow key={report.id}>
                    <TableCell><Badge variant="secondary">{report.report_type}</Badge></TableCell>
                    <TableCell className="font-mono text-xs">{report.period}</TableCell>
                    <TableCell><span className="text-xs text-muted-foreground">{formatDate(report.generated_at)}</span></TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground">
                        {report.data?.summary ? `${report.data.summary}` : `${Object.keys(report.data || {}).length} metrics`}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
