"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Github } from "lucide-react";

/** Barra flotante con los dos CTA del hero, solo en móvil y tras hacer scroll. */
export default function FloatingCtas() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > window.innerHeight * 0.45);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ y: 72, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 72, opacity: 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="fixed inset-x-4 bottom-4 z-50 flex gap-2 sm:hidden"
        >
          <Link
            href="/solver"
            className="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-md bg-ink text-[15px] font-medium text-paper shadow-[0_10px_24px_-12px_rgba(21,22,26,0.5)] transition-colors active:bg-blue"
          >
            Resolver un puzzle
            <ArrowRight size={18} />
          </Link>
          <a
            href="https://github.com/aleec02/CC-kenken"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Ver el proyecto en GitHub"
            className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-md border border-line-2 bg-paper text-ink shadow-[0_10px_24px_-12px_rgba(21,22,26,0.5)] transition-colors active:bg-paper-2"
          >
            <Github size={19} />
          </a>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
