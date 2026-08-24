"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Player } from "@/lib/types";

const ROLES = ["", "POR", "DIF", "CEN", "ATT"];

export default function PlayersPage() {
  const [role, setRole] = useState("");
  const [search, setSearch] = useState("");

  const { data: players, isLoading } = useQuery({
    queryKey: ["players", role, search],
    queryFn: () => {
      const params = new URLSearchParams();
      if (role) params.set("role", role);
      if (search) params.set("search", search);
      const qs = params.toString();
      return api.get<Player[]>(`/api/players${qs ? `?${qs}` : ""}`);
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">Giocatori</h1>

      <div className="flex flex-wrap gap-3">
        <input
          className="w-64 rounded-md border border-border bg-panel2 px-3 py-2 text-sm outline-none focus:border-accent"
          placeholder="Cerca per nome…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="flex gap-1">
          {ROLES.map((r) => (
            <button
              key={r || "all"}
              onClick={() => setRole(r)}
              className={`rounded-md px-3 py-2 text-sm ${
                role === r ? "bg-accent text-bg font-semibold" : "bg-panel2 text-muted hover:text-white"
              }`}
            >
              {r || "Tutti"}
            </button>
          ))}
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-panel2 text-left text-xs uppercase text-muted">
            <tr>
              <th className="px-4 py-2">Nome</th>
              <th className="px-4 py-2">Ruolo</th>
              <th className="px-4 py-2">Squadra</th>
              <th className="px-4 py-2">Stato</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  Caricamento…
                </td>
              </tr>
            )}
            {!isLoading && !players?.length && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-muted">
                  Nessun giocatore importato. Vai su Impostazioni → Dati per importare un listone.
                </td>
              </tr>
            )}
            {players?.map((p) => (
              <tr key={p.id} className="border-t border-border hover:bg-panel2/50">
                <td className="px-4 py-2">
                  <Link href={`/players/${p.id}`} className="text-accent hover:underline">
                    {p.name}
                  </Link>
                </td>
                <td className="px-4 py-2">{p.role}</td>
                <td className="px-4 py-2 text-muted">{p.team_name ?? "—"}</td>
                <td className="px-4 py-2 text-muted">{p.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
