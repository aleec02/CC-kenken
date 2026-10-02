"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";

const links = [
  { href: "/", label: "Inicio" },
  { href: "/solver", label: "Resolver" },
  { href: "/about", label: "Cómo funciona" },
];

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="sticky top-0 z-40 border-b border-line bg-paper/95 backdrop-blur-sm"
    >
      <nav className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link
          href="/"
          onClick={() => setOpen(false)}
          className="flex items-center gap-2.5 font-semibold tracking-tight"
        >
          <Logo />
          <span className="text-[17px]">
            KenKen<span className="text-blue">Lab</span>
          </span>
        </Link>

        <ul className="hidden items-center gap-1 sm:flex">
          {links.map((l) => {
            const active = pathname === l.href;
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className={`relative rounded-md px-3.5 py-2 text-sm transition-colors ${
                    active ? "text-ink" : "text-ink-2 hover:text-ink"
                  }`}
                >
                  {l.label}
                  {active && (
                    <motion.span
                      layoutId="nav-underline"
                      className="absolute inset-x-3.5 -bottom-[13px] h-0.5 bg-blue"
                      transition={{ type: "spring", stiffness: 500, damping: 40 }}
                    />
                  )}
                </Link>
              </li>
            );
          })}
          <li className="ml-2">
            <Link
              href="/solver"
              className="rounded-md bg-ink px-4 py-2 text-sm font-medium text-paper transition-colors hover:bg-blue"
            >
              Subir puzzle
            </Link>
          </li>
        </ul>

        <button
          aria-label={open ? "Cerrar menú" : "Abrir menú"}
          onClick={() => setOpen((v) => !v)}
          className="rounded-md p-2 text-ink sm:hidden"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.ul
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden border-t border-line sm:hidden"
          >
            {links.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className={`block px-6 py-3.5 text-[15px] ${
                    pathname === l.href ? "font-medium text-blue" : "text-ink-2"
                  }`}
                >
                  {l.label}
                </Link>
              </li>
            ))}
            <li className="px-5 pb-5 pt-2">
              <Link
                href="/solver"
                onClick={() => setOpen(false)}
                className="block rounded-md bg-ink py-3 text-center text-[15px] font-medium text-paper"
              >
                Subir puzzle
              </Link>
            </li>
          </motion.ul>
        )}
      </AnimatePresence>
    </motion.header>
  );
}

function Logo() {
  return (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden>
      <rect x="1" y="1" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" />
      <line x1="13" y1="1" x2="13" y2="25" stroke="currentColor" strokeWidth="1.2" />
      <line x1="1" y1="13" x2="25" y2="13" stroke="currentColor" strokeWidth="1.2" />
      <rect x="1" y="1" width="12" height="24" fill="none" stroke="currentColor" strokeWidth="2.4" />
      <rect x="15" y="15" width="8" height="8" fill="var(--blue)" />
    </svg>
  );
}
