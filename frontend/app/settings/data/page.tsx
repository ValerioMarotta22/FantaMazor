"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { DataSourceStatus, ImportResult } from "@/lib/types";

const SEASON_LABEL = "2025-26";

export default function DataSettingsPage() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [log, setLog] = useState<string[]>([]);

  const { data: sources } = useQuery({
    queryKey: ["data-status"],
    queryFn: () => api.get<DataSourceStatus[]>("/api/data/status"),
  });

  function pushLog(line: string) {
    setLog((prev) => [line, ...prev].slice(0, 20));
  }

  const importDemo = useMutation({
    mutationFn: () => api.post<ImportResult>("/api/data/import/demo"),
    onSuccess: (r) => {
      pushLog(
        `Demo importato: ${r.records_imported} righe (${r.players_created} nuovi giocatori, ${r.players_matched} già noti)`
      );
      queryClient.invalidateQueries({ queryKey: ["data-status"] });
    },
    onError: (e) => pushLog(`Errore import demo: ${e instanceof ApiError ? e.message : String(e)}`),
  });

  const importListone = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Nessun file selezionato");
      const form = new FormData();
      form.append("file", file);
      return api.postForm<ImportResult>(`/api/data/import/listone?season_label=${SEASON_LABEL}`, form);
    },
    onSuccess: (r) => {
      pushLog(
        `Listone importato: ${r.records_imported} righe (${r.players_created} nuovi giocatori, ${r.players_matched} già noti)`
      );
      queryClient.invalidateQueries({ queryKey: ["data-status"] });
    },
    onError: (e) => pushLog(`Errore import listone: ${e instanceof ApiError ? e.message : String(e)}`),
  });

  const runScoring = useMutation({
    mutationFn: () => api.post<{ players_scored: number }>(`/api/data/score?season_label=${SEASON_LABEL}`),
    onSuccess: (r) => pushLog(`FantaScore calcolato per ${r.players_scored} giocatori`),
    onError: (e) => pushLog(`Errore scoring: ${e instanceof ApiError ? e.message : String(e)}`),
  });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Dati</h1>
        <p className="text-sm text-muted">
          Importa un listone (CSV/JSON) o usa i dati demo, poi calcola il FantaScore. Nessuna chiamata a fonti
          esterne avviene automaticamente — vedi §37/§57.
        </p>
      </div>

      <div className="card p-4">
        <h2 className="mb-3 font-semibold">1. Importa dati</h2>
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".csv,.json"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="text-sm text-muted"
          />
          <button
            onClick={() => importListone.mutate()}
            disabled={!file || importListone.isPending}
            className="rounded-md bg-accent px-3 py-2 text-sm font-semibold text-bg disabled:opacity-50"
          >
            {importListone.isPending ? "Importazione…" : "Importa listone"}
          </button>
          <span className="text-muted">oppure</span>
          <button
            onClick={() => importDemo.mutate()}
            disabled={importDemo.isPending}
            className="rounded-md bg-panel2 px-3 py-2 text-sm font-semibold disabled:opacity-50"
          >
            {importDemo.isPending ? "Importazione…" : "Usa dati demo"}
          </button>
        </div>
        <p className="mt-2 text-xs text-muted">
          CSV richiesto: colonne <code>name,role</code> obbligatorie, <code>team,quotation,fvm</code> opzionali.
        </p>
      </div>

      <div className="card p-4">
        <h2 className="mb-3 font-semibold">2. Calcola FantaScore</h2>
        <button
          onClick={() => runScoring.mutate()}
          disabled={runScoring.isPending}
          className="rounded-md bg-accent px-3 py-2 text-sm font-semibold text-bg disabled:opacity-50"
        >
          {runScoring.isPending ? "Calcolo…" : `Calcola FantaScore per ${SEASON_LABEL}`}
        </button>
      </div>

      <div className="card p-4">
        <h2 className="mb-3 font-semibold">Stato fonti</h2>
        <table className="w-full text-sm">
          <thead className="text-left text-xs uppercase text-muted">
            <tr>
              <th className="py-1">Fonte</th>
              <th className="py-1">Ultimo sync riuscito</th>
              <th className="py-1">Ultimo errore</th>
            </tr>
          </thead>
          <tbody>
            {sources?.map((s) => (
              <tr key={s.key} className="border-t border-border">
                <td className="py-2">{s.display_name}</td>
                <td className="py-2 text-muted">
                  {s.last_successful_sync ? new Date(s.last_successful_sync).toLocaleString("it-IT") : "mai"}
                </td>
                <td className="py-2 text-danger">{s.last_error ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {log.length > 0 && (
        <div className="card p-4">
          <h2 className="mb-2 font-semibold">Log</h2>
          <div className="flex flex-col gap-1 text-xs text-muted">
            {log.map((line, i) => (
              <div key={i}>{line}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
