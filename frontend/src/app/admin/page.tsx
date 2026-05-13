"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { 
  ShieldAlert, Database, FileText, Settings, History, 
  Save, Users, UserPlus, Mail, Trash2, Loader2,
  Download, Search, CheckCircle2, XCircle, Clock
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

export default function AdminDashboard() {
  const { fetchWithAuth, user, isLoading: authLoading } = useAuth();
  const [schema, setSchema] = useState("");
  const [guardrails, setGuardrails] = useState({ allow_destructive: false, max_limit: 100, allowed_table_prefixes: [] });
  const [config, setConfig] = useState<{llm_provider: string, temperature: number, sql_dialects: string[]}>({ llm_provider: "openai", temperature: 0.0, sql_dialects: ["mysql"] });
  const [availableDialects, setAvailableDialects] = useState<Record<string, string>>({});
  
  // States for examples
  const [question, setQuestion] = useState("");
  const [sql, setSql] = useState("");
  const [examples, setExamples] = useState<{question: string, sql: string}[]>([]);

  // States for User Management
  const [users, setUsers] = useState<any[]>([]);
  const [newUser, setNewUser] = useState({ username: "", email: "", password: "", role: "USER" });
  const [userLoading, setUserLoading] = useState(false);

  // States for Logs
  const [logs, setLogs] = useState<any[]>([]);
  const [logSearch, setLogSearch] = useState("");
  const [exampleSearch, setExampleSearch] = useState("");

  const fetchState = useCallback(async () => {
    try {
      const [sRes, gRes, cRes, eRes, uRes, lRes, dRes] = await Promise.all([
        fetchWithAuth("http://localhost:8000/api/admin/schema"),
        fetchWithAuth("http://localhost:8000/api/admin/guardrails"),
        fetchWithAuth("http://localhost:8000/api/admin/config"),
        fetchWithAuth("http://localhost:8000/api/admin/examples"),
        fetchWithAuth("http://localhost:8000/api/admin/users"),
        fetchWithAuth("http://localhost:8000/api/admin/logs"),
        fetchWithAuth("http://localhost:8000/api/admin/dialects")
      ]);

      const [sData, gData, cData, eData, uData, lData, dData] = await Promise.all([
        sRes.ok ? sRes.json() : {},
        gRes.ok ? gRes.json() : null,
        cRes.ok ? cRes.json() : null,
        eRes.ok ? eRes.json() : {},
        uRes.ok ? uRes.json() : {},
        lRes.ok ? lRes.json() : {},
        dRes.ok ? dRes.json() : {}
      ]);

      setSchema(sData.schema || "");
      if(gData) setGuardrails(gData);
      if(cData) setConfig({ 
        llm_provider: cData.llm_provider || "openai",
        temperature: cData.temperature ?? 0.0,
        sql_dialects: cData.sql_dialects || ["mysql"] 
      });
      if(eData && eData.examples) setExamples(eData.examples);
      if(uData && uData.users) setUsers(uData.users);
      if(lData && lData.logs) setLogs(lData.logs);
      if(dData && dData.dialects) setAvailableDialects(dData.dialects);
    } catch (err) {
      console.error("Failed to fetch admin state", err);
    }
  }, [fetchWithAuth]);

  const hasFetched = useRef(false);

  useEffect(() => {
    if (!authLoading && user && !hasFetched.current) {
      fetchState();
      hasFetched.current = true;
    }
  }, [fetchState, authLoading, user]);

  if (authLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
          <p className="text-sm text-muted-foreground animate-pulse">Checking credentials...</p>
        </div>
      </div>
    );
  }

  const handleSaveGuardrails = async () => {
    await fetchWithAuth("http://localhost:8000/api/admin/guardrails", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(guardrails)
    });
    alert("Guardrails saved!");
  };

  const handleSaveConfig = async () => {
    await fetchWithAuth("http://localhost:8000/api/admin/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config)
    });
    alert("Configuration saved!");
  };

  const handleAddExample = async () => {
    const res = await fetchWithAuth(`http://localhost:8000/api/admin/examples?question=${encodeURIComponent(question)}&sql=${encodeURIComponent(sql)}`, {
      method: "POST"
    });
    
    if (!res.ok) {
      const error = await res.json();
      alert(`Error: ${error.detail || "Failed to add example"}`);
      return;
    }

    alert("Example verified and added successfully!");
    setQuestion("");
    setSql("");
    fetchState();
  };

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setUserLoading(true);
    try {
      const res = await fetchWithAuth("http://localhost:8000/api/admin/users", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newUser)
      });
      if (res.ok) {
        alert("User created and email sent!");
        setNewUser({ username: "", email: "", password: "", role: "USER" });
        fetchState();
      } else {
        const data = await res.json();
        alert(`Error: ${data.detail}`);
      }
    } catch (err) {
      alert("Failed to create user");
    } finally {
      setUserLoading(false);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!confirm("Are you sure? This will delete all user data and history.")) return;
    try {
      const res = await fetchWithAuth(`http://localhost:8000/api/admin/users/${userId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        fetchState();
      }
    } catch (err) {
      alert("Failed to delete user");
    }
  };

  const exportLogs = () => {
    const headers = ["ID", "Timestamp", "User", "Query", "SQL", "Status", "Latency (ms)", "Rows"];
    const csvContent = [
      headers.join(","),
      ...logs.map(l => [
        l.id,
        new Date(l.created_at).toLocaleString(),
        l.username,
        `"${l.nl_input?.replace(/"/g, '""') || ""}"`,
        `"${l.data?.sql?.replace(/"/g, '""') || ""}"`,
        l.data?.error ? "Error" : "Success",
        l.data?.latency_ms ? l.data.latency_ms.toFixed(2) : "N/A",
        l.data?.results?.length || 0
      ].join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `audit_logs_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const filteredLogs = logs.filter(l => 
    l.username?.toLowerCase().includes(logSearch.toLowerCase()) ||
    l.nl_input?.toLowerCase().includes(logSearch.toLowerCase()) ||
    l.data?.sql?.toLowerCase().includes(logSearch.toLowerCase())
  );

  const filteredExamples = examples.filter(ex => 
    ex.question.toLowerCase().includes(exampleSearch.toLowerCase()) ||
    ex.sql.toLowerCase().includes(exampleSearch.toLowerCase())
  );

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Admin Dashboard</h1>
          <p className="text-muted-foreground mt-2 text-lg">Manage users, engine settings, and datasets.</p>
        </div>
      </div>

      <Tabs defaultValue="users" className="w-full">
        <TabsList className="grid w-full grid-cols-6 h-12 mb-8">
          <TabsTrigger value="users" className="flex items-center gap-2"><Users className="w-4 h-4"/> Users</TabsTrigger>
          <TabsTrigger value="schema" className="flex items-center gap-2"><Database className="w-4 h-4"/> Schema</TabsTrigger>
          <TabsTrigger value="examples" className="flex items-center gap-2"><FileText className="w-4 h-4"/> Examples</TabsTrigger>
          <TabsTrigger value="guardrails" className="flex items-center gap-2"><ShieldAlert className="w-4 h-4"/> Guardrails</TabsTrigger>
          <TabsTrigger value="config" className="flex items-center gap-2"><Settings className="w-4 h-4"/> Model Config</TabsTrigger>
          <TabsTrigger value="logs" className="flex items-center gap-2"><History className="w-4 h-4"/> Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="users" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><UserPlus className="w-5 h-5 text-primary"/> Add New User</CardTitle>
                <CardDescription>Create a new account and notify them via email.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleAddUser} className="space-y-4">
                  <div className="space-y-2">
                    <Label>Username</Label>
                    <Input 
                      placeholder="john_doe" 
                      value={newUser.username} 
                      onChange={e => setNewUser({...newUser, username: e.target.value})}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input 
                      type="email" 
                      placeholder="john@example.com" 
                      value={newUser.email}
                      onChange={e => setNewUser({...newUser, email: e.target.value})}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Temporary Password</Label>
                    <Input 
                      type="password" 
                      placeholder="••••••••" 
                      value={newUser.password}
                      onChange={e => setNewUser({...newUser, password: e.target.value})}
                      required
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Role</Label>
                    <Select value={newUser.role} onValueChange={val => setNewUser({...newUser, role: val})}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="USER">User (Query only)</SelectItem>
                        <SelectItem value="ADMIN">Admin (Full Access)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <Button type="submit" className="w-full" disabled={userLoading}>
                    {userLoading ? <Loader2 className="w-4 h-4 animate-spin mr-2"/> : <Mail className="w-4 h-4 mr-2"/>}
                    Create & Send Email
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>System Users</CardTitle>
                <CardDescription>Manage existing users and their roles.</CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>User</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Last Login</TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map(u => (
                      <TableRow key={u.id}>
                        <TableCell className="font-medium">{u.username}</TableCell>
                        <TableCell className="text-muted-foreground">{u.email}</TableCell>
                        <TableCell>
                          <span className={cn(
                            "px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                            u.role === "ADMIN" ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                          )}>
                            {u.role}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs">{u.last_login ? new Date(u.last_login).toLocaleDateString() : "Never"}</TableCell>
                        <TableCell className="text-right">
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => handleDeleteUser(u.id)}
                            disabled={u.username === user?.username}
                          >
                            <Trash2 className="w-4 h-4"/>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="schema">
          <Card>
            <CardHeader>
              <CardTitle>Database Schema Context</CardTitle>
              <CardDescription>Current schema representation loaded into the LLM context.</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea value={schema} readOnly className="min-h-[400px] font-mono text-sm bg-muted/50" />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="examples">
          <Card>
            <CardHeader>
              <CardTitle>Few-Shot Training Data</CardTitle>
              <CardDescription>Add examples to the vector database for improved SQL generation.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Natural Language Question</Label>
                  <Textarea placeholder="Show all patients who paid more than 5000..." value={question} onChange={e => setQuestion(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <Label>Gold Standard SQL</Label>
                  <Textarea className="font-mono" placeholder="SELECT * FROM patients..." value={sql} onChange={e => setSql(e.target.value)} />
                </div>
              </div>
              <Button onClick={handleAddExample} className="gap-2">
                <Save className="w-4 h-4" /> Save to Retriever
              </Button>

              <div className="pt-6 border-t space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold">Existing Examples ({filteredExamples.length})</h3>
                  <div className="relative w-72">
                    <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input 
                      placeholder="Filter examples..." 
                      className="pl-10 h-9" 
                      value={exampleSearch}
                      onChange={(e) => setExampleSearch(e.target.value)}
                    />
                  </div>
                </div>

                <div className="rounded-md border max-h-[400px] overflow-y-auto">
                  <Table>
                    <TableHeader className="sticky top-0 bg-background z-10">
                      <TableRow>
                        <TableHead className="w-[40%]">Question</TableHead>
                        <TableHead>SQL Result</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredExamples.length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={2} className="text-center py-10 text-muted-foreground">
                            No examples found matching your search.
                          </TableCell>
                        </TableRow>
                      ) : (
                        filteredExamples.map((ex, i) => (
                          <TableRow key={i} className="group hover:bg-muted/30">
                            <TableCell className="font-medium text-sm leading-relaxed">{ex.question}</TableCell>
                            <TableCell className="font-mono text-[11px] opacity-70 group-hover:opacity-100 transition-opacity">
                              <code className="bg-muted px-2 py-1 rounded break-all whitespace-pre-wrap block">
                                {ex.sql}
                              </code>
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="guardrails">
          <div className="grid grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Safety & Governance</CardTitle>
                <CardDescription>Configure query restrictions and data limits.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <Label>Allow Destructive Queries (DROP, DELETE)</Label>
                  <Switch checked={guardrails.allow_destructive} onCheckedChange={val => setGuardrails({...guardrails, allow_destructive: val})} />
                </div>
                <div className="space-y-2">
                  <Label>Max Results Limit</Label>
                  <Input type="number" value={guardrails.max_limit} onChange={e => setGuardrails({...guardrails, max_limit: parseInt(e.target.value)})} />
                </div>
                <Button onClick={handleSaveGuardrails} className="gap-2">
                  <Save className="w-4 h-4" /> Save Guardrails
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="config">
          <Card className="max-w-md">
            <CardHeader>
              <CardTitle>Model Hyperparameters</CardTitle>
              <CardDescription>Adjust the generation settings for the SQL engine.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>LLM Provider</Label>
                <Select value={config.llm_provider} onValueChange={val => setConfig({...config, llm_provider: val})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="openai">OpenAI (GPT-4o)</SelectItem>
                    <SelectItem value="google">Google (Gemma-2b)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Temperature ({config.temperature ?? 0})</Label>
                <Input type="range" min="0" max="1" step="0.1" value={config.temperature ?? 0} onChange={e => setConfig({...config, temperature: parseFloat(e.target.value)})} />
              </div>
              
              <div className="space-y-3 pt-4 border-t border-border">
                <div className="flex justify-between items-center">
                  <Label>SQL Output Dialects</Label>
                  <span className="text-[10px] bg-muted px-2 py-0.5 rounded text-muted-foreground">
                    {config.sql_dialects.length - 1}/2 Selected
                  </span>
                </div>
                
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 p-2 rounded border border-primary/20 bg-primary/5 opacity-80 cursor-not-allowed">
                    <input type="checkbox" checked disabled className="rounded border-gray-300 text-primary focus:ring-primary h-4 w-4" />
                    <span className="text-sm font-medium">MySQL (Default / Executed)</span>
                  </label>
                  
                  <div className="grid grid-cols-2 gap-2 mt-2 max-h-[200px] overflow-y-auto pr-2">
                    {Object.entries(availableDialects).map(([key, label]) => {
                      const isChecked = config.sql_dialects.includes(key);
                      const isAtMax = config.sql_dialects.length >= 3;
                      const isDisabled = !isChecked && isAtMax;
                      
                      return (
                        <label 
                          key={key} 
                          className={cn(
                            "flex items-center space-x-2 p-2 rounded border transition-colors",
                            isChecked ? "border-primary bg-primary/10" : "border-border hover:bg-muted/50",
                            isDisabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
                          )}
                          title={isDisabled ? "Max 2 additional dialects allowed" : ""}
                        >
                          <input 
                            type="checkbox" 
                            checked={isChecked}
                            disabled={isDisabled}
                            onChange={(e) => {
                              if (e.target.checked) {
                                if (!isAtMax) {
                                  setConfig({...config, sql_dialects: [...config.sql_dialects, key]});
                                }
                              } else {
                                setConfig({...config, sql_dialects: config.sql_dialects.filter(d => d !== key)});
                              }
                            }}
                            className="rounded border-gray-300 text-primary focus:ring-primary h-4 w-4" 
                          />
                          <span className="text-sm truncate">{label}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>

              <Button onClick={handleSaveConfig} className="gap-2 w-full mt-4">
                <Save className="w-4 h-4" /> Save Config
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>System Audit Logs</CardTitle>
                <CardDescription>Detailed history of user queries and engine performance.</CardDescription>
              </div>
              <Button variant="outline" size="sm" onClick={exportLogs} className="gap-2">
                <Download className="w-4 h-4" /> Export CSV
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input 
                  placeholder="Search by user, query, or SQL..." 
                  className="pl-10" 
                  value={logSearch}
                  onChange={(e) => setLogSearch(e.target.value)}
                />
              </div>

              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/50">
                      <TableHead>Timestamp</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Query</TableHead>
                      <TableHead>Generated SQL</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Performance</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredLogs.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6} className="text-center py-10 text-muted-foreground">
                          No logs found matching your criteria.
                        </TableCell>
                      </TableRow>
                    ) : (
                      filteredLogs.map((log) => (
                        <TableRow key={log.id} className="text-xs">
                          <TableCell className="whitespace-nowrap text-muted-foreground">
                            {new Date(log.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </TableCell>
                          <TableCell className="font-bold">{log.username}</TableCell>
                          <TableCell className="max-w-[150px] truncate" title={log.nl_input}>{log.nl_input}</TableCell>
                          <TableCell className="max-w-[200px]">
                            {log.data?.sql ? (
                              <code className="bg-muted/50 px-2 py-0.5 rounded text-[10px] text-muted-foreground truncate block max-w-[180px] font-mono border border-border/50" title={log.data.sql}>
                                {log.data.sql}
                              </code>
                            ) : (
                              <span className="text-[10px] text-muted-foreground italic opacity-50">No SQL</span>
                            )}
                          </TableCell>
                          <TableCell>
                            {log.data?.error ? (
                              <span className="flex items-center gap-1 text-destructive font-semibold">
                                <XCircle className="w-3.5 h-3.5" /> Error
                              </span>
                            ) : (
                              <span className="flex items-center gap-1 text-primary font-semibold">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Success
                              </span>
                            )}
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-col gap-1">
                              {log.data?.latency_ms ? (
                                <>
                                  <span className="flex items-center gap-1 text-[10px]"><Clock className="w-3 h-3" /> {log.data.latency_ms.toFixed(1)}ms</span>
                                  <span className="text-[10px] text-muted-foreground">{log.data.results?.length || 0} rows returned</span>
                                </>
                              ) : (
                                <span className="text-[10px] text-muted-foreground italic">N/A</span>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
