"use client";

import { useQuery } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === "/login";

  const { isLoading, isError } = useQuery({
    queryKey: ["me"],
    queryFn: () => api.get<{ username: string }>("/api/auth/me"),
    retry: false,
    enabled: !isLoginPage,
  });

  useEffect(() => {
    if (!isLoginPage && isError) {
      router.replace("/login");
    }
  }, [isError, isLoginPage, router]);

  if (isLoginPage) return <>{children}</>;
  if (isLoading) return <div className="p-6 text-muted">Caricamento…</div>;
  if (isError) return null; // redirect in flight

  return <>{children}</>;
}
