"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { LeagueSettings } from "@/lib/types";

export default function LeagueSettingsPage() {
  const queryClient = useQueryClient();
  const { data: settings } = useQuery({
    queryKey: ["league-settings"],
    queryFn: () => api.get<LeagueSettings>("/api/league/settings"),
  });

  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (settings) setText(JSON.stringify(settings.config, null, 2));
  }, [settings]);

  const save = useMutation({
    mutationFn: (config: object) => api.put<LeagueSettings>("/api/league/settings", { config }),
    onSuccess: () => {
      setSaved(true);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["league-settings"] });
      setTimeout(() => setSaved(false), 2000);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : String(e)),
  });

  function handleSave() {
    try {
      const parsed = JSON.parse(text);
      save.mutate(parsed);
    } catch {
      setError("JSON non valido");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">Regolamento di lega</h1>
        <p className="text-sm text-muted">
          Nulla qui è hardcoded nel codice — questa configurazione (§1) guida FantaScore, tiering, budget e il
          motore d'asta.
        </p>
      </div>

      <div className="card p-4">
        <textarea
          className="h-[520px] w-full rounded-md border border-border bg-panel2 p-3 font-mono text-xs outline-none focus:border-accent"
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
        />
        <div className="mt-3 flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={save.isPending}
            className="rounded-md bg-accent px-3 py-2 text-sm font-semibold text-bg disabled:opacity-50"
          >
            {save.isPending ? "Salvataggio…" : "Salva"}
          </button>
          {saved && <span className="text-sm text-accent">Salvato</span>}
          {error && <span className="text-sm text-danger">{error}</span>}
        </div>
      </div>
    </div>
  );
}
