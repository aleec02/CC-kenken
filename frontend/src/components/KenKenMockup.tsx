"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

// Puzzle 4x4 real con solución única (el mismo ejemplo de los tests del backend).
const N = 4;
const CAGES: { clue: string; cells: [number, number][] }[] = [
  { clue: "2−", cells: [[0, 0], [0, 1]] },
  { clue: "2÷", cells: [[0, 2], [0, 3]] },
  { clue: "3−", cells: [[1, 0], [1, 1]] },
  { clue: "3+", cells: [[1, 2], [2, 2]] },
  { clue: "1−", cells: [[1, 3], [2, 3]] },
  { clue: "6×", cells: [[2, 0], [3, 0]] },
  { clue: "2÷", cells: [[2, 1], [3, 1]] },
  { clue: "4+", cells: [[3, 2], [3, 3]] },
];
const SOLUTION = [
  [1, 3, 4, 2],
  [4, 1, 2, 3],
  [3, 2, 1, 4],
  [2, 4, 3, 1],
];

// Orden en que "el solver" va llenando (recorre por jaulas: se siente deductivo).
const ORDER: [number, number][] = CAGES.flatMap((c) => c.cells);

const CELL = 84;
const PAD = 6;
const SIDE = N * CELL + PAD * 2;
const STEP_MS = 230;
const HOLD_MS = 2600;
const EMPTY_MS = 900;

const owner = (r: number, c: number) => CAGES.findIndex((k) => k.cells.some(([a, b]) => a === r && b === c));

function thickEdges() {
  const edges: { x1: number; y1: number; x2: number; y2: number }[] = [];
  for (let r = 0; r < N; r++)
    for (let c = 1; c < N; c++)
      if (owner(r, c - 1) !== owner(r, c))
        edges.push({ x1: PAD + c * CELL, y1: PAD + r * CELL, x2: PAD + c * CELL, y2: PAD + (r + 1) * CELL });
  for (let r = 1; r < N; r++)
    for (let c = 0; c < N; c++)
      if (owner(r - 1, c) !== owner(r, c))
        edges.push({ x1: PAD + c * CELL, y1: PAD + r * CELL, x2: PAD + (c + 1) * CELL, y2: PAD + r * CELL });
  return edges;
}
const THICK = thickEdges();

export default function KenKenMockup({ className }: { className?: string }) {
  const [filled, setFilled] = useState(0); // cuántas celdas de ORDER están rellenas
  const [phase, setPhase] = useState<"empty" | "filling" | "done">("empty");

  useEffect(() => {
    const next = () => {
      if (phase === "empty") setPhase("filling");
      else if (phase === "filling") {
        if (filled < ORDER.length) setFilled((v) => v + 1);
        else setPhase("done");
      } else { setFilled(0); setPhase("empty"); }
    };
    const delay = phase === "empty" ? EMPTY_MS : phase === "filling" ? (filled < ORDER.length ? STEP_MS : 0) : HOLD_MS;
    const t = setTimeout(next, delay);
    return () => clearTimeout(t);
  }, [phase, filled]);

  const cursor = phase === "filling" && filled < ORDER.length ? ORDER[filled] : null;
  const status = phase === "empty" ? "Leyendo pistas…" : phase === "filling" ? "Resolviendo…" : "Solución única";

  return (
    <div className={className}>
      <svg viewBox={`0 0 ${SIDE} ${SIDE}`} className="h-auto w-full" role="img" aria-label="Demostración de un KenKen 4×4 resolviéndose">
        <rect x={0} y={0} width={SIDE} height={SIDE} fill="#fff" />

        {/* cursor del solver */}
        <AnimatePresence>
          {cursor && (
            <motion.rect
              key="cursor"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1, x: PAD + cursor[1] * CELL, y: PAD + cursor[0] * CELL }}
              exit={{ opacity: 0 }}
              transition={{ type: "spring", stiffness: 420, damping: 36 }}
              width={CELL}
              height={CELL}
              fill="var(--blue-soft)"
            />
          )}
        </AnimatePresence>

        {/* líneas finas */}
        {Array.from({ length: N - 1 }, (_, i) => i + 1).map((i) => (
          <g key={i} stroke="var(--line)" strokeWidth={1.5}>
            <line x1={PAD + i * CELL} y1={PAD} x2={PAD + i * CELL} y2={SIDE - PAD} />
            <line x1={PAD} y1={PAD + i * CELL} x2={SIDE - PAD} y2={PAD + i * CELL} />
          </g>
        ))}

        {/* bordes de jaula */}
        <g stroke="var(--ink)" strokeWidth={4} strokeLinecap="square">
          {THICK.map((e, i) => (
            <motion.line
              key={i}
              {...e}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 0.5, delay: 0.25 + i * 0.03, ease: "easeOut" }}
            />
          ))}
          <motion.rect
            x={PAD} y={PAD} width={N * CELL} height={N * CELL} fill="none" strokeWidth={5}
            initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.9, ease: "easeInOut" }}
          />
        </g>

        {/* pistas */}
        {CAGES.map((k, i) => {
          const [r, c] = k.cells[0];
          return (
            <motion.text
              key={i}
              x={PAD + c * CELL + 9}
              y={PAD + r * CELL + 22}
              fontSize={15}
              fontWeight={700}
              fill="var(--ink)"
              fontFamily="var(--font-geist-sans), system-ui, sans-serif"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.6 + i * 0.05 }}
            >
              {k.clue}
            </motion.text>
          );
        })}

        {/* dígitos de la solución */}
        <AnimatePresence>
          {ORDER.slice(0, filled).map(([r, c]) => (
            <motion.text
              key={`${r}-${c}`}
              x={PAD + c * CELL + CELL / 2}
              y={PAD + r * CELL + CELL / 2 + 16}
              textAnchor="middle"
              fontSize={36}
              fontWeight={600}
              fill={phase === "done" ? "var(--ink)" : "var(--blue)"}
              fontFamily="var(--font-geist-mono), ui-monospace, monospace"
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, transition: { duration: 0.35 } }}
              transition={{ type: "spring", stiffness: 520, damping: 28 }}
              style={{ transformOrigin: `${PAD + c * CELL + CELL / 2}px ${PAD + r * CELL + CELL / 2}px`, transformBox: "view-box" }}
            >
              {SOLUTION[r][c]}
            </motion.text>
          ))}
        </AnimatePresence>
      </svg>

      <div className="mt-4 flex items-center justify-between font-mono text-xs text-ink-3">
        <span className="flex items-center gap-2">
          <span className={`inline-block h-2 w-2 rounded-full ${phase === "done" ? "bg-ok" : "bg-blue"}`} />
          <AnimatePresence mode="wait">
            <motion.span key={status} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.2 }}>
              {status}
            </motion.span>
          </AnimatePresence>
        </span>
        <span>{filled}/{N * N} celdas</span>
      </div>
    </div>
  );
}
