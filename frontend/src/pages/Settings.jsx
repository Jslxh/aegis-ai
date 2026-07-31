import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Settings as SettingsIcon, UserPlus, Moon, Sun, Loader2, Key } from "lucide-react";
import { PageHeader } from "../components/shared/PageHeader.jsx";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Select } from "../components/ui/select";
import { Badge } from "../components/ui/badge";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../hooks/use-theme";
import { api, getErrorMessage } from "../lib/api";
import { ROLE_META } from "../lib/status";

const ROLES = ["viewer", "operator", "auditor", "security_analyst", "admin"];

export default function Settings() {
  const { user, hasRole } = useAuth();
  const { theme, toggleTheme } = useTheme();
  
  // Form for creating users (admin only)
  const { register, handleSubmit, reset, formState: { isSubmitting, errors } } = useForm();
  
  // Form for changing password (any logged-in user)
  const {
    register: registerCP,
    handleSubmit: handleSubmitCP,
    reset: resetCP,
    formState: { isSubmitting: isSubmittingCP, errors: errorsCP },
    watch: watchCP,
  } = useForm();

  async function onCreateUser(values) {
    try {
      await api.post("/auth/register", values);
      toast.success(`User "${values.username}" created`);
      reset();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  }

  async function onChangePassword(values) {
    if (values.new_password !== values.confirm_password) {
      toast.error("New passwords do not match");
      return;
    }
    try {
      await api.post("/auth/change-password", {
        current_password: values.current_password,
        new_password: values.new_password,
      });
      toast.success("Password updated successfully");
      resetCP();
    } catch (err) {
      toast.error(getErrorMessage(err));
    }
  }

  const roleMeta = ROLE_META[user?.role] || { label: user?.role };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Settings"
        description="Manage your account and platform configuration"
        icon={SettingsIcon}
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Account</CardTitle>
            <CardDescription>Your signed-in profile and role.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <Label>Username</Label>
                <Input value={user?.username || ""} readOnly className="mt-1.5" />
              </div>
              <div>
                <Label>Email</Label>
                <Input value={user?.email || ""} readOnly className="mt-1.5" />
              </div>
            </div>
            <div>
              <Label>Role</Label>
              <div className="mt-1.5">
                <Badge variant={roleMeta.variant}>{roleMeta.label}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Appearance</CardTitle>
            <CardDescription>Toggle between light and dark themes.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="flex items-center gap-3">
                {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                <div>
                  <p className="text-sm font-medium">Theme</p>
                  <p className="text-xs text-muted-foreground">Currently {theme}</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={toggleTheme}>
                Switch to {theme === "dark" ? "light" : "dark"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Change Password</CardTitle>
            <CardDescription>Update your account security details.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmitCP(onChangePassword)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="current_password">Current Password</Label>
                <Input
                  id="current_password"
                  type="password"
                  placeholder="••••••••"
                  {...registerCP("current_password", { required: "Current password is required" })}
                />
                {errorsCP.current_password && (
                  <p className="text-xs text-destructive">{errorsCP.current_password.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="new_password">New Password</Label>
                <Input
                  id="new_password"
                  type="password"
                  placeholder="Minimum 8 characters"
                  {...registerCP("new_password", { 
                    required: "New password is required",
                    minLength: { value: 8, message: "New password must be at least 8 characters" }
                  })}
                />
                {errorsCP.new_password && (
                  <p className="text-xs text-destructive">{errorsCP.new_password.message}</p>
                )}
              </div>
              <div className="space-y-2">
                <Label htmlFor="confirm_password">Confirm New Password</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  placeholder="••••••••"
                  {...registerCP("confirm_password", { 
                    required: "Please confirm your new password",
                    validate: value => value === watchCP("new_password") || "Passwords do not match"
                  })}
                />
                {errorsCP.confirm_password && (
                  <p className="text-xs text-destructive">{errorsCP.confirm_password.message}</p>
                )}
              </div>
              <Button type="submit" disabled={isSubmittingCP} className="w-full">
                {isSubmittingCP && <Loader2 className="animate-spin mr-2" />}
                <Key className="mr-2 h-4 w-4" />
                Change Password
              </Button>
            </form>
          </CardContent>
        </Card>

        {hasRole("admin") && (
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>User Management</CardTitle>
              <CardDescription>
                Create platform accounts. Passwords are hashed server-side with bcrypt.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit(onCreateUser)} className="grid gap-4 sm:grid-cols-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    placeholder="j.doe"
                    {...register("username", { required: "Required", minLength: 3 })}
                  />
                  {errors.username && (
                    <p className="text-xs text-destructive">{errors.username.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="j.doe@corp.example"
                    {...register("email", { required: "Required" })}
                  />
                  {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Min 8 characters"
                    {...register("password", { required: "Required", minLength: 8 })}
                  />
                  {errors.password && (
                    <p className="text-xs text-destructive">{errors.password.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="role">Role</Label>
                  <Select id="role" defaultValue="viewer" {...register("role")}>
                    {ROLES.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="sm:col-span-4">
                  <Button type="submit" disabled={isSubmitting}>
                    {isSubmitting && <Loader2 className="animate-spin" />}
                    <UserPlus className="h-4 w-4" />
                    Create user
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
