import Link from "next/link";

export default function TopBar() {
  return (
    <div className="topbar">
      <Link href="/" className="brand">
        <span className="brand-mark">BH</span>
        BugHound
      </Link>
      <div className="topbar-links">
        <a href="https://github.com/Aditya-tec/bughound" target="_blank" rel="noreferrer">
          GitHub
        </a>
      </div>
    </div>
  );
}
