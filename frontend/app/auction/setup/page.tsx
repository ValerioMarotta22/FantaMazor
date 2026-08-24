"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { AuctionSession, LeagueMember, Player } from "@/lib/types";

export default function AuctionSetupPage() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("Asta " + new Date().getFullYear());
  const [error, setError] = useState<string | null>(null);

  const { data: sessions } = useQuery({
    queryKey: ["auction-sessions"],
    queryFn: () => api.get<AuctionSession[]>("/api/auction/sessions"),
  });
  const { data: members } = useQuery({
    queryKey: ["league-members"],
    queryFn: () => api.get<LeagueMember[]>("/api/league/members"),
  });
  const { data: players } = useQuery({
    queryKey: ["players", "", ""],
    queryFn: () => api.get<Player[]>("/api/players"),
  });

  const createSession = useMutation({
    mutationFn: () => api.post<AuctionSession>("/api/auction/sessions", { name }),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["auction-sessions"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  });

  const deleteSession = useMutation({
    mutationFn: (sessionId: number) => api.delete(`/api/auction/sessions/${sessionId}`),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["auction-sessions"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  });

  function handleDelete(s: AuctionSession) {
    const ok = window.confirm(
      `Eliminare definitivamente la sessione "${s.name}"?\n\nTutte le transazioni al suo interno verranno cancellate. I giocatori e il FantaScore non vengono toccati. Questa azione non si può annullare.`
    );
    if (ok) deleteSession.mutate(s.id);
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Prepara l&apos;asta</h1>
        <p className="text-sm text-muted">Verifica i dati e crea una nuova sessione d&apos;asta.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card p-4">
          <div className="text-xs uppercase tracking-wide text-muted">Giocatori importati</div>
          <div className="mt-1 text-2xl font-bold">{players?.length ?? "—"}</div>
          {!players?.length && (
            <Link href="/settings/data" className="mt-2 inline-block text-xs text-accent hover:underline">
              Importa un listone →
            </Link>
          )}
        </div>
        <div className="card p-4">
          <div className="text-xs uppercase tracking-wide text-muted">Partecipanti in lega</div>
          <div className="mt-1 text-2xl font-bold">{members?.length ?? "—"}</div>
        </div>
        <div className="card p-4">
          <div className="text-xs uppercase tracking-wide text-muted">Sessioni esistenti</div>
          <div className="mt-1 text-2xl font-bold">{sessions?.length ?? "—"}</div>
        </div>
      </div>

      <div className="card p-4">
        <h2 className="mb-3 font-semibold">Nuova sessione d&apos;asta</h2>
        <div className="flex flex-wrap items-center gap-3">
          <input
            className="w-64 rounded-md border border-border bg-panel2 px-3 py-2 text-sm outline-none focus:border-accent"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button
            onClick={() => createSession.mutate()}
            disabled={createSession.isPending || !players?.length}
            className="rounded-md bg-accent px-3 py-2 text-sm font-semibold text-bg disabled:opacity-50"
          >
            {createSession.isPending ? "Creazione…" : "Crea sessione"}
          </button>
          {error && <span className="text-sm text-danger">{error}</span>}
        </div>
      </div>

      <div className="card p-4">
        <h2 className="mb-3 font-semibold">Sessioni</h2>
        <div className="flex flex-col divide-y divide-border">
          {sessions?.map((s) => (
            <div key={s.id} className="flex items-center justify-between py-2 text-sm">
              <div>
                <span className="font-medium">{s.name}</span>{" "}
                <span className="badge ml-2 bg-panel2 text-muted">{s.status}</span>
              </div>
              <div className="flex items-center gap-4">
                <Link href={`/auction/live?session=${s.id}`} className="text-accent hover:underline">
                  Apri asta live →
                </Link>
                <button
                  onClick={() => handleDelete(s)}
                  disabled={deleteSession.isPending}
                  className="text-xs text-danger hover:underline disabled:opacity-40"
                >
                  Elimina
                </button>
              </div>
            </div>
          ))}
          {!sessions?.length && <p className="py-4 text-sm text-muted">Nessuna sessione ancora creata.</p>}
        </div>
      </div>
    </div>
  );
}
