import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "EdgeLedger",
  description: "Football odds research, decision-support and bet tracking.",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main">
          Skip to content
        </a>
        <header className="app-header">
          <span className="app-name">EdgeLedger</span>
          <nav aria-label="Main">{/* Module navigation (PRD 13.2) goes here. */}</nav>
        </header>
        <Providers>
          <main id="main">{children}</main>
        </Providers>
        <footer className="app-footer">
          {/* RG-01: persistent risk-disclosure link goes here. */}
          <small>Estimates are model outputs and can be wrong.</small>
        </footer>
      </body>
    </html>
  );
}
