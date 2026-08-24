import type { Metadata } from "next";
import { AuthGate } from "@/components/AuthGate";
import { Nav } from "@/components/Nav";
import { Providers } from "./providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "FantaMazor",
  description: "Decision-support system for Fantacalcio",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body className="min-h-screen bg-bg text-white">
        <Providers>
          <Nav />
          <main className="mx-auto max-w-7xl px-4 py-6">
            <AuthGate>{children}</AuthGate>
          </main>
        </Providers>
      </body>
    </html>
  );
}
