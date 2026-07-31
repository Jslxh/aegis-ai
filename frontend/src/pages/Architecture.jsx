import { useCallback, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Network,
  MonitorSmartphone,
  ServerCog,
  ShieldCheck,
  Wrench,
  UserCheck,
  Database,
  ScrollText,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { Card, CardContent } from "../components/ui/card";

function NodeShell({ data }) {
  const Icon = data.icon;
  return (
    <div
      className="w-52 rounded-lg border bg-card p-3 shadow-sm"
      style={{ borderColor: data.accent || "hsl(var(--border))" }}
    >
      <div className="flex items-center gap-2.5">
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md"
          style={{ background: data.accent || "hsl(var(--primary))", color: "white" }}
        >
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold leading-tight">{data.label}</p>
          <p className="truncate text-[10px] text-muted-foreground">{data.subtitle}</p>
        </div>
      </div>
    </div>
  );
}

export default function Architecture() {
  const nodeTypes = useMemo(() => ({ custom: NodeShell }), []);

  const nodes = useMemo(
    () => [
      {
        id: "client",
        type: "custom",
        position: { x: 60, y: 180 },
        data: { label: "Client Console", subtitle: "React SPA · Agents", icon: MonitorSmartphone, accent: "#6366f1" },
      },
      {
        id: "api",
        type: "custom",
        position: { x: 340, y: 180 },
        data: { label: "API Gateway", subtitle: "FastAPI · JWT + RBAC", icon: ServerCog, accent: "#4f46e5" },
      },
      {
        id: "policy",
        type: "custom",
        position: { x: 640, y: 60 },
        data: { label: "Policy Engine", subtitle: "Evaluator · Operators", icon: ShieldCheck, accent: "#2563eb" },
      },
      {
        id: "audit",
        type: "custom",
        position: { x: 640, y: 300 },
        data: { label: "Audit Logger", subtitle: "Immutable · Checksums", icon: ScrollText, accent: "#0891b2" },
      },
      {
        id: "hitl",
        type: "custom",
        position: { x: 920, y: 60 },
        data: { label: "Approval Queue", subtitle: "Human-in-the-loop", icon: UserCheck, accent: "#f59e0b" },
      },
      {
        id: "executor",
        type: "custom",
        position: { x: 920, y: 210 },
        data: { label: "Tool Executor", subtitle: "Registry · Plugins", icon: Wrench, accent: "#10b981" },
      },
      {
        id: "db",
        type: "custom",
        position: { x: 920, y: 370 },
        data: { label: "PostgreSQL", subtitle: "Models · Alembic", icon: Database, accent: "#0891b2" },
      },
      {
        id: "ai",
        type: "custom",
        position: { x: 1200, y: 210 },
        data: { label: "Groq Explainability", subtitle: "AI explains, never decides", icon: Sparkles, accent: "#8b5cf6" },
      },
    ],
    []
  );

  const edges = useMemo(
    () => [
      { id: "e-client-api", source: "client", target: "api", animated: true },
      { id: "e-api-policy", source: "api", target: "policy", animated: true },
      { id: "e-api-audit", source: "api", target: "audit", animated: true },
      {
        id: "e-policy-hitl",
        source: "policy",
        target: "hitl",
        label: "require_hitl",
        markerEnd: { type: MarkerType.ArrowClosed },
      },
      {
        id: "e-policy-exec",
        source: "policy",
        target: "executor",
        label: "allow / log_and_allow",
        markerEnd: { type: MarkerType.ArrowClosed },
      },
      {
        id: "e-policy-block",
        source: "policy",
        target: "audit",
        label: "block",
        markerEnd: { type: MarkerType.ArrowClosed },
      },
      { id: "e-hitl-audit", source: "hitl", target: "audit" },
      { id: "e-exec-audit", source: "executor", target: "audit" },
      { id: "e-audit-db", source: "audit", target: "db", animated: true },
      { id: "e-hitl-db", source: "hitl", target: "db" },
      { id: "e-exec-db", source: "executor", target: "db" },
      { id: "e-exec-ai", source: "executor", target: "ai" },
      { id: "e-audit-ai", source: "audit", target: "ai" },
      { id: "e-hitl-ai", source: "hitl", target: "ai" },
    ],
    []
  );

  const onNodeClick = useCallback(() => {}, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Architecture Viewer"
        description="Runtime request flow through the governance pipeline"
        icon={Network}
      />
      <Card>
        <CardContent className="p-0">
          <div className="h-[560px] w-full">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodeClick={onNodeClick}
              fitView
              fitViewOptions={{ padding: 0.15 }}
              proOptions={{ hideAttribution: true }}
              nodesConnectable={false}
              minZoom={0.4}
            >
              <Background gap={18} size={1} color="hsl(var(--border))" />
              <Controls />
              <MiniMap
                nodeStrokeWidth={2}
                nodeColor={(n) => n.data.accent || "#4f46e5"}
                maskColor="rgba(0,0,0,0.6)"
                style={{ background: "hsl(var(--card))" }}
              />
            </ReactFlow>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { label: "Client → API Gateway", desc: "Authenticated REST calls protected by JWT + RBAC." },
          { label: "API → Policy Engine", desc: "Every tool call is evaluated before execution." },
          { label: "Decisions", desc: "allow · block · require_hitl · log_and_allow." },
          { label: "Audit every action", desc: "Checksum-chained, tamper-evident audit trail." },
        ].map((item) => (
          <Card key={item.label}>
            <CardContent className="p-4">
              <p className="text-sm font-medium">{item.label}</p>
              <p className="mt-1 text-xs text-muted-foreground">{item.desc}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
