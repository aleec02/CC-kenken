"use client";

import { motion, type Variants } from "framer-motion";
import type { ReactNode } from "react";

const ease = [0.22, 1, 0.36, 1] as const;

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease } },
};

export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08, delayChildren: 0.05 } },
};

type Tag = "div" | "section" | "li" | "p" | "h1" | "h2" | "span";

interface RevealProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  as?: Tag;
  /** "mount": anima al cargar (contenido visible de entrada). "view": anima al hacer scroll. */
  mode?: "mount" | "view";
}

// Dispara la entrada en cuanto el elemento asoma por el borde inferior: sin pop tardío.
const viewport = { once: true, margin: "0px 0px -60px 0px" } as const;

function trigger(mode: "mount" | "view") {
  return mode === "mount"
    ? { initial: "hidden", animate: "show" }
    : { initial: "hidden", whileInView: "show", viewport };
}

/** Entrada de un bloque (al montar o al hacer scroll). */
export function Reveal({ children, className, delay = 0, as = "div", mode = "view" }: RevealProps) {
  const M = motion[as];
  return (
    <M
      className={className}
      {...trigger(mode)}
      variants={{
        hidden: { opacity: 0, y: 16 },
        show: { opacity: 1, y: 0, transition: { duration: 0.55, ease, delay } },
      }}
    >
      {children}
    </M>
  );
}

/** Contenedor que escalona la entrada de sus hijos `<Item>`. */
export function Stagger({ children, className, as = "div", mode = "view" }: Omit<RevealProps, "delay">) {
  const M = motion[as];
  return (
    <M className={className} {...trigger(mode)} variants={stagger}>
      {children}
    </M>
  );
}

export function Item({ children, className, as = "div" }: Omit<RevealProps, "delay" | "mode">) {
  const M = motion[as];
  return (
    <M className={className} variants={fadeUp}>
      {children}
    </M>
  );
}
