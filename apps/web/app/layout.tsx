import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BugHound",
  description: "An autonomous agent that explores websites and finds real bugs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
