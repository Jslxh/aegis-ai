import { useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { ShieldCheck, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { api, getErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";

export default function Login() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();
  const { 
    register: registerForgot, 
    handleSubmit: handleSubmitForgot, 
    formState: { errors: errorsForgot, isSubmitting: isSubmittingForgot },
    reset: resetForgot
  } = useForm();

  const [mode, setMode] = useState("login"); // "login" or "forgot"
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [error, setError] = useState(null);

  const from = location.state?.from?.pathname || "/";

  if (!loading && user) {
    return <Navigate to={from} replace />;
  }

  async function onSubmit(values) {
    try {
      await login(values.username, values.password);
      toast.success("Signed in successfully");
      navigate(from, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, "Invalid username or password"));
    }
  }

  async function onForgotSubmit(values) {
    try {
      setError(null);
      await api.post("/auth/forgot-password", { identity: values.identity });
      setForgotSuccess(true);
      toast.success("Password reset link requested");
      resetForgot();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to send reset link"));
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_right,hsl(var(--primary)/0.15),transparent_50%),radial-gradient(ellipse_at_bottom_left,hsl(var(--primary)/0.08),transparent_50%)]" />
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-md"
      >
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
            <ShieldCheck className="h-6 w-6 text-primary-foreground" />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">Aegis AI</h1>
          <p className="text-sm text-muted-foreground">
            Enterprise AI Runtime Governance Platform
          </p>
        </div>

        {mode === "login" ? (
          <Card>
            <CardHeader>
              <CardTitle>Sign in</CardTitle>
              <CardDescription>Use your platform credentials to access the console.</CardDescription>
            </CardHeader>
            <CardContent>
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertTitle>Authentication failed</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    placeholder="admin"
                    autoComplete="username"
                    {...register("username", { required: "Username is required" })}
                  />
                  {errors.username && (
                    <p className="text-xs text-destructive">{errors.username.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="password">Password</Label>
                    <button
                      type="button"
                      onClick={() => { setMode("forgot"); setError(null); setForgotSuccess(false); }}
                      className="text-xs font-medium text-primary hover:underline"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    autoComplete="current-password"
                    {...register("password", { required: "Password is required" })}
                  />
                  {errors.password && (
                    <p className="text-xs text-destructive">{errors.password.message}</p>
                  )}
                </div>
                <Button type="submit" className="w-full" disabled={isSubmitting}>
                  {isSubmitting && <Loader2 className="animate-spin mr-2" />}
                  Sign in
                </Button>
              </form>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle>Forgot password?</CardTitle>
              <CardDescription>
                Enter your username or email address and we'll send you a link to reset your password.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {error && (
                <Alert variant="destructive" className="mb-4">
                  <AlertTitle>Request failed</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              
              {forgotSuccess ? (
                <div className="space-y-4 text-center">
                  <div className="rounded-lg bg-success/15 p-4 text-sm text-success">
                    <p className="font-semibold">Reset Link Generated</p>
                    <p className="mt-1">
                      If an account exists for that identity, the reset instructions have been logged/sent.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={() => { setMode("login"); setError(null); setForgotSuccess(false); }}
                  >
                    Back to Sign In
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleSubmitForgot(onForgotSubmit)} className="space-y-4" noValidate>
                  <div className="space-y-2">
                    <Label htmlFor="identity">Username or Email</Label>
                    <Input
                      id="identity"
                      placeholder="admin or admin@example.com"
                      {...registerForgot("identity", { required: "Username or email is required" })}
                    />
                    {errorsForgot.identity && (
                      <p className="text-xs text-destructive">{errorsForgot.identity.message}</p>
                    )}
                  </div>
                  <Button type="submit" className="w-full" disabled={isSubmittingForgot}>
                    {isSubmittingForgot && <Loader2 className="animate-spin mr-2" />}
                    Send reset link
                  </Button>
                  <div className="text-center">
                    <button
                      type="button"
                      onClick={() => { setMode("login"); setError(null); }}
                      className="text-xs font-medium text-primary hover:underline"
                    >
                      Back to Sign In
                    </button>
                  </div>
                </form>
              )}
            </CardContent>
          </Card>
        )}
      </motion.div>
    </div>
  );
}
