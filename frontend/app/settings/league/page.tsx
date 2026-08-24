"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api";
import { LeagueMember, LeagueSettings } from "@/lib/types";

export default function LeagueSettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <MembersSection />
      <RulesSection />
    </div>
  );
}

function MembersSection() {
  const queryClient = useQueryClient();
  const { data: members } = useQuery({
    queryKey: ["league-members"],
    queryFn: () => api.get<LeagueMember[]>("/api/league/members"),
  });
  const [names, setNames] = useState<Record<number, string>>({});
  const [savedId, setSavedId] = useState<number | null>(null);

  useEffect(() => {
    if (members) {
      setNames(Object.fromEntries(members.map((m) => [m.id, m.name])));
    }
  }, [members]);

  const rename = useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api.put<LeagueMember>(`/api/league/members/${id}`, { name }),
    onSuccess: (_data, variables) => {
      setSavedId(variables.id);
      queryClient.invalidateQueries({ queryKey: ["league-members"] });
      setTimeout(() => setSavedId(null), 1500);
    },
  });

  return (
    <div>
      <h1 className="text-2xl font-bold">Partecipanti</h1>
      <p className="mb-4 text-sm text-muted">
        Rinomina i 10 partecipanti con i nomi veri prima dell&apos;asta — questi nomi appariranno ovunque
        nell&apos;app (asta live, rose, storico).
      </p>
      <div className="card flex flex-col divide-y divide-border p-4">
        {members?.map((m) => (
          <div key={m.id} className="flex items-center gap-3 py-2">
            <input
              className="w-64 rounded-md border border-border bg-panel2 px-3 py-1.5 text-sm outline-none focus:border-accent"
              value={names[m.id] ?? ""}
              onChange={(e) => setNames((prev) => ({ ...prev, [m.id]: e.target.value }))}
            />
            {m.is_admin && <span className="badge bg-accent/20 text-accent">tu</span>}
            <button
              onClick={() => rename.mutate({ id: m.id, name: names[m.id] })}
              disabled={rename.isPending || names[m.id] === m.name}
              className="rounded-md bg-panel2 px-3 py-1.5 text-xs font-semibold hover:bg-border disabled:opacity-40"
            >
              Salva
            </button>
            {savedId === m.id && <span className="text-xs text-accent">Salvato</span>}
          </div>
        ))}
        {!members?.length && <p className="py-4 text-sm text-muted">Nessun partecipante trovato.</p>}
      </div>
    </div>
  );
}

function RulesSection() {
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
    <div>
      <h2 className="text-xl font-bold">Regolamento di lega</h2>
      <p className="mb-4 text-sm text-muted">
        Nulla qui è hardcoded nel codice — questa configurazione (§1) guida FantaScore, tiering, budget e il
        motore d&apos;asta.
      </p>

      <div className="card p-4">
        <textarea
          className="h-[420px] w-full rounded-md border border-border bg-panel2 p-3 font-mono text-xs outline-none focus:border-accent"
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
