"use client";

import { useState } from "react";

export default function AnnouncementBar() {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) return null;

  return (
    <div className="announcement">
      <span>Scan mode runs end-to-end today — free, with no card, by design.</span>
      <a
        className="pill-mini"
        href="https://github.com/Aditya-tec/bughound"
        target="_blank"
        rel="noreferrer"
      >
        Star on GitHub ↗
      </a>
      <button className="close" aria-label="Dismiss" onClick={() => setDismissed(true)}>
        ×
      </button>
    </div>
  );
}
