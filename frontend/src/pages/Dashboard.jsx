import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  LayoutDashboard,
  Activity,
  Ban,
  CheckCircle2,
  Gauge,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";
import { api } from "../lib/api";
import { formatDuration, formatPercent } from "../lib/utils";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { StatCard } from "../components/shared/StatCard.jsx";
import { PageLoading } from "../components/shared/LoadingSkeleton.jsx";
import { EmptyState } from "../components/shared/EmptyState.jsx";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { TrendChart } from "../components/charts/TrendChart.jsx";
import { DecisionDonut } from "../components/charts/DecisionDonut.jsx";
import { StatusBadge, RiskBadge } from "../components/shared/StatusBadge.jsx";
import { formatDate } from "../lib/utils";

export default function Dashboard() {
  const dashboard = useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => (await api.get("/monitoring/dashboard")).data,
  });

  const timeline = useQuery({
    queryKey: ["metrics", "timeline", "24h"],
    queryFn: async () => (await api.get("/monitoring/metrics/timeline?time_range=24h&granularity=hour")).data,
  });

  const violations = useQuery({
    queryKey: ["violations", "top", "24h"],
    queryFn: async () => (await api.get("/monitoring/violations/top?limit=5&time_range=24h")).data,
  });

  if (dashboard.isLoading || timeline.isLoading) {
    return <PageLoading />;
  }

  if (dashboard.isError || timeline.isError) {
    return (
      <EmptyState
        title="Unable to load dashboard"
        description="Check that the API is reachable and the database is migrated."
      />
    );
  }

  const stats = dashboard.data;
  const activity = stats.recent_activity || [];

  const decisionsFromActivity = activity.reduce((acc, item) => {
    const key = item.decision || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const donutData = Object.entries(decisionsFromActivity).map(([decision, count]) => ({
    decision,
    count,
  }));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Runtime Governance Dashboard"
        description="Live posture of policy enforcement across your AI runtime"
        icon={LayoutDashboard}
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to="/runtime">
              Open Runtime Monitor <ArrowRight />
            </Link>
          </Button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Requests (24h)"
          value={stats.total_requests?.toLocaleString() ?? "0"}
          icon={Activity}
          accent="primary"
        />
        <StatCard
          title="Blocked"
          value={stats.blocked_count?.toLocaleString() ?? "0"}
          icon={Ban}
          accent="danger"
          subtitle={`${formatPercent(stats.total_requests ? ((stats.blocked_count / stats.total_requests) * 100) : 0)} block rate`}
        />
        <StatCard
          title="Success Rate"
          value={formatPercent(stats.success_rate)}
          icon={CheckCircle2}
          accent="success"
        />
        <StatCard
          title="Avg Execution Time"
          value={formatDuration(stats.avg_execution_time_ms)}
          icon={Gauge}
          accent="warning"
          subtitle={`${stats.active_rules_count} active policies`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Execution Timeline</CardTitle>
              <CardDescription>Requests over the last 24 hours</CardDescription>
            </div>
            <Badge variant="outline">{timeline.data?.granularity}</Badge>
          </CardHeader>
          <CardContent>
            <TrendChart data={timeline.data?.points} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Decision Distribution</CardTitle>
            <CardDescription>Outcomes across recent activity</CardDescription>
          </CardHeader>
          <CardContent>
            <DecisionDonut data={donutData} height={220} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest policy evaluations</CardDescription>
          </CardHeader>
          <CardContent>
            {activity.length === 0 ? (
              <EmptyState title="No activity" description="Execute an action to see it here." />
            ) : (
              <ul className="space-y-3">
                {activity.slice(0, 6).map((item) => (
                  <li
                    key={item.id}
                    className="flex items-center justify-between gap-3 rounded-md border p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">
                        {item.tool} <span className="text-muted-foreground">/</span> {item.action}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {formatDate(item.timestamp)}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <RiskBadge risk={item.risk_level} />
                      <StatusBadge status={item.execution_status} />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Violations</CardTitle>
            <CardDescription>Most frequently triggered rules</CardDescription>
          </CardHeader>
          <CardContent>
            {violations.data?.length === 0 ? (
              <EmptyState title="No violations" description="No rule triggers in this window." />
            ) : (
              <ul className="space-y-3">
                {(violations.data || []).map((v) => (
                  <li
                    key={v.matched_rule}
                    className="flex items-center justify-between gap-3 rounded-md border p-3"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-mono text-xs font-medium">{v.matched_rule}</p>
                      {v.tool && (
                        <p className="truncate text-xs text-muted-foreground">
                          {v.tool} / {v.action}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant="danger">{v.count}</Badge>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="border-primary/40 bg-primary/5">
        <CardContent className="flex flex-col items-start justify-between gap-4 p-5 sm:flex-row sm:items-center">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-semibold">
                Top risk level: <span className="uppercase">{stats.top_risk_level}</span>
              </p>
              <p className="text-xs text-muted-foreground">
                {stats.active_rules_count} enforcement policies active in the runtime.
              </p>
            </div>
          </div>
          <Button asChild size="sm">
            <Link to="/policies">Manage Policies</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
