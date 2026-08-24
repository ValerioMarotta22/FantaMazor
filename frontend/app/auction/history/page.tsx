"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { AuctionSession, Transaction } from "@/lib/types";

function HistoryInner() {
  const searchParams = useSearchParams();
  const initialSession = searchParams.get("session");
  const [sessionId, setSessionId] = useState<string>(initialSession ?? "");
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: sessions } = useQuery({
    queryKey: ["auction-sessions"],
    queryFn: () => api.get<AuctionSession[]>("/api/auction/sessions"),
  });

  const { data: transactions } = useQuery({
    queryKey: ["transactions", sessionId],
    queryFn: () => api.get<Transaction[]>(`/api/auction/sessions/${sessionId}/transactions`),
    enabled: Boolean(sessionId),
  });

  const undoTransaction = useMutation({
    mutationFn: (transactionId: number) =>
      api.delete(`/api/auction/sessions/${sessionId}/transactions/${transactionId}`),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["transactions", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["session-state", sessionId] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  });

  function handleUndo(t: Transaction) {
    const ok = window.confirm(
      `Annullare l'acquisto di ${t.player_name} da parte di ${t.buyer_name} a ${t.price} FM?\n\nIl giocatore tornerà disponibile e il budget/slot verranno ripristinati.`
    );
    if (ok) undoTransaction.mutate(t.id);
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">Storico asta</h1>
        <p className="text-sm text-muted">Ogni transazione registrata — la base per le statistiche di mercato di lega (§7).</p>
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

      {error && <p className="text-sm text-danger">{error}</p>}

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-panel2 text-left text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-2">Giocatore</th>
              <th className="px-4 py-2">Ruolo</th>
              <th className="px-4 py-2">Acquirente</th>
              <th className="px-4 py-2">Prezzo</th>
              <th className="px-4 py-2">Budget dopo</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {transactions?.map((t) => (
              <tr key={t.id} className="border-t border-border">
                <td className="px-4 py-2">{t.player_name}</td>
                <td className="px-4 py-2">{t.role}</td>
                <td className="px-4 py-2">{t.buyer_name}</td>
                <td className="px-4 py-2 font-semibold">{t.price} FM</td>
                <td className="px-4 py-2 text-muted">{t.budget_after} FM</td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => handleUndo(t)}
                    disabled={undoTransaction.isPending}
                    className="text-xs text-danger hover:underline disabled:opacity-40"
                  >
                    Annulla
                  </button>
                </td>
              </tr>
            ))}
            {sessionId && !transactions?.length && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-muted">
                  Nessuna transazione ancora registrata per questa sessione.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  return (
    <Suspense fallback={<p className="text-muted">Caricamento…</p>}>
      <HistoryInner />
    </Suspense>
  );
}
