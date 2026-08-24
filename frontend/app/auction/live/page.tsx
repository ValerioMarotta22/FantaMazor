"use client";

import { Suspense, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { MemberState, Player, Recommendation, SessionState } from "@/lib/types";

function ScarcityBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    HIGH: "bg-danger/20 text-danger",
    MEDIUM: "bg-warn/20 text-warn",
    LOW: "bg-accent/20 text-accent",
    UNKNOWN: "bg-panel2 text-muted",
  };
  return <span className={`badge ${colors[level] ?? colors.UNKNOWN}`}>{level}</span>;
}

function LiveAuctionInner() {
  const searchParams = useSearchParams();
  const sessionId = Number(searchParams.get("session"));
  const queryClient = useQueryClient();

  const [playerQuery, setPlayerQuery] = useState("");
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);
  const [buyerId, setBuyerId] = useState<number | null>(null);
  const [price, setPrice] = useState<string>("");
  const [txnError, setTxnError] = useState<string | null>(null);

  const { data: players } = useQuery({
    queryKey: ["players", "", ""],
    queryFn: () => api.get<Player[]>("/api/players"),
    enabled: Boolean(sessionId),
  });

  const { data: state, refetch: refetchState } = useQuery({
    queryKey: ["session-state", sessionId],
    queryFn: () => api.get<SessionState>(`/api/auction/sessions/${sessionId}/state`),
    enabled: Boolean(sessionId),
  });

  const { data: recommendation, refetch: refetchRecommendation } = useQuery({
    queryKey: ["recommendation", sessionId, selectedPlayerId],
    queryFn: () =>
      api.get<Recommendation>(`/api/auction/recommendation/${selectedPlayerId}?session_id=${sessionId}`),
    enabled: Boolean(sessionId) && Boolean(selectedPlayerId),
  });

  const admin = state?.members.find((m) => m.is_admin);
  const opponents = state?.members.filter((m) => !m.is_admin) ?? [];
  const selectedPlayer = players?.find((p) => p.id === selectedPlayerId);

  const matches = useMemo(() => {
    if (!playerQuery || !players) return [];
    const q = playerQuery.toLowerCase();
    return players.filter((p) => p.name.toLowerCase().includes(q)).slice(0, 8);
  }, [playerQuery, players]);

  const recordTransaction = useMutation({
    mutationFn: () => {
      if (!selectedPlayerId || !buyerId || !price) throw new Error("Compila giocatore, acquirente e prezzo");
      return api.post(`/api/auction/sessions/${sessionId}/transactions`, {
        player_id: selectedPlayerId,
        buyer_member_id: buyerId,
        price: Number(price),
      });
    },
    onSuccess: () => {
      setTxnError(null);
      setSelectedPlayerId(null);
      setPlayerQuery("");
      setPrice("");
      refetchState();
      queryClient.invalidateQueries({ queryKey: ["players"] });
    },
    onError: (e) => setTxnError(e instanceof ApiError ? e.message : String(e)),
  });

  if (!sessionId) {
    return <p className="text-muted">Nessuna sessione selezionata. Vai su Asta → Setup e apri una sessione.</p>;
  }

  return (
    <div className="flex flex-col gap-4">
      {/* TOP: role / price context */}
      <div className="card flex items-center justify-between px-4 py-3">
        <div>
          <span className="text-xs uppercase tracking-wide text-muted">Sessione</span>{" "}
          <span className="font-semibold">#{sessionId}</span>
          {state && <span className="badge ml-3 bg-panel2 text-muted">{state.status}</span>}
        </div>
        {admin && (
          <div className="text-sm">
            <span className="text-muted">Il tuo budget: </span>
            <span className="font-bold text-accent">{admin.budget_remaining} FM</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr_260px]">
        {/* LEFT: your roster */}
        <div className="card p-4">
          <h2 className="mb-3 font-semibold">La tua rosa</h2>
          {admin && (
            <div className="flex flex-col gap-1 text-sm">
              {Object.entries(admin.slots_remaining).map(([role, count]) => (
                <div key={role} className="flex items-center justify-between">
                  <span className="text-muted">{role}</span>
                  <span>{count} liberi</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* CENTER: current player + full recommendation */}
        <div className="card p-4">
          <div className="relative">
            <input
              className="w-full rounded-md border border-border bg-panel2 px-3 py-2 text-sm outline-none focus:border-accent"
              placeholder="Cerca giocatore chiamato…"
              value={playerQuery}
              onChange={(e) => {
                setPlayerQuery(e.target.value);
                setSelectedPlayerId(null);
              }}
            />
            {matches.length > 0 && !selectedPlayerId && (
              <div className="absolute z-10 mt-1 w-full rounded-md border border-border bg-panel2 shadow-lg">
                {matches.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      setSelectedPlayerId(p.id);
                      setPlayerQuery(p.name);
                    }}
                    className="block w-full px-3 py-2 text-left text-sm hover:bg-panel"
                  >
                    {p.name} <span className="text-muted">· {p.role}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {selectedPlayer && (
            <div className="mt-4">
              <div className="flex items-baseline justify-between">
                <h3 className="text-xl font-bold">{selectedPlayer.name}</h3>
                <span className="badge bg-panel2 text-muted">{selectedPlayer.role}</span>
              </div>

              {recommendation && (
                <>
                  <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <Metric label="FantaScore" value={recommendation.fanta_score ?? "—"} />
                    <Metric label="Fascia" value={recommendation.tier_label ?? "—"} />
                    <Metric label="Model Value" value={recommendation.model_value ?? "—"} />
                    <Metric label="Market Avg" value={recommendation.market_average ?? "n/d"} />
                  </div>

                  <div className="mt-3 flex items-center gap-3">
                    <ScarcityBadge level={recommendation.scarcity.level} />
                    <span className="text-xs text-muted">
                      {recommendation.scarcity.players_remaining_in_tier} rimasti in fascia ·{" "}
                      {recommendation.scarcity.slots_still_needed_league_wide} slot richiesti in lega
                    </span>
                  </div>

                  {recommendation.recommended_price && (
                    <div className="mt-4 rounded-md bg-panel2 p-3">
                      <div className="mb-2 text-xs uppercase tracking-wide text-muted">Prezzo consigliato</div>
                      <div className="flex flex-wrap gap-4 text-sm">
                        <span>
                          🟢 Bargain <b>≤{recommendation.recommended_price.bargain_max}</b>
                        </span>
                        <span>
                          🟡 Fair <b>≤{recommendation.recommended_price.fair_max}</b>
                        </span>
                        <span>
                          🟠 Aggressive <b>≤{recommendation.recommended_price.aggressive_max}</b>
                        </span>
                        <span className={recommendation.recommended_price.hard_capped ? "text-danger" : ""}>
                          🔴 Massimo <b>{recommendation.recommended_price.maximum}</b>
                          {recommendation.recommended_price.hard_capped && " (limite budget)"}
                        </span>
                      </div>
                    </div>
                  )}

                  {recommendation.warnings.length > 0 && (
                    <div className="mt-3 flex flex-col gap-1">
                      {recommendation.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-warn">
                          ⚠ {w}
                        </p>
                      ))}
                    </div>
                  )}
                </>
              )}

              <div className="mt-5 flex flex-wrap items-end gap-3 border-t border-border pt-4">
                <div>
                  <label className="mb-1 block text-xs text-muted">Acquirente</label>
                  <select
                    className="rounded-md border border-border bg-panel2 px-3 py-2 text-sm"
                    value={buyerId ?? ""}
                    onChange={(e) => setBuyerId(Number(e.target.value) || null)}
                  >
                    <option value="">—</option>
                    {state?.members.map((m) => (
                      <option key={m.member_id} value={m.member_id}>
                        {m.name}
                        {m.is_admin ? " (tu)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs text-muted">Prezzo finale (FM)</label>
                  <input
                    type="number"
                    min={1}
                    className="w-28 rounded-md border border-border bg-panel2 px-3 py-2 text-sm"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") recordTransaction.mutate();
                    }}
                  />
                </div>
                <button
                  onClick={() => recordTransaction.mutate()}
                  disabled={recordTransaction.isPending}
                  className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-bg disabled:opacity-50"
                >
                  {recordTransaction.isPending ? "Registrazione…" : "Registra acquisto"}
                </button>
              </div>
              {txnError && <p className="mt-2 text-sm text-danger">{txnError}</p>}
            </div>
          )}

          {!selectedPlayer && <p className="mt-6 text-sm text-muted">Cerca il giocatore chiamato all&apos;asta.</p>}
        </div>

        {/* RIGHT: opponents */}
        <div className="card p-4">
          <h2 className="mb-3 font-semibold">Avversari</h2>
          <div className="flex flex-col gap-3">
            {opponents.map((o) => (
              <OpponentRow key={o.member_id} member={o} />
            ))}
          </div>
        </div>
      </div>
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

function OpponentRow({ member }: { member: MemberState }) {
  const totalNeeded = Object.values(member.slots_remaining).reduce((a, b) => a + b, 0);
  return (
    <div className="rounded-md bg-panel2 p-3 text-sm">
      <div className="flex items-center justify-between">
        <span className="font-medium">{member.name}</span>
        <span className="font-bold">{member.budget_remaining} FM</span>
      </div>
      <div className="mt-1 text-xs text-muted">{totalNeeded} slot ancora da riempire</div>
    </div>
  );
}

export default function LiveAuctionPage() {
  return (
    <Suspense fallback={<p className="text-muted">Caricamento…</p>}>
      <LiveAuctionInner />
    </Suspense>
  );
}
