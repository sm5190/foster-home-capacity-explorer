import type { Metadata } from "next";
import type { ReactNode } from "react";

import { SiteHeader } from "../components/site-header";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Illinois Foster Home Capacity Explorer",
    template: "%s | Illinois Foster Home Capacity Explorer",
  },

  description:
    "County-level foster-home recruitment and existing-home engagement indicators for Illinois.",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>
        <SiteHeader />

        <main>{children}</main>

        <footer className="site-footer">
          <div className="site-footer__inner">
            <p>Illinois Foster Home Capacity Explorer</p>

            <p>Aggregate data as of July 1, 2026</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
