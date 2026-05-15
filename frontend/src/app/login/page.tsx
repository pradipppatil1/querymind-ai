"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Database, Lock, User, Loader2 } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: any) {
      setError(err.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-primary/10 via-background to-background px-4">
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 pointer-events-none"></div>
      
      <Card className="w-full max-w-md border-primary/20 shadow-2xl shadow-primary/10 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary/50 via-primary to-primary/50"></div>
        
        <CardHeader className="space-y-2 text-center pb-8 pt-10">
          <div className="mx-auto w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center mb-4 ring-1 ring-primary/20">
            <Database className="w-7 h-7 text-primary" />
          </div>
          <CardTitle className="text-3xl font-bold tracking-tight">Welcome Back</CardTitle>
          <CardDescription className="text-base">
            Enter your credentials to access <span className="font-bold text-foreground">QueryMind AI</span>
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Username</Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input 
                    id="username" 
                    placeholder="john" 
                    className="pl-10 h-11 bg-muted/30"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input 
                    id="password" 
                    type="password" 
                    placeholder="••••••••"
                    className="pl-10 h-11 bg-muted/30"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium animate-in fade-in zoom-in duration-200">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full h-11 text-base font-semibold transition-all hover:scale-[1.01]" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Authenticating...
                </>
              ) : (
                "Sign In"
              )}
            </Button>
          </form>
          
          <div className="mt-8 pt-6 border-t border-border/50 text-center">
            <p className="text-sm text-muted-foreground">
              Restricted access. Please contact your system administrator for account issues.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
