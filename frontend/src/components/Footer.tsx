import Link from "next/link";

const links = [
  { href: "/", label: "Inicio" },
  { href: "/solver", label: "Resolver" },
  { href: "/about", label: "Cómo funciona" },
];

export default function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-4 px-5 py-6 sm:flex-row sm:px-8">
        <Link href="/" className="text-sm font-semibold tracking-tight text-ink">
          KenKen<span className="text-blue">Lab</span>
        </Link>
        <ul className="flex items-center gap-6 text-sm text-ink-2">
          {links.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="transition-colors hover:text-blue">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}
