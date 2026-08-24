"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS: { href: string; label: string }[] = [
  { href: "/", label: "Dashboard" },
  { href: "/players", label: "Giocatori" },
  { href: "/auction/setup", label: "Asta · Setup" },
  { href: "/auction/live", label: "Asta · Live" },
  { href: "/auction/history", label: "Asta · Storico" },
  { href: "/strategy", label: "Strategia" },
  { href: "/budget", label: "Budget" },
  { href: "/squad", label: "Rosa" },
  { href: "/settings/league", label: "Lega" },
  { href: "/settings/data", label: "Dati" },
];

export function Nav() {
  const pathname = usePathname();

  return (
    <nav className="border-b border-border bg-panel">
      <div className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 py-2">
        <span className="mr-4 shrink-0 font-bold tracking-tight text-accent">FantaMazor</span>
        {LINKS.map((link) => {
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`shrink-0 rounded-md px-3 py-1.5 text-sm transition-colors ${
                active ? "bg-panel2 text-white" : "text-muted hover:text-white"
              }`}
            >
              {link.label}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
