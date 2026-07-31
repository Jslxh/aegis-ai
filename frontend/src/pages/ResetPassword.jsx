import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { ShieldCheck, Loader2, Key } from "lucide-react";
import { api, getErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm();
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  async function onSubmit(values) {
    if (!token) {
      setError("Reset token is missing. Please request a new link.");
      return;
    }
    try {
      setError(null);
      await api.post("/auth/reset-password", {
        token,
        new_password: values.new_password,
      });
      setSuccess(true);
      toast.success("Password reset successfully");
      setTimeout(() => {
        navigate("/login");
      }, 2000);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to reset password. The link may have expired."));
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

        <Card>
          <CardHeader>
            <CardTitle>Reset Password</CardTitle>
            <CardDescription>Enter your new password below.</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <Alert variant="destructive" className="mb-4">
                <AlertTitle>Reset failed</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {!token && (
              <Alert variant="destructive" className="mb-4">
                <AlertTitle>Invalid Link</AlertTitle>
                <AlertDescription>
                  This password reset link is invalid or expired. Please request a new one from the sign-in page.
                </AlertDescription>
              </Alert>
            )}

            {success ? (
              <div className="space-y-4 text-center">
                <div className="rounded-lg bg-success/15 p-4 text-sm text-success">
                  <p className="font-semibold">Password Reset Successful</p>
                  <p className="mt-1">Redirecting you to the sign-in page...</p>
                </div>
              </div>
            ) : (
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
                <div className="space-y-2">
                  <Label htmlFor="new_password">New Password</Label>
                  <Input
                    id="new_password"
                    type="password"
                    placeholder="Minimum 8 characters"
                    disabled={!token}
                    {...register("new_password", {
                      required: "New password is required",
                      minLength: { value: 8, message: "Password must be at least 8 characters" }
                    })}
                  />
                  {errors.new_password && (
                    <p className="text-xs text-destructive">{errors.new_password.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm_password">Confirm Password</Label>
                  <Input
                    id="confirm_password"
                    type="password"
                    placeholder="••••••••"
                    disabled={!token}
                    {...register("confirm_password", {
                      required: "Please confirm your password",
                      validate: value => value === watch("new_password") || "Passwords do not match"
                    })}
                  />
                  {errors.confirm_password && (
                    <p className="text-xs text-destructive">{errors.confirm_password.message}</p>
                  )}
                </div>
                <Button type="submit" className="w-full" disabled={isSubmitting || !token}>
                  {isSubmitting && <Loader2 className="animate-spin mr-2" />}
                  <Key className="mr-2 h-4 w-4" />
                  Reset Password
                </Button>
                <div className="text-center">
                  <button
                    type="button"
                    onClick={() => navigate("/login")}
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Back to Sign In
                  </button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
