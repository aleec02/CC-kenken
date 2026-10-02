import Link from "next/link";
import { ArrowRight, Github, Image as ImageIcon, ScanLine, Sigma } from "lucide-react";
import KenKenMockup from "@/components/KenKenMockup";
import { Item, Reveal, Stagger } from "@/components/motion";

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
          <Stagger mode="mount">
            <Item as="h1" className="text-[2.6rem] font-semibold leading-[1.05] tracking-tight text-ink sm:text-6xl">
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

          <Reveal mode="mount" delay={0.15} className="mx-auto w-full max-w-md lg:max-w-none">
            <div className="rounded-lg border border-line bg-white p-5 sm:p-7">
              <KenKenMockup />
            </div>
          </Reveal>
        </div>
      </section>

      {/* Tamaños permitidos */}
      <section className="border-b border-line bg-paper-2">
        <div className="mx-auto w-full max-w-6xl px-5 py-10 text-center sm:px-8">
          <Reveal>
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-ink-3">
              Tamaños de tablero permitidos
            </p>
          </Reveal>
          <Stagger className="mt-5 flex flex-wrap justify-center gap-2">
            {sizes.map((s) => (
              <Item
                key={s}
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
          <Stagger className="mt-12 grid gap-px overflow-hidden rounded-lg border border-line bg-line md:grid-cols-3">
            {steps.map((s, i) => (
              <Item key={s.title} className="bg-paper p-7">
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
    </main>
  );
}
