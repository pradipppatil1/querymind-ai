"use client";

import Link from "next/link";
import { Database, LayoutDashboard, MessageSquare, LogOut, User as UserIcon, Calendar } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from "@/components/ui/dropdown-menu";

export function Navbar() {
  const { user, logout } = useAuth();

  if (!user) return null;

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center justify-between px-4 max-w-7xl mx-auto">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center space-x-2">
            <Database className="h-6 w-6 text-primary" />
            <span className="font-bold">QueryMind AI</span>
          </Link>
          <nav className="flex items-center space-x-6 text-sm font-medium ml-6">
            <Link
              href="/"
              className="flex items-center transition-colors hover:text-foreground/80 text-foreground/60"
            >
              <MessageSquare className="h-4 w-4 mr-2" />
              Query
            </Link>
            {user.role === "ADMIN" && (
              <Link
                href="/admin"
                className="flex items-center transition-colors hover:text-foreground/80 text-foreground/60"
              >
                <LayoutDashboard className="h-4 w-4 mr-2" />
                Admin
              </Link>
            )}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden md:flex flex-col items-end mr-2">
            <span className="text-sm font-medium">{user.username}</span>
            <span className="text-[10px] text-muted-foreground flex items-center">
              <Calendar className="w-3 h-3 mr-1" /> Last login: {formatDate(user.last_login)}
            </span>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger render={<Button variant="ghost" size="icon" className="rounded-full bg-primary/5 hover:bg-primary/10 ring-1 ring-primary/20" />}>
              <UserIcon className="h-5 w-5 text-primary" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <div className="px-2 py-1.5 md:hidden">
                <p className="text-sm font-medium">{user.username}</p>
                <p className="text-[10px] text-muted-foreground">Last login: {formatDate(user.last_login)}</p>
              </div>
              <DropdownMenuItem className="text-destructive focus:text-destructive cursor-pointer" onClick={logout}>
                <LogOut className="mr-2 h-4 w-4" />
                <span>Log out</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
