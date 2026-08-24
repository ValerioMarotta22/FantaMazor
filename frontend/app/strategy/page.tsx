"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { AuctionSession, LeagueSettings, Player, PlayerValue, SessionState, SimulationResult } from "@/lib/types";

interface Target {
  player_id: number;
  name: string;
  role: string;
  model_value: number;
}

function StrategyInner() {
  const searchParams = useSearchParams();
  const [sessionId, setSessionId] = useState<string>(searchParams.get("session") ?? "");
  const [playerQuery, setPlayerQuery] = useState("");
  const [targets, setTargets] = useState<Target[]>([]);
  const [otherSlots, setOtherSlots] = useState<number>(15);
  const [iterations, setIterations] = useState<100 | 500 | 1000>(500);
  const [error, setError] = useState<string | null>(null);

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
  const { data: players } = useQuery({
    queryKey: ["players", "", ""],
    queryFn: () => api.get<Player[]>("/api/players"),
  });

  const admin = state?.members.find((m) => m.is_admin);
  const basePrice = settings?.config.base_price ?? 1;

  const matches = useMemo(() => {
    if (!playerQuery || !players) return [];
    const q = playerQuery.toLowerCase();
    return players
      .filter((p) => p.name.toLowerCase().includes(q) && !targets.some((t) => t.player_id === p.id))
      .slice(0, 6);
  }, [playerQuery, players, targets]);

  async function addTarget(p: Player) {
    try {
      const value = await api.get<PlayerValue>(`/api/players/${p.id}/value`);
      setTargets((prev) => [
        ...prev,
        { player_id: p.id, name: p.name, role: p.role, model_value: value.model_value ?? 0 },
      ]);
      setPlayerQuery("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  }

  const simulate = useMutation({
    mutationFn: () =>
      api.post<SimulationResult>("/api/auction/simulate", {
        targets: targets.map((t) => ({ player_id: t.player_id, role: t.role, model_value: t.model_value })),
        other_slots_needed: otherSlots,
        base_price: basePrice,
        budget: admin?.budget_remaining ?? settings?.config.starting_budget ?? 500,
        iterations,
      }),
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">Strategia &amp; Simulazione</h1>
        <p className="text-sm text-muted">
          Simula quanto potrebbe costare acquistare una lista di obiettivi (§23). Non modella i 9 avversari in
          modo indipendente — vedi nota nel motore.
        </p>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          className="w-64 rounded-md border border-border bg-panel2 px-3 py-2 text-sm"
          value={sessionId}
          onChange={(e) => setSessionId(e.target.value)}
        >
          <option value="">Sessione (opzionale, per budget reale)…</option>
          {sessions?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} (#{s.id})
            </option>
          ))}
        </select>
        <div className="flex items-center gap-2 text-sm">
          <label className="text-muted">Altri slot da riempire</label>
          <input
            type="number"
            className="w-20 rounded-md border border-border bg-panel2 px-2 py-2 text-sm"
            value={otherSlots}
            onChange={(e) => setOtherSlots(Number(e.target.value))}
          />
        </div>
        <div className="flex items-center gap-2 text-sm">
          <label className="text-muted">Iterazioni</label>
          <select
            className="rounded-md border border-border bg-panel2 px-2 py-2 text-sm"
            value={iterations}
            onChange={(e) => setIterations(Number(e.target.value) as 100 | 500 | 1000)}
          >
            <option value={100}>100</option>
            <option value={500}>500</option>
            <option value={1000}>1000</option>
          </select>
        </div>
      </div>

      <div className="card p-4">
        <h2 className="mb-3 font-semibold">Obiettivi</h2>
        <div className="relative mb-3">
          <input
            className="w-full rounded-md border border-border bg-panel2 px-3 py-2 text-sm outline-none focus:border-accent"
            placeholder="Aggiungi giocatore…"
            value={playerQuery}
            onChange={(e) => setPlayerQuery(e.target.value)}
          />
          {matches.length > 0 && (
            <div className="absolute z-10 mt-1 w-full rounded-md border border-border bg-panel2 shadow-lg">
              {matches.map((p) => (
                <button
                  key={p.id}
                  onClick={() => addTarget(p)}
                  className="block w-full px-3 py-2 text-left text-sm hover:bg-panel"
                >
                  {p.name} <span className="text-muted">· {p.role}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col divide-y divide-border">
          {targets.map((t) => (
            <div key={t.player_id} className="flex items-center justify-between py-2 text-sm">
              <span>
                {t.name} <span className="text-muted">· {t.role}</span>
              </span>
              <div className="flex items-center gap-3">
                <span className="font-semibold">{t.model_value} FM</span>
                <button
                  onClick={() => setTargets((prev) => prev.filter((x) => x.player_id !== t.player_id))}
                  className="text-xs text-danger hover:underline"
                >
                  Rimuovi
                </button>
              </div>
            </div>
          ))}
          {!targets.length && <p className="py-4 text-sm text-muted">Nessun obiettivo aggiunto.</p>}
        </div>

        <button
          onClick={() => simulate.mutate()}
          disabled={!targets.length || simulate.isPending}
          className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-bg disabled:opacity-50"
        >
          {simulate.isPending ? "Simulazione…" : `Simula (${iterations}x)`}
        </button>
        {error && <p className="mt-2 text-sm text-danger">{error}</p>}
      </div>

      {simulate.data && (
        <div className="card p-4">
          <h2 className="mb-3 font-semibold">Risultato simulazione</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <Metric label="Probabilità completamento" value={`${Math.round(simulate.data.completion_probability * 100)}%`} />
            <Metric label="Costo p10" value={`${simulate.data.total_cost_p10} FM`} />
            <Metric label="Costo p50" value={`${simulate.data.total_cost_p50} FM`} />
            <Metric label="Costo p90" value={`${simulate.data.total_cost_p90} FM`} />
            <Metric label="Budget residuo (p50)" value={`${simulate.data.remaining_budget_p50} FM`} />
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted">{label}</div>
      <div className="text-lg font-bold">{value}</div>
    </div>
  );
}

export default function StrategyPage() {
  return (
    <Suspense fallback={<p className="text-muted">Caricamento…</p>}>
      <StrategyInner />
    </Suspense>
  );
}
