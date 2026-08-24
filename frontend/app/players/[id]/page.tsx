"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Player, PlayerScore, PlayerValue } from "@/lib/types";

export default function PlayerDetailPage() {
  const params = useParams();
  const playerId = Number(params.id);

  const { data: player } = useQuery({
    queryKey: ["player", playerId],
    queryFn: () => api.get<Player>(`/api/players/${playerId}`),
  });
  const { data: score } = useQuery({
    queryKey: ["player-score", playerId],
    queryFn: () => api.get<PlayerScore>(`/api/players/${playerId}/score`),
  });
  const { data: value } = useQuery({
    queryKey: ["player-value", playerId],
    queryFn: () => api.get<PlayerValue>(`/api/players/${playerId}/value`),
  });

  if (!player) return <p className="text-muted">Caricamento…</p>;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">{player.name}</h1>
        <p className="text-sm text-muted">
          {player.role} · {player.team_name ?? "Squadra sconosciuta"} · stato: {player.status}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="card p-4">
          <div className="text-xs uppercase tracking-wide text-muted">FantaScore</div>
          <div className="mt-1 text-3xl font-bold text-accent">{score?.fanta_score ?? "—"}</div>
          <div className="mt-1 text-xs text-muted">Fascia {score?.tier_label ?? "n/d"}</div>
        </div>
        <div className="card p-4">
          <div className="text-xs uppercase tracking-wide text-muted">Model Value</div>
          <div className="mt-1 text-3xl font-bold">{value?.model_value ?? "—"}</div>
          <div className="mt-1 text-xs text-muted">Stima teorica, non prezzo di mercato</div>
        </div>
        <div className="card p-4">
          <div className="text-xs uppercase tracking-wide text-muted">Market Average</div>
          <div className="mt-1 text-3xl font-bold">{value?.market_average ?? "n/d"}</div>
          <div className="mt-1 text-xs text-muted">Da transazioni locali di lega</div>
        </div>
      </div>

      {score?.components && Object.keys(score.components).length > 0 && (
        <div className="card p-4">
          <h2 className="mb-3 font-semibold">Perché questo FantaScore — {score.model_version}</h2>
          <div className="flex flex-col gap-2 text-sm">
            {Object.entries(score.components).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-muted">{key}</span>
                <span>{String(val)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {value?.components && Object.keys(value.components).length > 0 && (
        <div className="card p-4">
          <h2 className="mb-3 font-semibold">Composizione Model Value</h2>
          <div className="flex flex-col gap-2 text-sm">
            {Object.entries(value.components).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between">
                <span className="text-muted">{key}</span>
                <span>{String(val)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
