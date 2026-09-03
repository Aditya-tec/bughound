"use client";

import { useEffect } from "react";

export default function Tier1Fixture() {
  useEffect(() => {
    console.error("Eval fixture: intentional console error");
  }, []);

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "3rem 1.5rem" }}>
      <h1>Tier 1 — Functional fixture</h1>

      <img src="/eval/does-not-exist.png" alt="Intentionally broken image" width={200} height={120} />

      <p>
        <a href="/eval/tier1-functional/dead-page">This internal link goes nowhere</a>
      </p>

      <form onSubmit={(e) => e.preventDefault()}>
        <label htmlFor="required-field">Required field, no client-side validation feedback</label>
        <br />
        <input id="required-field" name="required-field" required />
        <button type="submit">Submit</button>
      </form>

      <p style={{ marginTop: "3rem", fontSize: "0.75rem", color: "#999" }}>
        BugHound eval fixture — intentionally broken for automated recall testing.
      </p>
    </main>
  );
}
