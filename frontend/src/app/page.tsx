import Link from "next/link";
import type { Variants } from "framer-motion";
import { ArrowRight, Github, Image as ImageIcon, ScanLine, Sigma } from "lucide-react";
import KenKenMockup from "@/components/KenKenMockup";
import FloatingCtas from "@/components/FloatingCtas";
import { Item, Reveal, Stagger } from "@/components/motion";

const ease = [0.22, 1, 0.36, 1] as const;

// Orquestación de entrada: cada sección entra distinto.
const heroStagger: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.11, delayChildren: 0.05 } } };
const titleRise: Variants = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0, transition: { duration: 0.7, ease } },
};
const mockSlide: Variants = {
  hidden: { opacity: 0, x: 34, scale: 0.96 },
  show: { opacity: 1, x: 0, scale: 1, transition: { duration: 0.75, ease, delay: 0.3 } },
};
const fadeOnly: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.6, ease } },
};
const chipStagger: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.045 } } };
const chipPop: Variants = {
  hidden: { opacity: 0, scale: 0.8, y: 8 },
  show: { opacity: 1, scale: 1, y: 0, transition: { type: "spring", stiffness: 380, damping: 22 } },
};
const cardStagger: Variants = { hidden: {}, show: { transition: { staggerChildren: 0.13, delayChildren: 0.08 } } };
const cardRise: Variants = {
  hidden: { opacity: 0, y: 34 },
  show: { opacity: 1, y: 0, transition: { duration: 0.65, ease } },
};

const steps = [
  {
    icon: ScanLine,
    title: "Leemos tu foto",
    text: "Encontramos el tablero aunque esté inclinado, separamos las jaulas y leemos cada pista (número y operación).",
  },
  {
    icon: Sigma,
    title: "Lo resolvemos",
    text: "El puzzle se convierte en un conjunto de reglas matemáticas y un solver encuentra la única grilla que las cumple.",
  },
  {
    icon: ImageIcon,
    title: "Te lo mostramos",
    text: "Dibujamos la solución sobre tu propia imagen y también en un tablero limpio para que la compares.",
  },
];

const sizes = ["3x3", "4x4", "5x5", "6x6", "7x7", "8x8", "9x9"];

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      {/* Hero */}
      <section className="border-b border-line">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:py-24">
          <Stagger mode="mount" variants={heroStagger}>
            <Item as="h1" variants={titleRise} className="text-[2.6rem] font-semibold leading-[1.05] tracking-tight text-ink sm:text-6xl">
              Envía un KenKen,
              <br />
              recibe la solución.
            </Item>
            <Item as="p" className="mt-6 max-w-lg text-lg leading-8 text-ink-2">
              Sube una foto o una imagen del puzzle. KenKenLab lo lee, lo resuelve y te devuelve la
              respuesta dibujada sobre tu imagen.
            </Item>
            <Item className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/solver"
                className="group inline-flex h-12 items-center justify-center gap-2 rounded-md bg-ink px-6 text-[15px] font-medium text-paper transition-colors hover:bg-blue"
              >
                Resolver un puzzle
                <ArrowRight size={18} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a
                href="https://github.com/aleec02/CC-kenken"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex h-12 items-center justify-center gap-2 rounded-md border border-line-2 px-6 text-[15px] font-medium text-ink transition-colors hover:bg-paper-2"
              >
                <Github size={18} />
                Ver el proyecto
              </a>
            </Item>
          </Stagger>

          <Reveal mode="mount" variants={mockSlide} className="mx-auto w-full max-w-md lg:max-w-none">
            <div className="rounded-lg border border-line bg-white p-5 sm:p-7">
              <KenKenMockup />
            </div>
          </Reveal>
        </div>
      </section>

      {/* Tamaños permitidos */}
      <section className="border-b border-line bg-paper-2">
        <div className="mx-auto w-full max-w-6xl px-5 py-10 text-center sm:px-8">
          <Reveal variants={fadeOnly}>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-ink-3">
              Tamaños de tablero permitidos
            </p>
          </Reveal>
          <Stagger variants={chipStagger} className="mt-5 flex flex-wrap justify-center gap-2">
            {sizes.map((s) => (
              <Item
                key={s}
                variants={chipPop}
                className="rounded-md border border-line bg-paper px-4 py-2 font-mono text-sm text-ink"
              >
                {s}
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      {/* Pasos */}
      <section>
        <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 lg:py-24">
          <Reveal>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-ink-3">En tres pasos</p>
            <h2 className="mt-3 max-w-xl text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
              Sin escribir nada a mano. Tú tomas la foto, nosotros hacemos el resto.
            </h2>
          </Reveal>
          <Stagger variants={cardStagger} className="mt-12 grid gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-3">
            {steps.map((s, i) => (
              <Item key={s.title} variants={cardRise} className="bg-paper p-7">
                <div className="flex items-center justify-between">
                  <s.icon size={22} className="text-blue" strokeWidth={1.75} />
                  <span className="font-mono text-xs text-ink-3">0{i + 1}</span>
                </div>
                <h3 className="mt-6 text-lg font-semibold text-ink">{s.title}</h3>
                <p className="mt-2 text-[15px] leading-7 text-ink-2">{s.text}</p>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      <FloatingCtas />
    </main>
  );
}
