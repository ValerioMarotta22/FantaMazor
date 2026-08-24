"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AuctionSession, MemberRoster, SessionState } from "@/lib/types";

function SquadInner() {
  const searchParams = useSearchParams();
  const [sessionId, setSessionId] = useState<string>(searchParams.get("session") ?? "");

  const { data: sessions } = useQuery({
    queryKey: ["auction-sessions"],
    queryFn: () => api.get<AuctionSession[]>("/api/auction/sessions"),
  });

  const { data: state } = useQuery({
    queryKey: ["session-state", sessionId],
    queryFn: () => api.get<SessionState>(`/api/auction/sessions/${sessionId}/state`),
    enabled: Boolean(sessionId),
  });

  const admin = state?.members.find((m) => m.is_admin);

  const { data: roster } = useQuery({
    queryKey: ["roster", admin?.member_id, sessionId],
    queryFn: () => api.get<MemberRoster>(`/api/league/members/${admin!.member_id}/roster?session_id=${sessionId}`),
    enabled: Boolean(admin) && Boolean(sessionId),
  });

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">La tua rosa</h1>
        <p className="text-sm text-muted">Giocatori acquistati e slot residui per la sessione selezionata.</p>
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

      {roster && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <div className="card p-4">
              <div className="text-xs uppercase tracking-wide text-muted">Budget residuo</div>
              <div className="mt-1 text-xl font-bold text-accent">{roster.budget_remaining} FM</div>
            </div>
            {Object.entries(roster.slots_remaining).map(([role, count]) => (
              <div key={role} className="card p-4">
                <div className="text-xs uppercase tracking-wide text-muted">{role} liberi</div>
                <div className="mt-1 text-xl font-bold">{count}</div>
              </div>
            ))}
          </div>

          <div className="card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-panel2 text-left text-xs uppercase text-muted">
                <tr>
                  <th className="px-4 py-2">Giocatore</th>
                  <th className="px-4 py-2">Ruolo</th>
                  <th className="px-4 py-2">Prezzo</th>
                </tr>
              </thead>
              <tbody>
                {roster.players.map((p) => (
                  <tr key={p.player_id} className="border-t border-border">
                    <td className="px-4 py-2">{p.name}</td>
                    <td className="px-4 py-2">{p.role}</td>
                    <td className="px-4 py-2 font-semibold">{p.price} FM</td>
                  </tr>
                ))}
                {!roster.players.length && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-center text-muted">
                      Nessun giocatore ancora acquistato.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export default function SquadPage() {
  return (
    <Suspense fallback={<p className="text-muted">Caricamento…</p>}>
      <SquadInner />
    </Suspense>
  );
}
