import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { FlaskConical, Play, Sparkles, Loader2, ShieldCheck, Ban, UserCheck, ScrollText } from "lucide-react";
import { api, getErrorMessage } from "../lib/api";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { StatCard } from "../components/shared/StatCard.jsx";
import { EmptyState } from "../components/shared/EmptyState.jsx";
import { CardSkeleton } from "../components/shared/LoadingSkeleton.jsx";
import { JsonView } from "../components/shared/JsonView.jsx";
import { DecisionBadge, RiskBadge } from "../components/shared/StatusBadge.jsx";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select } from "../components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { useAuth } from "../context/AuthContext";

export default function Simulation() {
  const { hasRole } = useAuth();
  const [dryRun, setDryRun] = useState({ tool: "database", action: "delete", extra: "record_count=500" });
  const [dryResult, setDryResult] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [run, setRun] = useState(null);
  const [running, setRunning] = useState(false);

  const dryRunMutation = useMutation({
    mutationFn: async () => {
      const extra = {};
      dryRun.extra.split(",").forEach((pair) => {
        const [k, v] = pair.trim().split("=");
        if (k) extra[k.trim()] = v !== undefined ? v.trim() : true;
      });
      const body = { tool: dryRun.tool, action: dryRun.action, ...extra };
      return (await api.post("/execute?dry_run=true", body)).data;
    },
    onSuccess: (data) => setDryResult(data),
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.get("/simulate");
      const { data: analysisData } = await api.post("/ai/simulation-summary", {
        summary: data.summary,
        results: data.results,
      });
      return { run: data, analysis: analysisData };
    },
    onSuccess: ({ run: runData, analysis: a }) => {
      setRun(runData);
      setAnalysis(a);
      toast.success("Simulation analysis generated");
    },
    onError: (err) => toast.error(getErrorMessage(err, "Unable to generate AI analysis")),
  });

  async function runSimulation() {
    setRunning(true);
    try {
      const { data } = await api.get("/simulate");
      setRun(data);
      toast.success(`Simulation completed: ${data.total_scenarios} scenarios`);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setRunning(false);
    }
  }

  if (running && !run) {
    return <div className="space-y-6"><PageHeader title="Simulation" description="Scenario harness and dry-run" icon={FlaskConical} /><CardSkeleton rows={6} /></div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Simulation"
        description="Validate policy behavior against scenarios without side effects"
        icon={FlaskConical}
        actions={
          <>
            {hasRole("auditor") && (
              <Button variant="outline" size="sm" onClick={() => analyzeMutation.mutate()} disabled={analyzeMutation.isPending}>
                {analyzeMutation.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
                AI analysis
              </Button>
            )}
            <Button size="sm" onClick={runSimulation} disabled={running}>
              {running ? <Loader2 className="animate-spin" /> : <Play />}
              Run simulation
            </Button>
          </>
        }
      />

      {!run ? (
        <EmptyState
          title="No simulation run yet"
          description="Run the built-in scenario harness to evaluate policy outcomes."
          action={<Button size="sm" onClick={runSimulation}><Play /> Run simulation</Button>}
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard title="Scenarios" value={run.total_scenarios} icon={FlaskConical} accent="primary" />
            <StatCard title="Blocked" value={run.summary.blocked ?? 0} icon={Ban} accent="danger" />
            <StatCard title="Require HITL" value={run.summary.require_hitl ?? 0} icon={UserCheck} accent="warning" />
            <StatCard title="Allowed / Logged" value={(run.summary.allowed ?? 0) + (run.summary.log_and_allow ?? 0)} icon={ShieldCheck} accent="success" />
          </div>

          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Scenario</TableHead>
                    <TableHead>Tool / Action</TableHead>
                    <TableHead>Decision</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Rule</TableHead>
                    <TableHead>Executed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {run.results.map((scenario, i) => (
                    <TableRow key={i}>
                      <TableCell className="text-sm font-medium">{scenario.scenario}</TableCell>
                      <TableCell>
                        <span className="font-mono text-xs">{scenario.request.tool} / {scenario.request.action}</span>
                      </TableCell>
                      <TableCell><DecisionBadge decision={scenario.decision} /></TableCell>
                      <TableCell>
                        <RiskBadge risk={scenario.decision === "block" ? "critical" : scenario.decision === "require_hitl" ? "high" : scenario.decision === "log_and_allow" ? "medium" : "low"} />
                      </TableCell>
                      <TableCell><span className="font-mono text-xs">{scenario.matched_rule || "—"}</span></TableCell>
                      <TableCell>{scenario.executed ? <Badge variant="success">Yes</Badge> : <Badge variant="secondary">No</Badge>}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Dry-run console</CardTitle>
            <CardDescription>Evaluate an action without executing the tool</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="tool">Tool</Label>
                <Select id="tool" value={dryRun.tool} onChange={(e) => setDryRun((d) => ({ ...d, tool: e.target.value }))}>
                  {["database", "email", "file", "shell", "http"].map((t) => <option key={t} value={t}>{t}</option>)}
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="action">Action</Label>
                <Input id="action" value={dryRun.action} onChange={(e) => setDryRun((d) => ({ ...d, action: e.target.value }))} placeholder="delete" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="extra">Parameters (k=v, comma separated)</Label>
              <Input id="extra" value={dryRun.extra} onChange={(e) => setDryRun((d) => ({ ...d, extra: e.target.value }))} placeholder="record_count=500" />
            </div>
            <Button onClick={() => dryRunMutation.mutate()} disabled={dryRunMutation.isPending}>
              {dryRunMutation.isPending ? <Loader2 className="animate-spin" /> : <ScrollText />}
              Evaluate (dry run)
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Dry-run result</CardTitle>
            <CardDescription>What would happen on real execution</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {!dryResult ? (
              <EmptyState title="No evaluation yet" description="Submit a dry run to see the preview." />
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <DecisionBadge decision={dryResult.decision} />
                  <RiskBadge risk={dryResult.risk_level} />
                  {dryResult.would_execute && <Badge variant="success">Would execute</Badge>}
                  {dryResult.would_block && <Badge variant="danger">Would block</Badge>}
                  {dryResult.would_require_hitl && <Badge variant="warning">Would require HITL</Badge>}
                </div>
                {dryResult.matched_rule && (
                  <p className="text-sm"><span className="text-muted-foreground">Matched rule:</span> <span className="font-mono text-xs">{dryResult.matched_rule}</span></p>
                )}
                <p className="text-sm text-muted-foreground">{dryResult.reason}</p>
                {dryResult.simulated_output && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-muted-foreground">Simulated tool output</p>
                    <JsonView data={dryResult.simulated_output} />
                  </div>
                )}
                {dryResult.audit_preview && (
                  <div>
                    <p className="mb-1 text-xs font-medium text-muted-foreground">Audit preview</p>
                    <JsonView data={dryResult.audit_preview} />
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {analysis && (
        <Alert variant="info">
          <Sparkles />
          <AlertTitle>AI Simulation Analysis</AlertTitle>
          <AlertDescription>
            <div className="mt-2 space-y-3">
              {analysis.summary && <p>{analysis.summary}</p>}
              {analysis.explanation && <p className="whitespace-pre-wrap">{analysis.explanation}</p>}
              {analysis.risk_analysis && <p className="whitespace-pre-wrap">{analysis.risk_analysis}</p>}
              {analysis.recommendations?.length > 0 && (
                <ul className="list-inside list-disc">
                  {analysis.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
            </div>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
