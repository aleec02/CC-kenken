import Link from "next/link";
import {
  ArrowRight, Braces, Camera, Database, Eye, GitBranch, Layers, Server, Sigma, Terminal, Wand2, Workflow,
} from "lucide-react";
import { Item, Reveal, Stagger } from "@/components/motion";
import { PipelineDiagram, RuleCage, RuleCol, RuleRow } from "@/components/RuleBoards";

const rules = [
  { Board: RuleRow, title: "Cada fila usa todos los números una vez", text: "En un tablero de 4×4 van del 1 al 4; en uno de 6×6, del 1 al 6. Nunca se repiten en la misma fila." },
  { Board: RuleCol, title: "Cada columna también", text: "Igual que en un sudoku: ningún número se repite en una columna." },
  { Board: RuleCage, title: "Cada jaula cumple su pista", text: "Las zonas de borde grueso son jaulas. Sus números, combinados con la operación indicada, deben dar el resultado. Aquí 1 × 3 × 2 = 6." },
];

const phases = [
  {
    n: "Fase 1",
    icon: Eye,
    title: "Ver el tablero",
    text: "Limpiamos la foto, encontramos la grilla aunque esté torcida, la enderezamos y detectamos cuántas celdas tiene. Después separamos las jaulas por el grosor de las líneas y leemos cada pista con un lector de símbolos propio, entrenado solo con los 15 caracteres que puede tener una pista.",
  },
  {
    n: "Fase 2",
    icon: Sigma,
    title: "Plantearlo como reglas",
    text: "Cada celda es una incógnita de 1 a N. Añadimos la regla de 'todos distintos' por fila y columna y una regla aritmética por jaula. Un solver (OR-Tools CP-SAT) deduce la única grilla que cumple todo, normalmente sin tener que probar opciones.",
  },
  {
    n: "Fase 3",
    icon: Wand2,
    title: "Corregir y mostrar",
    text: "Si la lectura de alguna pista no encaja con el resto, el propio solver elige la interpretación más probable que sí funciona. Al final proyectamos los números sobre tu foto respetando la perspectiva del papel.",
  },
];

const stack = [
  { icon: Camera, name: "OpenCV", desc: "Procesamiento de la imagen y geometría" },
  { icon: Layers, name: "OCR propio (k-NN)", desc: "Lectura de pistas sin modelos externos" },
  { icon: Sigma, name: "OR-Tools CP-SAT", desc: "Solver de programación con restricciones" },
  { icon: Server, name: "FastAPI", desc: "API HTTP que expone el pipeline" },
  { icon: Terminal, name: "CLI (Typer)", desc: "Mismos comandos que la API, desde la terminal" },
  { icon: Braces, name: "Next.js + TypeScript", desc: "Esta interfaz web" },
  { icon: Workflow, name: "Framer Motion", desc: "Animaciones de la interfaz" },
  { icon: Database, name: "Dataset propio", desc: "30 puzzles reales etiquetados + 28 sintéticos" },
];

const team = [
  { name: "Bedia Torres, Marcos Aaron", phase: "Fase 1", role: "Extracción y limpieza de datos", icon: Eye },
  { name: "Conza Hualpa, Alexia Evelyn", phase: "Fase 2", role: "Modelado y resolución", icon: Sigma },
  { name: "Rojas Vélez De Villa, Sebastián", phase: "Fase 3", role: "Entrenamiento, integración, visualización y despliegue", icon: GitBranch },
];

export default function About() {
  return (
    <main className="flex flex-1 flex-col">
      {/* Encabezado */}
      <section className="border-b border-line">
        <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 lg:py-20">
          <Stagger mode="mount">
            <Item as="p" className="font-mono text-xs uppercase tracking-[0.16em] text-blue">Cómo funciona</Item>
            <Item as="h1" className="mt-4 max-w-2xl text-4xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-5xl">
              Un KenKen es un sudoku con aritmética. Así lo leemos y lo resolvemos.
            </Item>
            <Item as="p" className="mt-6 max-w-2xl text-lg leading-8 text-ink-2">
              KenKenLab es un proyecto académico del curso CC58. Une dos áreas: visión computacional, para
              entender la foto, y programación con restricciones, para encontrar la solución.
            </Item>
          </Stagger>
        </div>
      </section>

      {/* Reglas */}
      <section className="border-b border-line bg-paper-2">
        <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 lg:py-20">
          <Reveal>
            <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Las tres reglas del juego</h2>
          </Reveal>
          <Stagger className="mt-10 grid gap-6 md:grid-cols-3">
            {rules.map((r, i) => (
              <Item key={r.title} className="flex flex-col rounded-lg border border-line bg-paper p-6">
                <div className="mb-6 flex items-start justify-between gap-4">
                  <div className="w-28 shrink-0 sm:w-32"><r.Board /></div>
                  <span className="font-mono text-xs text-ink-3">Regla {i + 1}</span>
                </div>
                <h3 className="text-[17px] font-semibold leading-snug text-ink">{r.title}</h3>
                <p className="mt-2 text-[15px] leading-7 text-ink-2">{r.text}</p>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      {/* Pipeline */}
      <section className="border-b border-line">
        <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 lg:py-20">
          <Reveal>
            <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">De la foto a la solución</h2>
            <p className="mt-3 max-w-2xl text-ink-2">El sistema trabaja en tres fases encadenadas. Todo ocurre de forma automática, sin intervención manual.</p>
          </Reveal>
          <Reveal delay={0.1} className="mt-10 rounded-lg border border-line bg-white p-4 sm:p-8">
            <PipelineDiagram />
          </Reveal>
          <Stagger className="mt-8 grid gap-px overflow-hidden rounded-lg border border-line bg-line lg:grid-cols-3">
            {phases.map((p) => (
              <Item key={p.n} className="bg-paper p-7">
                <div className="flex items-center justify-between">
                  <p.icon size={22} className="text-blue" strokeWidth={1.75} />
                  <span className="font-mono text-xs text-ink-3">{p.n}</span>
                </div>
                <h3 className="mt-6 text-lg font-semibold text-ink">{p.title}</h3>
                <p className="mt-2 text-[15px] leading-7 text-ink-2">{p.text}</p>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      {/* Stack */}
      <section className="border-b border-line bg-paper-2">
        <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 lg:py-20">
          <Reveal>
            <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Con qué está hecho</h2>
          </Reveal>
          <Stagger className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {stack.map((s) => (
              <Item key={s.name} className="flex gap-4 rounded-lg border border-line bg-paper p-5">
                <s.icon size={20} className="mt-0.5 shrink-0 text-blue" strokeWidth={1.75} />
                <div>
                  <p className="font-medium text-ink">{s.name}</p>
                  <p className="mt-1 text-sm leading-6 text-ink-2">{s.desc}</p>
                </div>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      {/* Equipo */}
      <section className="border-b border-line">
        <div className="mx-auto w-full max-w-6xl px-5 py-16 sm:px-8 lg:py-20">
          <Reveal>
            <h2 className="text-2xl font-semibold tracking-tight text-ink sm:text-3xl">Equipo</h2>
            <p className="mt-3 text-ink-2">Cada integrante lideró una fase del sistema.</p>
          </Reveal>
          <Stagger className="mt-10 grid gap-4 md:grid-cols-3">
            {team.map((m) => (
              <Item key={m.name} className="rounded-lg border border-line bg-paper p-6">
                <div className="flex h-11 w-11 items-center justify-center rounded-md border border-line-2 text-ink">
                  <m.icon size={20} strokeWidth={1.75} />
                </div>
                <p className="mt-5 font-mono text-xs text-blue">{m.phase}</p>
                <p className="mt-1 text-[17px] font-semibold leading-snug text-ink">{m.name}</p>
                <p className="mt-2 text-sm leading-6 text-ink-2">{m.role}</p>
              </Item>
            ))}
          </Stagger>
        </div>
      </section>

      <section>
        <div className="mx-auto flex w-full max-w-6xl flex-col items-start justify-between gap-6 px-5 py-14 sm:flex-row sm:items-center sm:px-8">
          <Reveal>
            <h2 className="text-2xl font-semibold tracking-tight text-ink">¿Listo para probarlo?</h2>
          </Reveal>
          <Reveal delay={0.1}>
            <Link href="/solver" className="group inline-flex h-12 items-center gap-2 rounded-md bg-ink px-6 text-[15px] font-medium text-paper transition-colors hover:bg-blue">
              Ir al solver <ArrowRight size={18} className="transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Reveal>
        </div>
      </section>
    </main>
  );
}
