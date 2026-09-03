import type { Metadata } from "next";
import "./globals.css";
import TopBar from "@/components/TopBar";

export const metadata: Metadata = {
  title: "BugHound",
  description: "An autonomous agent that explores websites and finds real bugs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <div className="glow" aria-hidden="true" />
          <TopBar />
          {children}
        </div>
      </body>
    </html>
  );
}
