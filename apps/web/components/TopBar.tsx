import Link from "next/link";

export default function TopBar() {
  return (
    <div className="topbar">
      <Link href="/" className="brand">
        <span className="brand-mark">BH</span>
        BugHound
      </Link>
      <nav className="topbar-nav">
        <a href="#how-it-works">How it works</a>
        <a href="#findings">Findings</a>
        <a href="#faq">FAQ</a>
      </nav>
      <div className="topbar-links">
        <a
          href="https://github.com/Aditya-tec/bughound"
          target="_blank"
          rel="noreferrer"
          className="ghost-btn"
        >
          GitHub ↗
        </a>
      </div>
    </div>
  );
}
