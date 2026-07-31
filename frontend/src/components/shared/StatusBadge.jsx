import { Badge } from "../ui/badge";
import { getDecisionMeta, getRiskMeta, getStatusMeta } from "../../lib/status";

export function DecisionBadge({ decision }) {
  const meta = getDecisionMeta(decision);
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}

export function RiskBadge({ risk }) {
  const meta = getRiskMeta(risk);
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}

export function StatusBadge({ status }) {
  const meta = getStatusMeta(status);
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}
