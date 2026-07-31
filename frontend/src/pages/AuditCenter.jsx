import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ScrollText, Download, FileJson, ShieldCheck, Filter } from "lucide-react";
import { api } from "../lib/api";
import { formatDate, toQueryString } from "../lib/utils";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { EmptyState } from "../components/shared/EmptyState.jsx";
import { Pagination } from "../components/shared/Pagination.jsx";
import { SearchInput } from "../components/shared/SearchInput.jsx";
import { CardSkeleton } from "../components/shared/LoadingSkeleton.jsx";
import { JsonView } from "../components/shared/JsonView.jsx";
import { TrendChart } from "../components/charts/TrendChart.jsx";
import { StatusBadge, RiskBadge, DecisionBadge } from "../components/shared/StatusBadge.jsx";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogCloseButton } from "../components/ui/dialog";

const DECISIONS = ["allow", "block", "require_hitl", "log_and_allow"];
const STATUSES = ["executed", "executed_with_logging", "blocked", "waiting_for_human", "failed"];

export default function AuditCenter() {
  const [filters, setFilters] = useState({ page: 1, page_size: 50 });
  const [searchInput, setSearchInput] = useState("");
  const [selected, setSelected] = useState(null);
  const [integrity, setIntegrity] = useState(null);
  const [integrityLoading, setIntegrityLoading] = useState(false);

  const set = (patch) => setFilters((f) => ({ ...f, ...patch, page: 1 }));

  const logs = useQuery({
    queryKey: ["audit", "logs", filters],
    queryFn: async () => {
      const params = { ...filters };
      if (!params.search) delete params.search;
      return (await api.get(`/audit/logs${toQueryString(params)}`)).data;
    },
  });

  const timeline = useQuery({
    queryKey: ["audit", "timeline"],
    queryFn: async () => (await api.get("/audit/timeline?granularity=hour&limit=48")).data,
  });

  useEffect(() => {
    const timer = setTimeout(() => set({ search: searchInput || undefined }), 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  async function verifyIntegrity() {
    setIntegrityLoading(true);
    try {
      const { data } = await api.get("/audit/verify");
      setIntegrity(data);
    } finally {
      setIntegrityLoading(false);
    }
  }

  function download(format) {
    const params = { ...filters, page: undefined, page_size: undefined };
    const qs = toQueryString(params);
    window.open(`/api/audit/export/${format}${qs}`, "_blank");
  }

  const exportCsv = () => download("csv");
  const exportJson = () => download("json");

  const timelineData = (timeline.data?.points || []).map((p) => ({
    timestamp: p.bucket,
    total: p.total,
    blocked: p.decisions?.block || 0,
    allowed: (p.decisions?.allow || 0) + (p.decisions?.log_and_allow || 0),
    failed: 0,
  }));

  if (logs.isLoading) {
    return <div className="space-y-6"><PageHeader title="Audit Center" description="Immutable audit trail" icon={ScrollText} /><CardSkeleton rows={8} /></div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Audit Center"
        description="Searchable, tamper-evident audit trail with correlation IDs"
        icon={ScrollText}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={verifyIntegrity} disabled={integrityLoading}>
              <ShieldCheck /> {integrityLoading ? "Verifying…" : "Verify integrity"}
            </Button>
            <Button variant="outline" size="sm" onClick={exportCsv}><Download /> CSV</Button>
            <Button variant="outline" size="sm" onClick={exportJson}><FileJson /> JSON</Button>
          </>
        }
      />

      {integrity && (
        <Alert variant={integrity.valid ? "success" : "destructive"}>
          <ShieldCheck />
          <AlertTitle>
            Integrity check {integrity.valid ? "passed" : "FAILED"}
          </AlertTitle>
          <AlertDescription>
            Checked {integrity.checked} records. {integrity.errors?.length || 0} errors.
            {integrity.errors?.slice(0, 3).map((e, i) => <p key={i}>{e}</p>)}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Audit Timeline</CardTitle>
          <CardDescription>Event volume by decision</CardDescription>
        </CardHeader>
        <CardContent>
          <TrendChart data={timelineData} series={["total", "blocked", "allowed"]} />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="w-full sm:w-64">
              <SearchInput value={searchInput} onChange={setSearchInput} placeholder="Search IDs, rules, reasons…" />
            </div>
            <Select value={filters.tool || ""} onChange={(e) => set({ tool: e.target.value || undefined })} className="w-40">
              <option value="">All tools</option>
              <option value="database">database</option>
              <option value="email">email</option>
              <option value="file">file</option>
              <option value="shell">shell</option>
              <option value="http">http</option>
            </Select>
            <Select value={filters.decision || ""} onChange={(e) => set({ decision: e.target.value || undefined })} className="w-40">
              <option value="">All decisions</option>
              {DECISIONS.map((d) => <option key={d} value={d}>{d}</option>)}
            </Select>
            <Select value={filters.status || ""} onChange={(e) => set({ status: e.target.value || undefined })} className="w-44">
              <option value="">All statuses</option>
              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
            <Select value={filters.risk_level || ""} onChange={(e) => set({ risk_level: e.target.value || undefined })} className="w-40">
              <option value="">All risk</option>
              <option value="low">low</option>
              <option value="medium">medium</option>
              <option value="high">high</option>
              <option value="critical">critical</option>
            </Select>
            <Input
              type="date"
              value={filters.start_date || ""}
              onChange={(e) => set({ start_date: e.target.value || undefined })}
              className="w-40"
            />
            <Input
              type="date"
              value={filters.end_date || ""}
              onChange={(e) => set({ end_date: e.target.value || undefined })}
              className="w-40"
            />
            {(Object.values(filters).some((v) => v) || searchInput) && (
              <Button
                variant="ghost" size="sm"
                onClick={() => { setFilters({ page: 1, page_size: 50 }); setSearchInput(""); }}
              >
                Clear
              </Button>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Filter className="h-3.5 w-3.5" />
            {logs.data?.total ?? 0} records · page {logs.data?.page ?? 1} of {logs.data?.pages ?? 1}
          </div>

          {logs.data?.items?.length === 0 ? (
            <EmptyState title="No audit records" description="Adjust filters or wait for new executions." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Tool / Action</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Rule</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Correlation ID</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(logs.data?.items || []).map((item) => (
                  <TableRow key={item.id} onClick={() => setSelected(item)} className="cursor-pointer">
                    <TableCell><span className="whitespace-nowrap text-xs text-muted-foreground">{formatDate(item.timestamp)}</span></TableCell>
                    <TableCell>
                      <span className="font-mono text-xs">{item.tool} / {item.action}</span>
                    </TableCell>
                    <TableCell><DecisionBadge decision={item.decision} /></TableCell>
                    <TableCell><span className="font-mono text-xs">{item.matched_rule || "—"}</span></TableCell>
                    <TableCell><StatusBadge status={item.status} /></TableCell>
                    <TableCell><RiskBadge risk={item.risk_level} /></TableCell>
                    <TableCell><span className="font-mono text-[10px] text-muted-foreground">{item.correlation_id || "—"}</span></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          <Pagination
            page={logs.data?.page ?? 1}
            pages={logs.data?.pages ?? 1}
            total={logs.data?.total ?? 0}
            onChange={(p) => setFilters((f) => ({ ...f, page: p }))}
            loading={logs.isFetching}
          />
        </CardContent>
      </Card>

      <Dialog open={Boolean(selected)} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogCloseButton onClose={() => setSelected(null)} />
        <DialogHeader>
          <DialogTitle>Audit record #{selected?.id}</DialogTitle>
        </DialogHeader>
        <DialogContent className="space-y-4">
          {selected && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{selected.tool} / {selected.action}</Badge>
                <DecisionBadge decision={selected.decision} />
                <StatusBadge status={selected.status} />
                <RiskBadge risk={selected.risk_level} />
              </div>
              {selected.matched_rule && (
                <p className="text-sm"><span className="text-muted-foreground">Rule:</span> <span className="font-mono text-xs">{selected.matched_rule}</span></p>
              )}
              {selected.reason && <p className="text-sm text-muted-foreground">{selected.reason}</p>}
              <div className="grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
                <span>Correlation: <span className="font-mono">{selected.correlation_id || "—"}</span></span>
                <span>Request: <span className="font-mono">{selected.request_id || "—"}</span></span>
                <span>Execution: <span className="font-mono">{selected.execution_id || "—"}</span></span>
                <span>Actor: {selected.actor || "system"}</span>
              </div>
              <div className="grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
                <span>Checksum: <span className="font-mono">{selected.checksum || "—"}</span></span>
                <span>Prev: <span className="font-mono">{selected.prev_checksum || "—"}</span></span>
              </div>
              {selected.request_data && (
                <div>
                  <p className="mb-1 text-xs font-medium text-muted-foreground">Request</p>
                  <JsonView data={selected.request_data} />
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
