import "./globals.css";

import Link from "next/link";
import type { ReactNode } from "react";

export const metadata = {
  title: "Liber Novus Admin",
  description: "Internal debug console for session traces"
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main className="shell">
          <nav className="nav">
            <Link className="brand" href="/sessions">
              Liber Novus Admin
            </Link>
            <Link href="/sessions">Sessions</Link>
            <Link href="/prompts">Prompts</Link>
          </nav>
          {children}
        </main>
      </body>
    </html>
  );
}
