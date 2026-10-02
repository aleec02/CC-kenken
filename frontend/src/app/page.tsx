import Link from "next/link";
import { ArrowRight, Camera, FileText, Grid3x3, Image as ImageIcon, ScanLine, Sigma } from "lucide-react";
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

const facts = [
  { value: "3–9", label: "tamaños de tablero" },
  { value: "< 1 s", label: "tiempo típico por foto" },
  { value: "100 %", label: "de fotos de prueba resueltas" },
  { value: "0", label: "pasos manuales" },
];

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      {/* Hero */}
      <section className="border-b border-line">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:py-24">
          <Stagger mode="mount">
            <Item as="p" className="font-mono text-xs uppercase tracking-[0.16em] text-blue">
              Visión computacional + programación con restricciones
            </Item>
            <Item as="h1" className="mt-5 text-[2.6rem] font-semibold leading-[1.05] tracking-tight text-ink sm:text-6xl">
              Fotografía un KenKen.
              <br />
              Recibe la solución.
            </Item>
            <Item as="p" className="mt-6 max-w-lg text-lg leading-8 text-ink-2">
              Sube una foto o un PDF del puzzle. KenKenLab lo lee, lo resuelve y te devuelve la
              respuesta dibujada sobre tu imagen en menos de un segundo.
            </Item>
            <Item className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/solver"
                className="group inline-flex h-12 items-center justify-center gap-2 rounded-md bg-ink px-6 text-[15px] font-medium text-paper transition-colors hover:bg-blue"
              >
                Resolver un puzzle
                <ArrowRight size={18} className="transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link
                href="/about"
                className="inline-flex h-12 items-center justify-center rounded-md border border-line-2 px-6 text-[15px] font-medium text-ink transition-colors hover:bg-paper-2"
              >
                Cómo funciona
              </Link>
            </Item>
            <Item className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-ink-3">
              <span className="inline-flex items-center gap-1.5"><Camera size={15} /> Fotos de celular</span>
              <span className="inline-flex items-center gap-1.5"><FileText size={15} /> PDFs</span>
              <span className="inline-flex items-center gap-1.5"><Grid3x3 size={15} /> Tableros de 3×3 a 9×9</span>
            </Item>
          </Stagger>

          <Reveal mode="mount" delay={0.15} className="mx-auto w-full max-w-md lg:max-w-none">
            <div className="rounded-lg border border-line bg-white p-5 sm:p-7">
              <KenKenMockup />
            </div>
          </Reveal>
        </div>
      </section>

      {/* Datos */}
      <section className="border-b border-line bg-paper-2">
        <Stagger className="mx-auto grid w-full max-w-6xl grid-cols-2 divide-line px-5 sm:px-8 md:grid-cols-4 md:divide-x">
          {facts.map((f) => (
            <Item key={f.label} className="py-8 md:px-8 md:first:pl-0">
              <p className="font-mono text-3xl font-medium tracking-tight text-ink">{f.value}</p>
              <p className="mt-1 text-sm text-ink-2">{f.label}</p>
            </Item>
          ))}
        </Stagger>
      </section>

      {/* Pasos */}
      <section className="border-b border-line">
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

      {/* CTA */}
      <section>
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start justify-between gap-6 px-5 py-16 sm:flex-row sm:items-center sm:px-8">
          <Reveal>
            <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">¿Tienes un KenKen a mano?</h2>
            <p className="mt-2 text-ink-2">Pruébalo ahora. No necesitas crear una cuenta.</p>
          </Reveal>
          <Reveal delay={0.1}>
            <Link
              href="/solver"
              className="group inline-flex h-12 items-center gap-2 rounded-md bg-blue px-6 text-[15px] font-medium text-white transition-colors hover:bg-blue-2"
            >
              Ir al solver
              <ArrowRight size={18} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Reveal>
        </div>
      </section>
    </main>
  );
}
