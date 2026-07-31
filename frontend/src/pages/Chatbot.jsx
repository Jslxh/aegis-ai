import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  MessageSquare,
  Send,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Database,
  Mail,
  FileText,
  Shield,
  ArrowRight,
  Loader2,
  HelpCircle,
} from "lucide-react";
import { api, getErrorMessage } from "../lib/api";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";

export default function Chatbot() {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      role: "assistant",
      content: "Hello! I am Aegis AI, your security governance copilot. Tell me what action you'd like to perform (e.g., 'send email to external@customer.com', 'read /docs/api.md', or 'delete 50 records from database'). I will format the request and execute it through the Aegis Policy Engine to verify its safety.",
    },
  ]);
  const [input, setInput] = useState("");
  const [activeExecution, setActiveExecution] = useState(null);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: async (body) => {
      return (await api.post("/ai/chat", body)).data;
    },
    onSuccess: (data) => {
      const assistantMessage = {
        id: Date.now().toString(),
        role: "assistant",
        content: data.response,
        isToolCall: data.is_tool_call,
        toolCall: data.tool_call,
        executionResult: data.execution_result,
        explanation: data.explanation,
        recommendations: data.recommendations,
        riskLevel: data.risk_level,
        summary: data.summary,
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
      if (data.is_tool_call && data.execution_result) {
        setActiveExecution(assistantMessage);
      }
    },
    onError: (err) => {
      toast.error(`Chat error: ${getErrorMessage(err)}`);
    },
  });

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || chatMutation.isPending) return;

    const userMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    const history = messages
      .filter((m) => m.id !== "welcome")
      .slice(-6)
      .map((m) => ({
        role: m.role,
        content: m.content,
      }));

    chatMutation.mutate({
      message: userMessage.content,
      history,
    });
  };

  const getToolIcon = (tool) => {
    switch (tool?.toLowerCase()) {
      case "database":
        return <Database className="h-4 w-4" />;
      case "email":
        return <Mail className="h-4 w-4" />;
      case "file":
        return <FileText className="h-4 w-4" />;
      default:
        return <HelpCircle className="h-4 w-4" />;
    }
  };

  const getDecisionBadge = (decision) => {
    switch (decision?.toLowerCase()) {
      case "allow":
      case "log_and_allow":
        return <Badge className="bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 border-emerald-500/20">Allowed</Badge>;
      case "block":
        return <Badge className="bg-destructive/10 text-destructive hover:bg-destructive/20 border-destructive/20">Blocked</Badge>;
      case "require_hitl":
        return <Badge className="bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 border-amber-500/20">HITL Required</Badge>;
      default:
        return <Badge variant="secondary">{decision}</Badge>;
    }
  };

  return (
    <div className="flex flex-col space-y-6 h-[calc(100vh-8rem)]">
      <PageHeader
        title="AI Chatbot Copilot"
        description="Issue conversational action requests and view real-time safety policy enforcement."
        icon={MessageSquare}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 flex-1 overflow-hidden">
        {/* Chat Panel */}
        <Card className="lg:col-span-7 flex flex-col h-full overflow-hidden border-border bg-card">
          <CardHeader className="border-b border-border/40 pb-4">
            <CardTitle className="text-base flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary animate-pulse" />
              Conversation with Aegis Agent
            </CardTitle>
            <CardDescription>
              Interact using natural language commands to invoke tools.
            </CardDescription>
          </CardHeader>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[85%] ${
                  msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
                }`}
              >
                <div
                  className={`flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-full border ${
                    msg.role === "user"
                      ? "bg-primary border-primary text-primary-foreground"
                      : "bg-muted border-border text-muted-foreground"
                  }`}
                >
                  {msg.role === "user" ? "U" : <Sparkles className="h-4 w-4" />}
                </div>

                <div className="space-y-2 flex-1">
                  <div
                    className={`rounded-lg px-4 py-2.5 text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {msg.content}
                  </div>

                  {msg.isToolCall && msg.toolCall && msg.executionResult && (
                    <div
                      onClick={() => setActiveExecution(msg)}
                      className={`cursor-pointer rounded-lg border p-3.5 space-y-3 transition-all hover:bg-muted/50 ${
                        msg.executionResult.decision === "block"
                          ? "border-destructive/30 bg-destructive/5"
                          : msg.executionResult.decision === "require_hitl"
                          ? "border-amber-500/30 bg-amber-500/5"
                          : "border-emerald-500/30 bg-emerald-500/5"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 border-b border-border/40 pb-2">
                        <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                          {getToolIcon(msg.toolCall.tool)}
                          <span className="capitalize">{msg.toolCall.tool}</span>
                          <ArrowRight className="h-3 w-3 text-muted-foreground" />
                          <span className="font-mono text-muted-foreground">{msg.toolCall.action}</span>
                        </div>
                        {getDecisionBadge(msg.executionResult.decision)}
                      </div>

                      <div className="text-xs space-y-1">
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Status:</span>
                          <span className="font-medium text-foreground">{msg.executionResult.status}</span>
                        </div>
                        {msg.executionResult.matched_rule && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Triggered Policy:</span>
                            <span className="font-mono font-medium text-foreground">{msg.executionResult.matched_rule}</span>
                          </div>
                        )}
                        {msg.executionResult.reason && (
                          <div className="text-muted-foreground mt-1 border-t border-border/20 pt-1">
                            <span className="font-semibold text-foreground">Intercept Reason: </span>
                            {msg.executionResult.reason}
                          </div>
                        )}
                      </div>
                      
                      <div className="text-[10px] text-primary/80 font-medium flex items-center justify-end gap-1 select-none">
                        Click to view Aegis verification details &rarr;
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {chatMutation.isPending && (
              <div className="flex gap-3 max-w-[85%] mr-auto items-center">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-muted border-border text-muted-foreground animate-spin">
                  <Loader2 className="h-4 w-4" />
                </div>
                <div className="rounded-lg px-4 py-2 text-sm bg-muted text-muted-foreground italic flex items-center gap-2">
                  Analyzing and executing instructions safely...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSend} className="p-4 border-t border-border/40 flex items-center gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. Delete 5 records from database..."
              disabled={chatMutation.isPending}
              className="flex-1"
            />
            <Button type="submit" disabled={chatMutation.isPending || !input.trim()}>
              {chatMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </form>
        </Card>

        {/* Verification / Intercept Detail Panel */}
        <Card className="lg:col-span-5 flex flex-col h-full overflow-hidden border-border bg-card">
          <CardHeader className="border-b border-border/40 pb-4">
            <CardTitle className="text-base flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              Aegis Verification Details
            </CardTitle>
            <CardDescription>
              Security assessment and explanation of the evaluated tool execution.
            </CardDescription>
          </CardHeader>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {activeExecution ? (
              <div className="space-y-4">
                {/* Header info */}
                <div className="flex items-center justify-between border-b border-border/40 pb-3">
                  <div>
                    <h4 className="text-sm font-semibold capitalize flex items-center gap-1.5 text-foreground">
                      {getToolIcon(activeExecution.toolCall.tool)}
                      {activeExecution.toolCall.tool} {activeExecution.toolCall.action}
                    </h4>
                    <span className="text-[10px] text-muted-foreground font-mono">
                      Rule: {activeExecution.executionResult.matched_rule || "None"}
                    </span>
                  </div>
                  {getDecisionBadge(activeExecution.executionResult.decision)}
                </div>

                {/* Parameters parsed */}
                <div className="space-y-1.5">
                  <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Extracted Request Arguments</h5>
                  <pre className="text-xs bg-muted/60 p-2.5 rounded border border-border/40 font-mono overflow-x-auto text-foreground">
                    {JSON.stringify(
                      Object.keys(activeExecution.toolCall)
                        .filter((k) => k !== "tool" && k !== "action" && activeExecution.toolCall[k] !== null)
                        .reduce((obj, key) => {
                          obj[key] = activeExecution.toolCall[key];
                          return obj;
                        }, {}),
                      null,
                      2
                    )}
                  </pre>
                </div>

                {/* Verification result */}
                <div className="space-y-1.5">
                  <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Aegis Intercept</h5>
                  <div
                    className={`rounded-lg border p-3 text-sm flex gap-3 items-start ${
                      activeExecution.executionResult.decision === "block"
                        ? "border-destructive/30 bg-destructive/5 text-destructive-foreground"
                        : activeExecution.executionResult.decision === "require_hitl"
                        ? "border-amber-500/30 bg-amber-500/5 text-amber-500"
                        : "border-emerald-500/30 bg-emerald-500/5 text-emerald-500"
                    }`}
                  >
                    {activeExecution.executionResult.decision === "block" ? (
                      <ShieldAlert className="h-5 w-5 shrink-0 mt-0.5" />
                    ) : activeExecution.executionResult.decision === "require_hitl" ? (
                      <Clock className="h-5 w-5 shrink-0 mt-0.5" />
                    ) : (
                      <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <p className="font-semibold text-foreground">
                        {activeExecution.executionResult.decision === "block"
                          ? "Blocked by Policy Engine"
                          : activeExecution.executionResult.decision === "require_hitl"
                          ? "Pending Approval"
                          : "Execution Allowed"}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {activeExecution.executionResult.reason || "Action evaluated safe under present policies."}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Output (if executed) */}
                {activeExecution.executionResult.tool_output && (
                  <div className="space-y-1.5">
                    <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Execution Output</h5>
                    <pre className="text-xs bg-muted/60 p-2.5 rounded border border-border/40 font-mono overflow-x-auto text-foreground">
                      {JSON.stringify(activeExecution.executionResult.tool_output, null, 2)}
                    </pre>
                  </div>
                )}

                {/* AI Explanation */}
                {activeExecution.explanation && (
                  <div className="space-y-1.5 border-t border-border/40 pt-4">
                    <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-primary" />
                      AI Decision Explanation
                    </h5>
                    <div className="text-sm bg-muted/40 p-3 rounded-lg border leading-relaxed text-foreground">
                      {activeExecution.explanation}
                    </div>
                  </div>
                )}

                {/* Recommendations */}
                {activeExecution.recommendations && activeExecution.recommendations.length > 0 && (
                  <div className="space-y-1.5">
                    <h5 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                      Security Recommendations
                    </h5>
                    <ul className="text-xs bg-muted/40 p-3 rounded-lg border space-y-1.5 list-inside list-disc text-foreground">
                      {activeExecution.recommendations.map((rec, idx) => (
                        <li key={idx}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-center text-muted-foreground space-y-2">
                <Shield className="h-8 w-8 text-muted-foreground/40" />
                <p className="text-sm font-medium">No Active Execution Loaded</p>
                <p className="text-xs text-muted-foreground/60 max-w-xs">
                  Issue a tool instruction to see live Aegis security intercepts and explanations here.
                </p>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
