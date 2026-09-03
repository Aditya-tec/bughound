import type { Metadata } from "next";
import "./globals.css";
import TopBar from "@/components/TopBar";
import AnnouncementBar from "@/components/AnnouncementBar";

export const metadata: Metadata = {
  title: "BugHound",
  description: "An autonomous agent that explores websites and finds real bugs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400&family=IBM+Plex+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="shell">
          <AnnouncementBar />
          <TopBar />
          {children}
        </div>
      </body>
    </html>
  );
}
