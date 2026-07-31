import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Sparkles, Loader2, ShieldAlert, Info } from "lucide-react";
import { api, getErrorMessage } from "../lib/api";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { Tabs, TabsList, TabsContent } from "../components/ui/tabs";

const TABS = [
  { value: "explain", label: "Explain decision" },
  { value: "risk", label: "Risk analysis" },
  { value: "execution", label: "Execution explanation" },
  { value: "audit", label: "Audit summary" },
];

function AiResultCard({ result }) {
  if (!result) return null;
  if (!result.success) {
    return (
      <Alert variant="destructive">
        <ShieldAlert />
        <AlertTitle>Generation failed</AlertTitle>
        <AlertDescription>{result.error || "Unknown error"}</AlertDescription>
      </Alert>
    );
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">{result.model || "model"}</Badge>
        {result.confidence != null && <Badge variant="outline">Confidence {result.confidence}</Badge>}
        {result.risk_level && <Badge variant="warning">Risk: {result.risk_level}</Badge>}
        {result.latency != null && <Badge variant="outline">{result.latency} ms</Badge>}
      </div>
      {result.summary && (
        <div className="rounded-md border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Summary</p>
          <p className="mt-1 text-sm">{result.summary}</p>
        </div>
      )}
      {result.explanation && (
        <div className="rounded-md border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Explanation</p>
          <p className="mt-1 whitespace-pre-wrap text-sm">{result.explanation}</p>
        </div>
      )}
      {result.risk_analysis && (
        <div className="rounded-md border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Risk analysis</p>
          <p className="mt-1 whitespace-pre-wrap text-sm">{result.risk_analysis}</p>
        </div>
      )}
      {result.recommendations?.length > 0 && (
        <div className="rounded-md border p-3">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recommendations</p>
          <ul className="mt-1 list-inside list-disc text-sm">
            {result.recommendations.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function AIExplainability() {
  const [tab, setTab] = useState("explain");
  const [result, setResult] = useState(null);
  const [explain, setExplain] = useState({ matched_rule: "", decision: "block", reason: "", request: "" });
  const [risk, setRisk] = useState({ tool: "database", action: "delete", parameters: "", decision: "block" });
  const [executionId, setExecutionId] = useState("");
  const [auditId, setAuditId] = useState("");

  const clear = () => setResult(null);

  const mutation = useMutation({
    mutationFn: async ({ type }) => {
      if (type === "explain") {
        const request = JSON.parse(explain.request || "{}");
        const body = {
          matched_rule: explain.matched_rule || null,
          decision: explain.decision,
          reason: explain.reason,
          request,
        };
        return (await api.post("/ai/explain", body)).data;
      }
      if (type === "risk") {
        const parameters = JSON.parse(risk.parameters || "{}");
        return (await api.post("/ai/risk-analysis", {
          tool: risk.tool,
          action: risk.action,
          parameters,
          decision: risk.decision,
        })).data;
      }
      if (type === "execution") {
        if (!executionId) throw new Error("Enter an execution ID");
        return (await api.get(`/ai/executions/${executionId}/explanation`)).data;
      }
      if (type === "audit") {
        if (!auditId) throw new Error("Enter an audit ID");
        return (await api.get(`/ai/audit/${auditId}/summary`)).data;
      }
      throw new Error("Unknown action");
    },
    onSuccess: (data) => setResult(data),
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI Explainability"
        description="Groq-powered explanations — AI explains decisions, it never makes them"
        icon={Sparkles}
      />

      <Alert variant="info">
        <Info />
        <AlertTitle>Guardrail invariant</AlertTitle>
        <AlertDescription>
          The AI model is used exclusively to explain, summarize and analyze decisions made by the
          deterministic policy engine. It has no influence over policy outcomes.
        </AlertDescription>
      </Alert>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Generator</CardTitle>
            <CardDescription>Choose an analysis type and provide inputs</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Tabs value={tab} onValueChange={setTab}>
              <TabsList items={TABS} value={tab} onValueChange={setTab} className="w-full" />
            </Tabs>

            <TabsContent value={tab} activeValue="explain">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Matched rule</Label>
                  <Input value={explain.matched_rule} onChange={(e) => { clear(); setExplain((f) => ({ ...f, matched_rule: e.target.value })); }} placeholder="block_bulk_delete" />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Decision</Label>
                    <Select value={explain.decision} onChange={(e) => { clear(); setExplain((f) => ({ ...f, decision: e.target.value })); }}>
                      {["allow", "block", "require_hitl", "log_and_allow"].map((d) => <option key={d} value={d}>{d}</option>)}
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Reason</Label>
                    <Input value={explain.reason} onChange={(e) => { clear(); setExplain((f) => ({ ...f, reason: e.target.value })); }} placeholder="Why the policy matched" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Request (JSON)</Label>
                  <Textarea rows={4} value={explain.request} onChange={(e) => { clear(); setExplain((f) => ({ ...f, request: e.target.value })); }} placeholder='{"tool": "database", "action": "delete", "record_count": 500}' className="font-mono text-xs" />
                </div>
              </div>
            </TabsContent>

            <TabsContent value={tab} activeValue="risk">
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Tool</Label>
                    <Input value={risk.tool} onChange={(e) => { clear(); setRisk((f) => ({ ...f, tool: e.target.value })); }} />
                  </div>
                  <div className="space-y-2">
                    <Label>Action</Label>
                    <Input value={risk.action} onChange={(e) => { clear(); setRisk((f) => ({ ...f, action: e.target.value })); }} />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Parameters (JSON)</Label>
                  <Textarea rows={4} value={risk.parameters} onChange={(e) => { clear(); setRisk((f) => ({ ...f, parameters: e.target.value })); }} placeholder='{"recipient": "external", "attachment": true}' className="font-mono text-xs" />
                </div>
                <div className="space-y-2">
                  <Label>Decision</Label>
                  <Select value={risk.decision} onChange={(e) => { clear(); setRisk((f) => ({ ...f, decision: e.target.value })); }}>
                    {["allow", "block", "require_hitl", "log_and_allow"].map((d) => <option key={d} value={d}>{d}</option>)}
                  </Select>
                </div>
              </div>
            </TabsContent>

            <TabsContent value={tab} activeValue="execution">
              <div className="space-y-2">
                <Label>Execution ID</Label>
                <Input value={executionId} onChange={(e) => { clear(); setExecutionId(e.target.value); }} placeholder="123" type="number" />
                <p className="text-xs text-muted-foreground">Retrieves (or generates) the stored explanation for an execution.</p>
              </div>
            </TabsContent>

            <TabsContent value={tab} activeValue="audit">
              <div className="space-y-2">
                <Label>Audit record ID</Label>
                <Input value={auditId} onChange={(e) => { clear(); setAuditId(e.target.value); }} placeholder="42" type="number" />
                <p className="text-xs text-muted-foreground">Retrieves (or generates) the AI summary for an audit record.</p>
              </div>
            </TabsContent>

            <Button
              onClick={() => mutation.mutate({ type: tab })}
              disabled={mutation.isPending}
              className="w-full"
            >
              {mutation.isPending ? <Loader2 className="animate-spin" /> : <Sparkles />}
              Generate analysis
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Result</CardTitle>
            <CardDescription>AI-generated insight for the selected context</CardDescription>
          </CardHeader>
          <CardContent>
            {!result && !mutation.isPending ? (
              <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
                Run a generation to see the analysis here.
              </div>
            ) : mutation.isPending ? (
              <div className="flex h-64 flex-col items-center justify-center gap-3 text-sm text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin" />
                Generating analysis…
              </div>
            ) : (
              <AiResultCard result={result} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
