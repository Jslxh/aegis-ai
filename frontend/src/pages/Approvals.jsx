import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ClipboardCheck, Check, X } from "lucide-react";
import { api, getErrorMessage } from "../lib/api";
import { formatDate } from "../lib/utils";
import { useAuth } from "../context/AuthContext";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { StatCard } from "../components/shared/StatCard.jsx";
import { EmptyState } from "../components/shared/EmptyState.jsx";
import { Pagination } from "../components/shared/Pagination.jsx";
import { CardSkeleton } from "../components/shared/LoadingSkeleton.jsx";
import { JsonView } from "../components/shared/JsonView.jsx";
import { StatusBadge, RiskBadge } from "../components/shared/StatusBadge.jsx";
import { Card, CardContent } from "../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Label } from "../components/ui/label";
import { Select } from "../components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogCloseButton } from "../components/ui/dialog";

const STATUS_OPTIONS = ["pending", "approved", "rejected", "expired", "all"];

function riskLevel(policyDecision) {
  if (policyDecision === "require_hitl") return "high";
  return "medium";
}

export default function Approvals() {
  const { hasRole } = useAuth();
  const queryClient = useQueryClient();
  const [status, setStatus] = useState("pending");
  const [page, setPage] = useState(1);
  const [active, setActive] = useState(null);
  const [reason, setReason] = useState("");
  const [comments, setComments] = useState("");

  const approvals = useQuery({
    queryKey: ["approvals", { status, page }],
    queryFn: async () => (await api.get(`/approvals?status=${status}&page=${page}&page_size=25`)).data,
  });

  const stats = useQuery({
    queryKey: ["approvals", "stats"],
    queryFn: async () => (await api.get("/approvals/stats")).data,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["approvals"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  };

  const resolveMutation = useMutation({
    mutationFn: ({ id, action }) =>
      api.post(`/approvals/${id}/${action}`, { reason: reason || null, comments: comments || null }),
    onSuccess: (_data, vars) => {
      toast.success(vars.action === "approve" ? "Request approved" : "Request rejected");
      setActive(null);
      setReason("");
      setComments("");
      invalidate();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const canResolve = hasRole("security_analyst");

  if (approvals.isLoading || stats.isLoading) {
    return <div className="space-y-6"><PageHeader title="Approval Center" description="Human-in-the-loop workflow" icon={ClipboardCheck} /><CardSkeleton rows={6} /></div>;
  }

  const s = stats.data || {};

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approval Center"
        description="Review actions that require human-in-the-loop approval"
        icon={ClipboardCheck}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="Pending" value={s.pending ?? 0} icon={ClipboardCheck} accent="warning" />
        <StatCard title="Approved" value={s.approved ?? 0} icon={Check} accent="success" subtitle={`${s.approval_rate_pct ?? 0}% approval rate`} />
        <StatCard title="Rejected" value={s.rejected ?? 0} icon={X} accent="danger" subtitle={`${s.rejection_rate_pct ?? 0}% rejection rate`} />
        <StatCard title="Total" value={s.total_requests ?? 0} icon={ClipboardCheck} accent="primary" />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="w-48">
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </Select>
        <Badge variant="outline" className="ml-auto">{approvals.data?.total ?? 0} requests</Badge>
      </div>

      <Card>
        <CardContent className="p-0">
          {approvals.data?.items?.length === 0 ? (
            <div className="p-6">
              <EmptyState title={`No ${status === "all" ? "" : status + " "}approval requests`} description="Requests appear here when an action evaluates to require_hitl." />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Request</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Reviewer</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(approvals.data?.items || []).map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      <span className="font-mono text-xs">{item.request_id}</span>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs">{item.tool} / {item.action}</span>
                    </TableCell>
                    <TableCell><RiskBadge risk={riskLevel(item.policy_decision)} /></TableCell>
                    <TableCell><StatusBadge status={item.status} /></TableCell>
                    <TableCell>
                      <span className="text-xs text-muted-foreground">{item.reviewer || "—"}</span>
                    </TableCell>
                    <TableCell><span className="text-xs text-muted-foreground">{formatDate(item.created_at)}</span></TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1">
                        <Button variant="outline" size="sm" onClick={() => setActive(item)}>Review</Button>
                        {item.status === "pending" && canResolve && (
                          <>
                            <Button variant="default" size="sm" onClick={() => resolveMutation.mutate({ id: item.request_id, action: "approve" })}>
                              <Check /> Approve
                            </Button>
                            <Button variant="destructive" size="sm" onClick={() => resolveMutation.mutate({ id: item.request_id, action: "reject" })}>
                              <X /> Reject
                            </Button>
                          </>
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

      <Pagination page={page} pages={approvals.data?.pages ?? 1} total={approvals.data?.total ?? 0} onChange={setPage} loading={approvals.isFetching} />

      <Dialog open={Boolean(active)} onOpenChange={(v) => !v && setActive(null)}>
        <DialogCloseButton onClose={() => setActive(null)} />
        <DialogHeader>
          <DialogTitle>Approval review</DialogTitle>
          <DialogDescription>Request {active?.request_id}</DialogDescription>
        </DialogHeader>
        <DialogContent className="space-y-4">
          {active && (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{active.tool} / {active.action}</Badge>
                <StatusBadge status={active.status} />
                <span className="text-xs text-muted-foreground">Created {formatDate(active.created_at)}</span>
              </div>
              {active.policy_reason && (
                <p className="text-sm text-muted-foreground">{active.policy_reason}</p>
              )}
              <div>
                <Label className="mb-1 block">Request payload</Label>
                <JsonView data={active.request_data} />
              </div>
              {active.status === "pending" && canResolve ? (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="reason">Decision reason</Label>
                    <Input id="reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why you approved or rejected" />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="comments">Comments</Label>
                    <Textarea id="comments" value={comments} onChange={(e) => setComments(e.target.value)} placeholder="Notes for the audit trail" />
                  </div>
                  <DialogFooter className="border-0 p-0">
                    <Button variant="outline" onClick={() => setActive(null)}>Close</Button>
                    <Button variant="destructive" onClick={() => resolveMutation.mutate({ id: active.request_id, action: "reject" })}>
                      <X /> Reject
                    </Button>
                    <Button onClick={() => resolveMutation.mutate({ id: active.request_id, action: "approve" })}>
                      <Check /> Approve
                    </Button>
                  </DialogFooter>
                </>
              ) : (
                <div className="rounded-md border p-3 text-sm">
                  {active.reviewer && (
                    <p><span className="text-muted-foreground">Reviewed by:</span> {active.reviewer}</p>
                  )}
                  {active.approval_reason && (
                    <p><span className="text-muted-foreground">Reason:</span> {active.approval_reason}</p>
                  )}
                  {active.comments && (
                    <p><span className="text-muted-foreground">Comments:</span> {active.comments}</p>
                  )}
                  {active.approved_at && (
                    <p><span className="text-muted-foreground">Approved at:</span> {formatDate(active.approved_at)}</p>
                  )}
                  {active.rejected_at && (
                    <p><span className="text-muted-foreground">Rejected at:</span> {formatDate(active.rejected_at)}</p>
                  )}
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
