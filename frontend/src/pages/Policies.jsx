import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  ShieldCheck,
  Plus,
  Pencil,
  Trash2,
  Download,
  Upload,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { api, getErrorMessage } from "../lib/api";
import { formatDate } from "../lib/utils";
import { useAuth } from "../context/AuthContext";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { SearchInput } from "../components/shared/SearchInput.jsx";
import { EmptyState } from "../components/shared/EmptyState.jsx";
import { CardSkeleton } from "../components/shared/LoadingSkeleton.jsx";
import { DecisionBadge } from "../components/shared/StatusBadge.jsx";
import {
  Card, CardContent,
} from "../components/ui/card";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle, DialogCloseButton,
} from "../components/ui/dialog";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Select } from "../components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";

const DECISIONS = ["allow", "block", "require_hitl", "log_and_allow"];
const OPERATORS = ["==", "!=", ">", ">=", "<", "<=", "contains", "in", "exists"];

const EMPTY_POLICY = {
  rule_id: "",
  tool: "",
  action: "",
  conditions: [{ field: "", operator: "==", value: "" }],
  combinator: "AND",
  decision: "block",
  message: "",
  priority: 0,
  enabled: true,
  tags: [],
};

function PolicyForm({ initial, onCancel, onSubmit, submitting }) {
  const [form, setForm] = useState(() => ({
    ...EMPTY_POLICY,
    ...initial,
    conditions:
      initial?.conditions?.length
        ? initial.conditions.map((c) => ({ field: c.field, operator: c.operator, value: c.value }))
        : [...EMPTY_POLICY.conditions],
    tags: initial?.tags ? initial.tags.join(", ") : "",
  }));

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const setCondition = (index, patch) =>
    setForm((f) => ({
      ...f,
      conditions: f.conditions.map((c, i) => (i === index ? { ...c, ...patch } : c)),
    }));

  function handleSubmit(e) {
    e.preventDefault();
    const payload = {
      rule_id: form.rule_id,
      tool: form.tool,
      action: form.action,
      conditions: form.conditions.filter((c) => c.field && c.value !== ""),
      combinator: form.combinator,
      decision: form.decision,
      message: form.message,
      priority: Number(form.priority) || 0,
      enabled: form.enabled,
      tags: form.tags ? form.tags.split(",").map((t) => t.trim()).filter(Boolean) : [],
    };
    if (!payload.rule_id || !payload.tool || !payload.action || !payload.message) {
      toast.error("Rule ID, tool, action and message are required");
      return;
    }
    onSubmit(payload);
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Rule ID</Label>
          <Input
            value={form.rule_id}
            disabled={Boolean(initial)}
            onChange={(e) => set({ rule_id: e.target.value })}
            placeholder="block_bulk_delete"
          />
        </div>
        <div className="space-y-2">
          <Label>Priority</Label>
          <Input
            type="number"
            min={0}
            value={form.priority}
            onChange={(e) => set({ priority: e.target.value })}
          />
        </div>
        <div className="space-y-2">
          <Label>Tool</Label>
          <Input value={form.tool} onChange={(e) => set({ tool: e.target.value })} placeholder="database" />
        </div>
        <div className="space-y-2">
          <Label>Action</Label>
          <Input value={form.action} onChange={(e) => set({ action: e.target.value })} placeholder="delete" />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Conditions</Label>
        {form.conditions.map((condition, index) => (
          <div key={index} className="flex items-center gap-2">
            <Input
              className="flex-1"
              placeholder="field (e.g. record_count)"
              value={condition.field}
              onChange={(e) => setCondition(index, { field: e.target.value })}
            />
            <Select
              className="w-28"
              value={condition.operator}
              onChange={(e) => setCondition(index, { operator: e.target.value })}
            >
              {OPERATORS.map((op) => (
                <option key={op} value={op}>{op}</option>
              ))}
            </Select>
            <Input
              className="flex-1"
              placeholder="value"
              value={condition.value}
              onChange={(e) => setCondition(index, { value: e.target.value })}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() =>
                setForm((f) => ({ ...f, conditions: f.conditions.filter((_, i) => i !== index) }))
              }
              aria-label="Remove condition"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setForm((f) => ({ ...f, conditions: [...f.conditions, { field: "", operator: "==", value: "" }] }))}
        >
          <Plus /> Add condition
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label>Combinator</Label>
          <Select value={form.combinator} onChange={(e) => set({ combinator: e.target.value })}>
            <option value="AND">AND</option>
            <option value="OR">OR</option>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Decision</Label>
          <Select value={form.decision} onChange={(e) => set({ decision: e.target.value })}>
            {DECISIONS.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </Select>
        </div>
      </div>

      <div className="space-y-2">
        <Label>Message / Reason</Label>
        <Textarea
          value={form.message}
          onChange={(e) => set({ message: e.target.value })}
          placeholder="Why this policy exists"
        />
      </div>

      <div className="space-y-2">
        <Label>Tags (comma separated)</Label>
        <Input value={form.tags} onChange={(e) => set({ tags: e.target.value })} placeholder="high-risk, data" />
      </div>

      <div className="flex items-center justify-between rounded-md border p-3">
        <div>
          <p className="text-sm font-medium">Enabled</p>
          <p className="text-xs text-muted-foreground">Policies evaluate against incoming actions.</p>
        </div>
        <Switch checked={form.enabled} onCheckedChange={(v) => set({ enabled: v })} />
      </div>

      <DialogFooter className="border-0 p-0">
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" disabled={submitting}>
          {submitting && <Loader2 className="animate-spin" />}
          {initial ? "Update policy" : "Create policy"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export default function Policies() {
  const queryClient = useQueryClient();
  const { hasRole } = useAuth();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [toolFilter, setToolFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [validationResult, setValidationResult] = useState(null);
  const [importOpen, setImportOpen] = useState(false);
  const [importYaml, setImportYaml] = useState("");

  const policies = useQuery({
    queryKey: ["policies"],
    queryFn: async () => (await api.get("/policies")).data,
  });

  const toggleMutation = useMutation({
    mutationFn: (ruleId) => api.post(`/policies/${ruleId}/toggle`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      toast.success("Policy updated");
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const saveMutation = useMutation({
    mutationFn: async (payload) => {
      if (editing) {
        const { rule_id: _unused, ...update } = payload;
        return api.put(`/policies/${editing.rule_id}`, update);
      }
      return api.post("/policies", payload);
    },
    onSuccess: () => {
      toast.success(editing ? "Policy updated" : "Policy created");
      setDialogOpen(false);
      setEditing(null);
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const deleteMutation = useMutation({
    mutationFn: (ruleId) => api.delete(`/policies/${ruleId}`),
    onSuccess: () => {
      toast.success("Policy deleted");
      queryClient.invalidateQueries({ queryKey: ["policies"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const filtered = useMemo(() => {
    if (!policies.data?.rules) return [];
    return policies.data.rules.filter((p) => {
      const matchesSearch =
        !search ||
        [p.rule_id, p.tool, p.action, p.message, (p.tags || []).join(" ")].some((v) =>
          String(v || "").toLowerCase().includes(search.toLowerCase())
        );
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "enabled" && p.enabled) ||
        (statusFilter === "disabled" && !p.enabled);
      const matchesTool = toolFilter === "all" || p.tool === toolFilter;
      return matchesSearch && matchesStatus && matchesTool;
    });
  }, [policies.data, search, statusFilter, toolFilter]);

  const tools = useMemo(
    () => [...new Set((policies.data?.rules || []).map((p) => p.tool))].sort(),
    [policies.data]
  );

  function handleExport() {
    window.open("/api/policies/export/yaml", "_blank");
  }

  async function handleImport() {
    try {
      await api.post("/policies/import", importYaml, { headers: { "Content-Type": "text/plain" } });
      toast.success("Policies imported");
      setImportOpen(false);
      setImportYaml("");
      queryClient.invalidateQueries({ queryKey: ["policies"] });
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  }

  async function handleValidate(payload) {
    setValidationResult(null);
    try {
      const { data } = await api.post("/policies/validate", payload);
      setValidationResult(data);
      if (!data.valid) toast.error("Policy validation failed");
      else toast.success("Policy is valid");
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  }

  if (policies.isLoading) {
    return <div className="space-y-6"><PageHeader title="Policies" description="Manage enforcement rules" icon={ShieldCheck} /><CardSkeleton rows={8} /></div>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Policies"
        description="Define and manage action enforcement rules"
        icon={ShieldCheck}
        actions={
          <>
            {hasRole("auditor") && (
              <Button variant="outline" size="sm" onClick={handleExport}>
                <Download /> Export YAML
              </Button>
            )}
            {hasRole("admin") && (
              <Button variant="outline" size="sm" onClick={() => setImportOpen(true)}>
                <Upload /> Import
              </Button>
            )}
            {hasRole("security_analyst") && (
              <Button size="sm" onClick={() => { setEditing(null); setDialogOpen(true); }}>
                <Plus /> New policy
              </Button>
            )}
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <SearchInput value={search} onChange={setSearch} placeholder="Search policies…" className="w-full sm:w-64" />
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
          <option value="all">All statuses</option>
          <option value="enabled">Enabled</option>
          <option value="disabled">Disabled</option>
        </Select>
        <Select value={toolFilter} onChange={(e) => setToolFilter(e.target.value)} className="w-40">
          <option value="all">All tools</option>
          {tools.map((tool) => (
            <option key={tool} value={tool}>{tool}</option>
          ))}
        </Select>
        <Badge variant="outline" className="ml-auto">
          {filtered.length} of {policies.data?.total ?? 0} rules
        </Badge>
      </div>

      {validationResult && (
        <Alert variant={validationResult.valid ? "success" : "warning"}>
          <AlertTriangle />
          <AlertTitle>
            Validation {validationResult.valid ? "passed" : "failed"}
          </AlertTitle>
          <AlertDescription>
            {validationResult.errors?.length > 0 && (
              <ul className="list-inside list-disc">
                {validationResult.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            )}
            {validationResult.warnings?.length > 0 && (
              <ul className="list-inside list-disc">
                {validationResult.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            )}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="p-0">
          {filtered.length === 0 ? (
            <div className="p-6">
              <EmptyState
                title="No policies match"
                description="Adjust filters or create your first enforcement rule."
                action={<Button size="sm" onClick={() => { setEditing(null); setDialogOpen(true); }}><Plus /> New policy</Button>}
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>Decision</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Tags</TableHead>
                  <TableHead>Enabled</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((policy) => (
                  <TableRow key={policy.rule_id}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span className="font-mono text-xs font-medium">{policy.rule_id}</span>
                        <span className="max-w-[240px] truncate text-xs text-muted-foreground">{policy.message}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs">{policy.tool}</span>
                      <span className="text-muted-foreground"> / </span>
                      <span className="font-mono text-xs">{policy.action}</span>
                    </TableCell>
                    <TableCell><DecisionBadge decision={policy.decision} /></TableCell>
                    <TableCell><Badge variant="outline">{policy.priority}</Badge></TableCell>
                    <TableCell><span className="text-xs text-muted-foreground">v{policy.version}</span></TableCell>
                    <TableCell>
                      <div className="flex max-w-[160px] flex-wrap gap-1">
                        {(policy.tags || []).slice(0, 2).map((tag) => (
                          <Badge key={tag} variant="secondary">{tag}</Badge>
                        ))}
                        {(policy.tags || []).length > 2 && (
                          <Badge variant="secondary">+{(policy.tags || []).length - 2}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Switch
                        checked={policy.enabled}
                        disabled={!hasRole("security_analyst")}
                        onCheckedChange={() => toggleMutation.mutate(policy.rule_id)}
                      />
                    </TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground">{formatDate(policy.updated_at)}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        {hasRole("security_analyst") && (
                          <>
                            <Button
                              variant="ghost" size="icon"
                              onClick={() => { setEditing(policy); setDialogOpen(true); }}
                              aria-label="Edit policy"
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost" size="icon"
                              onClick={() => {
                                if (window.confirm(`Delete policy "${policy.rule_id}"?`)) {
                                  deleteMutation.mutate(policy.rule_id);
                                }
                              }}
                              aria-label="Delete policy"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        {hasRole("operator") && (
                          <Button variant="ghost" size="sm" onClick={() => handleValidate(policy)}>
                            Validate
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogCloseButton onClose={() => setDialogOpen(false)} />
        <DialogHeader>
          <DialogTitle>{editing ? `Edit ${editing.rule_id}` : "Create policy"}</DialogTitle>
          <DialogDescription>
            Configure an enforcement rule evaluated before tool execution.
          </DialogDescription>
        </DialogHeader>
        <DialogContent>
          <PolicyForm
            initial={editing}
            onCancel={() => setDialogOpen(false)}
            onSubmit={(payload) => saveMutation.mutate(payload)}
            submitting={saveMutation.isPending}
          />
        </DialogContent>
      </Dialog>

      <Dialog open={importOpen} onOpenChange={setImportOpen}>
        <DialogCloseButton onClose={() => setImportOpen(false)} />
        <DialogHeader>
          <DialogTitle>Import policies (YAML)</DialogTitle>
          <DialogDescription>
            Paste YAML rules. Existing rule IDs are updated, new ones are created.
          </DialogDescription>
        </DialogHeader>
        <DialogContent className="space-y-4">
          <Textarea
            rows={12}
            value={importYaml}
            onChange={(e) => setImportYaml(e.target.value)}
            placeholder={"rules:\n  - id: block_bulk_delete\n    tool: database\n    action: delete\n    conditions:\n      - field: record_count\n        operator: \">\"\n        value: 100\n    decision: block\n    message: Block bulk deletes"}
            className="font-mono text-xs"
          />
          <DialogFooter className="border-0 p-0">
            <Button variant="outline" onClick={() => setImportOpen(false)}>Cancel</Button>
            <Button onClick={handleImport} disabled={!importYaml.trim()}>Import</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
