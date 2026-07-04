"use client";

import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarImage, AvatarFallback } from "@/components/ui/avatar";
import { GitHubIcon } from "@/components/shared/github-icon";
import { signInWithGitHub } from "@/lib/auth-client";
import { Bot, Menu, X, LogOut, LayoutDashboard } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useState } from "react";

export function Navbar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { data: session, status } = useSession();
  const isAuthenticated = status === "authenticated";

  return (
    <motion.nav
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="fixed top-0 left-0 right-0 z-50"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group">
            <div className="gradient-brand rounded-lg p-1.5">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <span className="text-lg font-bold tracking-tight">
              Agent<span className="gradient-text">Commit</span>
            </span>
          </Link>

          {/* Desktop nav links */}
          <div className="hidden md:flex items-center gap-6">
            {isAuthenticated && (
              <Link
                href="/dashboard"
                className="text-sm text-muted-foreground hover:text-foreground transition-colors flex items-center gap-1.5"
              >
                <LayoutDashboard className="h-3.5 w-3.5" />
                Dashboard
              </Link>
            )}
            <Link
              href="#features"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Features
            </Link>
            <Link
              href="#architecture"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Architecture
            </Link>

            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                <Link href="/dashboard">
                  <Avatar className="h-8 w-8 border-2 border-primary/30 hover:border-primary transition-colors cursor-pointer">
                    <AvatarImage src={session.user?.image ?? ""} alt={session.user?.name ?? ""} />
                    <AvatarFallback className="text-xs">
                      {session.user?.name?.charAt(0)?.toUpperCase() ?? "U"}
                    </AvatarFallback>
                  </Avatar>
                </Link>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => signOut({ callbackUrl: "/" })}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <Button
                size="sm"
                className="gradient-brand border-0 text-white hover:opacity-90"
                onClick={() => {
                  void signInWithGitHub();
                }}
              >
                <GitHubIcon className="mr-2 h-4 w-4" />
                Sign in with GitHub
              </Button>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            className="md:hidden p-2"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="md:hidden bg-background/80 backdrop-blur-sm border-b border-border/50 overflow-hidden"
          >
            <div className="px-4 py-4 space-y-3">
              {isAuthenticated && (
                <Link
                  href="/dashboard"
                  className="block text-sm text-muted-foreground"
                  onClick={() => setMobileOpen(false)}
                >
                  Dashboard
                </Link>
              )}
              <Link
                href="#features"
                className="block text-sm text-muted-foreground"
                onClick={() => setMobileOpen(false)}
              >
                Features
              </Link>
              <Link
                href="#architecture"
                className="block text-sm text-muted-foreground"
                onClick={() => setMobileOpen(false)}
              >
                Architecture
              </Link>
              {isAuthenticated ? (
                <div className="flex items-center gap-3 pt-2 border-t border-border/50">
                  <Avatar className="h-8 w-8">
                    <AvatarImage src={session.user?.image ?? ""} />
                    <AvatarFallback>{session.user?.name?.charAt(0) ?? "U"}</AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium flex-1">{session.user?.name}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => signOut({ callbackUrl: "/" })}
                  >
                    <LogOut className="h-4 w-4" />
                  </Button>
                </div>
              ) : (
                <Button
                  size="sm"
                  className="w-full gradient-brand border-0 text-white"
                  onClick={() => {
                    void signInWithGitHub();
                  }}
                >
                  <GitHubIcon className="mr-2 h-4 w-4" />
                  Sign in with GitHub
                </Button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.nav>
  );
}
