"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuctionSession, LeagueSettings, SessionState } from "@/lib/types";

function BudgetInner() {
  const searchParams = useSearchParams();
  const [sessionId, setSessionId] = useState<string>(searchParams.get("session") ?? "");

  const { data: sessions } = useQuery({
    queryKey: ["auction-sessions"],
    queryFn: () => api.get<AuctionSession[]>("/api/auction/sessions"),
  });
  const { data: settings } = useQuery({
    queryKey: ["league-settings"],
    queryFn: () => api.get<LeagueSettings>("/api/league/settings"),
  });
  const { data: state } = useQuery({
    queryKey: ["session-state", sessionId],
    queryFn: () => api.get<SessionState>(`/api/auction/sessions/${sessionId}/state`),
    enabled: Boolean(sessionId),
  });

  const admin = state?.members.find((m) => m.is_admin);
  const basePrice = settings?.config.base_price ?? 1;

  const totalSlotsRemaining = admin
    ? Object.values(admin.slots_remaining).reduce((a, b) => a + b, 0)
    : 0;
  const minimumCompletionBudget = totalSlotsRemaining * basePrice;
  const safeSpendable = admin ? admin.budget_remaining - minimumCompletionBudget : 0;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">Budget</h1>
        <p className="text-sm text-muted">
          Il sistema non consiglierà mai una spesa che renda impossibile completare la rosa (§21).
        </p>
      </div>

      <select
        className="w-72 rounded-md border border-border bg-panel2 px-3 py-2 text-sm"
        value={sessionId}
        onChange={(e) => setSessionId(e.target.value)}
      >
        <option value="">Seleziona sessione…</option>
        {sessions?.map((s) => (
          <option key={s.id} value={s.id}>
            {s.name} (#{s.id})
          </option>
        ))}
      </select>

      {admin && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Tile label="Budget residuo" value={`${admin.budget_remaining} FM`} accent />
          <Tile label="Slot residui" value={totalSlotsRemaining} />
          <Tile label="Riserva minima" value={`${minimumCompletionBudget} FM`} />
          <Tile label="Spendibile in sicurezza" value={`${safeSpendable} FM`} accent />
        </div>
      )}

      {admin && (
        <div className="card p-4">
          <h2 className="mb-3 font-semibold">Slot residui per ruolo</h2>
          <div className="flex flex-col gap-2 text-sm">
            {Object.entries(admin.slots_remaining).map(([role, count]) => (
              <div key={role} className="flex items-center justify-between">
                <span className="text-muted">{role}</span>
                <span>
                  {count} × {basePrice} FM riservati = {count * basePrice} FM
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Tile({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className={`mt-1 text-xl font-bold ${accent ? "text-accent" : ""}`}>{value}</div>
    </div>
  );
}

export default function BudgetPage() {
  return (
    <Suspense fallback={<p className="text-muted">Caricamento…</p>}>
      <BudgetInner />
    </Suspense>
  );
}
