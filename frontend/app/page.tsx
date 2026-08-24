"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { DataSourceStatus, LeagueSettings } from "@/lib/types";

export default function DashboardPage() {
  const { data: settings } = useQuery({
    queryKey: ["league-settings"],
    queryFn: () => api.get<LeagueSettings>("/api/league/settings"),
  });
  const { data: sources } = useQuery({
    queryKey: ["data-status"],
    queryFn: () => api.get<DataSourceStatus[]>("/api/data/status"),
  });

  const config = settings?.config;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-sm text-muted">
          {settings ? settings.name : "Caricamento lega…"}
        </p>
      </div>

      {config && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatTile label="Partecipanti" value={config.participants} />
          <StatTile label="Budget iniziale" value={`${config.starting_budget} FM`} />
          <StatTile label="Rosa" value={`${config.roster_size} giocatori`} />
          <StatTile label="Base d'asta" value={`${config.base_price} FM`} />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <QuickLink href="/auction/setup" title="Prepara l'asta" desc="Crea una sessione d'asta e verifica i dati importati" />
        <QuickLink href="/auction/live" title="Asta Live" desc="Dashboard live per condurre l'asta" />
        <QuickLink href="/players" title="Giocatori" desc="Sfoglia listone, FantaScore e valori" />
      </div>

      <div className="card p-4">
        <h2 className="mb-3 font-semibold">Stato fonti dati</h2>
        <div className="flex flex-col gap-2">
          {(sources ?? []).map((s) => (
            <div key={s.key} className="flex items-center justify-between text-sm">
              <span>{s.display_name}</span>
              <span className={`badge ${s.last_successful_sync ? "bg-accent/20 text-accent" : "bg-panel2 text-muted"}`}>
                {s.last_successful_sync
                  ? `Sync ${new Date(s.last_successful_sync).toLocaleString("it-IT")}`
                  : "Mai sincronizzato"}
              </span>
            </div>
          ))}
          {!sources?.length && <p className="text-sm text-muted">Nessuna fonte ancora registrata.</p>}
        </div>
      </div>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-1 text-xl font-bold">{value}</div>
    </div>
  );
}

function QuickLink({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <Link href={href} className="card block p-4 transition-colors hover:border-accent">
      <div className="font-semibold">{title}</div>
      <div className="mt-1 text-sm text-muted">{desc}</div>
    </Link>
  );
}
