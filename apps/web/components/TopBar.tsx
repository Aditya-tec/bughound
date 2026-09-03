import Image from "next/image";
import Link from "next/link";

export default function TopBar() {
  return (
    <div className="topbar">
      <Link href="/" className="brand">
        <Image src="/logo-round-128.png" alt="" width={30} height={30} className="brand-mark" priority />
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
