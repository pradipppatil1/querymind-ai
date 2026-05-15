"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Mic, Send, Bot, User, Code, Info, AlertTriangle,
  Plus, Trash2, MessageSquare, ChevronLeft, ChevronRight,
  Loader2, History, Database, Copy, Check
} from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, LineChart, Line } from "recharts";
import { useAuth } from "@/context/AuthContext";
import { PasswordResetModal } from "@/components/PasswordResetModal";
import { cn } from "@/lib/utils";

type Message = {
  role: "user" | "assistant";
  content: string;
  data?: any;
  error?: string;
};

type Session = {
  id: string;
  title: string;
  created_at: string;
};

export default function Home() {
  const { fetchWithAuth, user, isLoading: authLoading } = useAuth();
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const getChartConfig = (results: any[]) => {
    if (!results || results.length === 0) return null;
    const keys = Object.keys(results[0]);
    
    // STRICT CONSTRAINT: Result set must have <= 2 columns
    if (keys.length === 0 || keys.length > 2) return null;

    const isNumeric = (val: any) => {
      if (typeof val === 'number') return true;
      if (typeof val === 'string' && val.trim() !== '') {
        return !isNaN(Number(val));
      }
      return false;
    };

    // Identify which key is the "measure" (value) and which is the "dimension" (category)
    const numKeys = keys.filter(k => isNumeric(results[0][k]));
    const categoricalKeys = keys.filter(k => !isNumeric(results[0][k]));

    let numericKey = "";
    let categoryKey = "";

    if (numKeys.length === 0) return null;

    if (numKeys.length === 1) {
      numericKey = numKeys[0];
      categoryKey = categoricalKeys.length > 0 ? categoricalKeys[0] : (keys.find(k => k !== numericKey) || keys[0]);
    } else {
      // If both are numbers (e.g., year and total_revenue), we need smarter heuristics
      const valueKeywords = ['amount', 'total', 'billed', 'price', 'count', 'sum', 'avg', 'revenue', 'cost', 'rate', 'value'];
      const categoryKeywords = ['id', 'month', 'year', 'day', 'quarter', 'code', 'zip', 'age'];
      
      const vKey = numKeys.find(k => valueKeywords.some(kw => k.toLowerCase().includes(kw)));
      const cKey = numKeys.find(k => categoryKeywords.some(kw => k.toLowerCase().includes(kw)));
      
      if (vKey && cKey && vKey !== cKey) {
        numericKey = vKey;
        categoryKey = cKey;
      } else if (vKey) {
        numericKey = vKey;
        categoryKey = numKeys.find(k => k !== vKey) || keys[0];
      } else {
        // Fallback: pick the last numeric key as value (often sum/count), first as category
        numericKey = numKeys[numKeys.length - 1];
        categoryKey = numKeys[0];
      }
    }

    if (!numericKey || !categoryKey || numericKey === categoryKey) return null;
    
    // Detect if the category key looks like a date/time
    const firstVal = results[0][categoryKey];
    const isDateLike = (typeof firstVal === 'string' || typeof firstVal === 'number') && (
      !isNaN(Date.parse(String(firstVal))) || 
      /^\d{4}$/.test(String(firstVal)) ||
      /^\d{4}-\d{2}/.test(String(firstVal)) || 
      /^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/i.test(String(firstVal))
    );

    // Prefer Bar chart for small datasets (<= 10) even if it's "date-like" (like years)
    // Use Line chart for larger datasets or more granular dates
    const type = (isDateLike && results.length > 10) ? 'line' : 'bar';

    return {
      type: type,
      xKey: categoryKey,
      yKey: numericKey
    };
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await fetchWithAuth("http://localhost:8000/api/chat/sessions");
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions);
      }
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    }
  }, [fetchWithAuth]);

  useEffect(() => {
    if (user) {
      fetchSessions();
    }
  }, [user, fetchSessions]);

  const loadSession = async (sessionId: string) => {
    setIsLoading(true);
    setCurrentSessionId(sessionId);
    try {
      const res = await fetchWithAuth(`http://localhost:8000/api/chat/sessions/${sessionId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages);
      }
    } catch (err) {
      console.error("Failed to load session", err);
    } finally {
      setIsLoading(false);
    }
  };

  const createNewChat = () => {
    setCurrentSessionId(null);
    setMessages([
      { role: "assistant", content: "Hello! I am your Text-to-SQL Analytics Assistant. How can I help you explore the Hospital Billing database today?" }
    ]);
  };

  const deleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this chat?")) return;

    try {
      const res = await fetchWithAuth(`http://localhost:8000/api/chat/sessions/${sessionId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setSessions(prev => prev.filter(s => s.id !== sessionId));
        if (currentSessionId === sessionId) {
          createNewChat();
        }
      }
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  const toggleRecording = () => {
    const win = window as any;
    const SpeechRecognition = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    // Protection against rapid clicking
    if (isRecording) {
      setIsRecording(false);
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          console.error("Error stopping recognition", e);
        }
      }
    } else {
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;

      recognition.lang = 'en-US';
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsRecording(true);
      };

      recognition.onresult = (event: any) => {
        const speechResult = event.results[0][0].transcript;
        setQuery(speechResult);
        setIsRecording(false);
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error", event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognition.start();
    }
  };

  const handleSubmit = async () => {
    if (!query.trim() || isLoading) return;

    const userMessage = query.trim();
    setQuery("");
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    try {
      const res = await fetchWithAuth("http://localhost:8000/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: userMessage,
          history: messages.map(m => ({ role: m.role, content: m.content })),
          session_id: currentSessionId
        }),
      });

      const data = await res.json();

      if (data.error) {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: data.error,
          error: data.error,
          data: data.data
        }]);
      } else if (data.clarification_needed) {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: data.message,
          data: data
        }]);
      } else {
        const answer = data.data.summary;
        setMessages(prev => [...prev, {
          role: "assistant",
          content: answer,
          data: data.data
        }]);
      }

      // Update session ID if it was a new session (even on error/unsupported)
      if (!currentSessionId && data.session_id) {
        setCurrentSessionId(data.session_id);
        fetchSessions();
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Sorry, I couldn't connect to the server."
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 rounded-full border-4 border-primary border-t-transparent animate-spin"></div>
          <p className="text-sm text-muted-foreground animate-pulse">Initializing session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 overflow-hidden h-[calc(100vh-3.5rem)] relative">
      <PasswordResetModal open={!!user?.password_reset_required} />

      {/* Sidebar */}
      <aside
        className={cn(
          "bg-muted/30 border-r transition-all duration-300 flex flex-col z-20",
          sidebarOpen ? "w-64" : "w-0 overflow-hidden border-none"
        )}
      >
        <div className="p-4 border-b bg-background/50">
          <Button onClick={createNewChat} className="w-full justify-start gap-2 h-10 shadow-sm" variant="outline">
            <Plus className="w-4 h-4" /> New Chat
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessions.length === 0 ? (
            <div className="text-center py-8 px-4">
              <History className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-xs text-muted-foreground">No history yet</p>
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => loadSession(session.id)}
                className={cn(
                  "group flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all hover:bg-accent/50",
                  currentSessionId === session.id ? "bg-accent shadow-sm" : "text-muted-foreground"
                )}
              >
                <MessageSquare className="w-4 h-4 shrink-0" />
                <span className="text-sm truncate flex-1 font-medium">{session.title}</span>
                <button
                  onClick={(e) => deleteSession(e, session.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 hover:text-destructive rounded transition-all"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="p-4 border-t text-[10px] text-muted-foreground bg-background/50">
          <p>© 2026 QueryMind AI</p>
        </div>
      </aside>

      {/* Sidebar Toggle Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className={cn(
          "absolute top-1/2 -translate-y-1/2 z-30 p-1 bg-background border rounded-full shadow-md hover:bg-accent transition-all",
          sidebarOpen ? "left-[250px]" : "left-4"
        )}
      >
        {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
      </button>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col relative bg-background overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-2">
                  <Database className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-2xl font-bold tracking-tight">Ready to query?</h2>
                <p className="text-muted-foreground max-w-sm">
                  Ask me about patient demographics, billing amounts, or insurance providers in the hospital system.
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <div key={index} className={cn(
                "flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300",
                message.role === "user" ? "justify-end" : "justify-start"
              )}>
                {message.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0 border border-primary/20">
                    <Bot className="w-5 h-5 text-primary" />
                  </div>
                )}

                <div className={cn(
                  "max-w-[85%] space-y-2",
                  message.role === "user" ? "items-end" : "items-start"
                )}>
                  <div className={cn(
                    "p-4 rounded-2xl shadow-sm",
                    message.role === "user"
                      ? "bg-primary text-primary-foreground rounded-tr-none"
                      : "bg-muted/50 border border-border/50 rounded-tl-none"
                  )}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>

                    {message.data?.explanation && (
                      <div className="mt-3 p-4 bg-primary/5 border border-primary/10 rounded-xl space-y-3">
                        <p className="text-sm text-foreground/90 italic leading-relaxed">
                          {message.data.explanation}
                        </p>
                        <div className="flex justify-end pt-1 border-t border-primary/10">
                          <Dialog>
                            <DialogTrigger render={<Button variant="ghost" size="sm" className="h-7 text-[10px] font-bold text-primary hover:bg-primary/10 gap-1.5 px-2 bg-primary/5 border border-primary/20" />}>
                              <Code className="w-3.5 h-3.5" /> VIEW GENERATED SQL
                            </DialogTrigger>
                            <DialogContent className="sm:max-w-[700px] font-mono border-primary/20 shadow-2xl">
                              <DialogHeader>
                                <DialogTitle className="flex items-center gap-2 text-primary">
                                  <Code className="w-5 h-5" /> Optimized SQL Query
                                </DialogTitle>
                              </DialogHeader>

                              {message.data.sql_dialect_versions ? (
                                <Tabs defaultValue="mysql" className="mt-4">
                                  <TabsList className="mb-2 w-full justify-start overflow-x-auto bg-muted/50 p-1 border border-border/50">
                                    {Object.keys(message.data.sql_dialect_versions).map((dialect) => (
                                      <TabsTrigger
                                        key={dialect}
                                        value={dialect}
                                        className="text-xs data-[state=active]:bg-primary/10 data-[state=active]:text-primary"
                                      >
                                        {dialect === "mysql" ? "MySQL" : dialect.charAt(0).toUpperCase() + dialect.slice(1)}
                                        {dialect === "mysql" && " ✓"}
                                      </TabsTrigger>
                                    ))}
                                  </TabsList>
                                  {Object.entries(message.data.sql_dialect_versions).map(([dialect, sqlStr]) => (
                                    <TabsContent key={dialect} value={dialect} className="mt-0 outline-none">
                                      <div className="relative group">
                                        <div className="p-5 bg-slate-950 text-emerald-400 rounded-xl text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap break-all shadow-inner border border-white/10 ring-1 ring-white/5">
                                          {sqlStr as string}
                                        </div>
                                        <Button
                                          variant="ghost"
                                          size="icon"
                                          className="absolute top-2 right-2 bg-slate-800 hover:bg-slate-700 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 rounded-lg"
                                          onClick={() => navigator.clipboard.writeText(sqlStr as string)}
                                          title="Copy SQL"
                                        >
                                          <Copy className="h-4 w-4" />
                                        </Button>
                                      </div>
                                    </TabsContent>
                                  ))}
                                  <p className="text-[10px] text-muted-foreground mt-3 italic flex items-center gap-1.5 opacity-80">
                                    <Info className="w-3 h-3" /> MySQL is always executed against your data. Other dialects are transpiled for reference only.
                                  </p>
                                </Tabs>
                              ) : (
                                <div className="relative group mt-4">
                                  <div className="p-5 bg-slate-950 text-emerald-400 rounded-xl text-xs leading-relaxed overflow-x-auto whitespace-pre-wrap break-all shadow-inner border border-white/10 ring-1 ring-white/5">
                                    {message.data.sql}
                                  </div>
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    className="absolute top-2 right-2 bg-slate-800 hover:bg-slate-700 text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity h-8 w-8 rounded-lg"
                                    onClick={() => navigator.clipboard.writeText(message.data.sql)}
                                    title="Copy SQL"
                                  >
                                    <Copy className="h-4 w-4" />
                                  </Button>
                                </div>
                              )}
                            </DialogContent>
                          </Dialog>
                        </div>
                      </div>
                    )}

                    {message.error && (
                      <div className="mt-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive text-xs font-mono">
                        {message.error}
                      </div>
                    )}
                  </div>

                  {message.data && message.data.results && (
                    <div className="mt-4 space-y-4 animate-in zoom-in-95 duration-500">
                      {/* Data Table */}

                      <div className={cn("grid gap-4", getChartConfig(message.data.results) ? "grid-cols-1 lg:grid-cols-3" : "grid-cols-1")}>
                        {/* Data Table */}
                        <Card className={cn("border-none shadow-md overflow-hidden bg-muted/30", getChartConfig(message.data.results) ? "lg:col-span-2" : "col-span-1")}>
                          <CardHeader className="py-3 px-4 border-b bg-muted/50">
                            <CardTitle className="text-xs font-bold flex items-center gap-2">
                              <Database className="w-3.5 h-3.5" /> Result Set
                            </CardTitle>
                          </CardHeader>
                          <CardContent className="p-0">
                            <div className="overflow-x-auto max-h-[400px]">
                              <Table>
                                <TableHeader className="bg-muted/30 sticky top-0 z-10">
                                  <TableRow>
                                    {Object.keys(message.data.results[0] || {}).map((key) => (
                                      <TableHead key={key} className="h-9 text-[10px] font-bold">{key}</TableHead>
                                    ))}
                                  </TableRow>
                                </TableHeader>
                                <TableBody>
                                  {message.data.results.map((row: any, i: number) => (
                                    <TableRow key={i} className="hover:bg-muted/50 transition-colors">
                                      {Object.values(row).map((val: any, j) => (
                                        <TableCell key={j} className="py-2 text-[11px] font-medium">{String(val)}</TableCell>
                                      ))}
                                    </TableRow>
                                  ))}
                                </TableBody>
                              </Table>
                            </div>
                          </CardContent>
                        </Card>

                        {getChartConfig(message.data.results) && (() => {
                          const config = getChartConfig(message.data.results)!;
                          const chartData = message.data.results.slice(0, 30).map((r: any) => ({
                            ...r,
                            [config.yKey]: Number(r[config.yKey])
                          }));
                          
                          return (
                            <div className="space-y-4">
                              <Card className="bg-muted/30 border-none shadow-sm h-[250px]">
                                <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
                                  <CardTitle className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                                    {config.type === 'line' ? 'Trend' : 'Comparison'}
                                  </CardTitle>
                                  {config.type === 'line' ? (
                                    <LineChart className="w-4 h-4 text-primary opacity-40" />
                                  ) : (
                                    <BarChart className="w-4 h-4 text-primary opacity-40" />
                                  )}
                                </CardHeader>
                                <CardContent className="p-2 h-[180px] w-full">
                                  <ResponsiveContainer width="100%" height="100%">
                                    {config.type === 'line' ? (
                                      <LineChart data={chartData}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" opacity={0.1} />
                                        <XAxis 
                                          dataKey={config.xKey} 
                                          fontSize={10} 
                                          axisLine={false} 
                                          tickLine={false} 
                                        />
                                        <YAxis fontSize={10} axisLine={false} tickLine={false} />
                                        <RechartsTooltip 
                                          cursor={{ strokeOpacity: 0.2 }}
                                          contentStyle={{ 
                                            backgroundColor: 'var(--background)', 
                                            borderRadius: '8px', 
                                            border: '1px solid var(--border)', 
                                            fontSize: '12px',
                                            color: 'var(--foreground)'
                                          }}
                                          itemStyle={{ color: 'var(--primary)' }}
                                        />
                                        <Line 
                                          type="monotone" 
                                          dataKey={config.yKey} 
                                          stroke="var(--primary)" 
                                          strokeWidth={2} 
                                          dot={{ fill: 'var(--primary)', r: 3 }} 
                                          activeDot={{ r: 5 }} 
                                        />
                                      </LineChart>
                                    ) : (
                                      <BarChart data={chartData}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" opacity={0.1} />
                                        <XAxis 
                                          dataKey={config.xKey} 
                                          fontSize={10} 
                                          axisLine={false} 
                                          tickLine={false} 
                                        />
                                        <YAxis fontSize={10} axisLine={false} tickLine={false} />
                                        <RechartsTooltip 
                                          cursor={{ fill: 'currentColor', fillOpacity: 0.05 }}
                                          contentStyle={{ 
                                            backgroundColor: 'var(--background)', 
                                            borderRadius: '8px', 
                                            border: '1px solid var(--border)', 
                                            fontSize: '12px',
                                            color: 'var(--foreground)'
                                          }}
                                          itemStyle={{ color: 'var(--primary)' }}
                                        />
                                        <Bar 
                                          dataKey={config.yKey} 
                                          fill="var(--primary)" 
                                          radius={[4, 4, 0, 0]} 
                                        />
                                      </BarChart>
                                    )}
                                  </ResponsiveContainer>
                                </CardContent>
                              </Card>

                            <Card className="bg-muted/30 border-none shadow-sm flex flex-col h-[135px]">
                              <CardHeader className="py-2 px-4">
                                <CardTitle className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Performance</CardTitle>
                              </CardHeader>
                              <CardContent className="flex-1 flex flex-col justify-center space-y-2 px-4 pb-4">
                                <div className="flex items-center justify-between">
                                  <span className="text-[10px] text-muted-foreground flex items-center gap-1"><Info className="w-3 h-3" /> Execution</span>
                                  <span className="text-xs font-bold font-mono">{message.data.latency_ms?.toFixed(2) || "0"}ms</span>
                                </div>
                                <div className="w-full bg-muted h-1 rounded-full overflow-hidden">
                                  <div className="bg-primary h-full transition-all duration-500" style={{ width: `${Math.min(100, (message.data.latency_ms || 0) / 2)}%` }}></div>
                                </div>
                              </CardContent>
                            </Card>
                          </div>
                        )})()}
                      </div>
                    </div>
                  )}
                </div>

                {message.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0 shadow-lg ring-2 ring-primary/20">
                    <User className="w-5 h-5 text-primary-foreground" />
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex gap-4 animate-pulse">
                <div className="w-8 h-8 rounded-full bg-muted shrink-0" />
                <div className="max-w-[70%] space-y-2">
                  <div className="h-4 bg-muted rounded w-32" />
                  <div className="h-20 bg-muted rounded-2xl w-96" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="p-4 md:p-6 border-t bg-background/50 backdrop-blur-sm z-10">
          <div className="max-w-4xl mx-auto relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 via-primary/10 to-primary/20 rounded-2xl blur opacity-25 group-focus-within:opacity-100 transition duration-1000"></div>
            <div className="relative">
              <Textarea
                placeholder="Ask about patient billing, demographics, or analysis..."
                className="min-h-[60px] max-h-[200px] w-full pr-24 py-4 px-5 rounded-xl border-border bg-background shadow-xl focus-visible:ring-primary/20 resize-none"
                value={query}
                disabled={isLoading}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
              />
              <div className="absolute right-3 bottom-3 flex gap-2">
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={toggleRecording}
                  className={cn(
                    "h-9 w-9 rounded-lg transition-all",
                    isRecording ? "text-destructive bg-destructive/10 animate-pulse" : "text-muted-foreground hover:text-primary"
                  )}
                >
                  <Mic className="h-5 w-5" />
                </Button>
                <Button
                  size="icon"
                  onClick={handleSubmit}
                  disabled={isLoading || !query.trim()}
                  className="h-9 w-9 rounded-lg shadow-lg hover:scale-105 transition-transform"
                >
                  <Send className="h-5 w-5" />
                </Button>
              </div>
            </div>
          </div>
          <p className="text-[10px] text-center mt-3 text-muted-foreground">
            Press <kbd className="px-1.5 py-0.5 rounded bg-muted border">Enter</kbd> to send • AI can make mistakes, verify results.
          </p>
        </div>
      </main>
    </div>
  );
}
