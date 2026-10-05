/* Mini tableros SVG para explicar las reglas del KenKen. */

const C = 44;
const P = 3;

function Board({ n, children }: { n: number; children: React.ReactNode }) {
  const side = n * C + P * 2;
  return (
    <svg viewBox={`0 0 ${side} ${side}`} className="h-auto w-full max-w-[200px]" aria-hidden>
      <rect x={0} y={0} width={side} height={side} fill="#fff" />
      {Array.from({ length: n - 1 }, (_, i) => i + 1).map((i) => (
        <g key={i} stroke="var(--line)" strokeWidth={1.2}>
          <line x1={P + i * C} y1={P} x2={P + i * C} y2={side - P} />
          <line x1={P} y1={P + i * C} x2={side - P} y2={P + i * C} />
        </g>
      ))}
      {children}
      <rect x={P} y={P} width={n * C} height={n * C} fill="none" stroke="var(--ink)" strokeWidth={3} />
    </svg>
  );
}

const digit = (r: number, c: number, v: string | number, color = "var(--ink)") => (
  <text
    key={`${r}${c}`}
    x={P + c * C + C / 2}
    y={P + r * C + C / 2 + 8}
    textAnchor="middle"
    fontSize={22}
    fontWeight={600}
    fill={color}
    fontFamily="var(--font-geist-mono), ui-monospace, monospace"
  >
    {v}
  </text>
);

const clue = (r: number, c: number, t: string) => (
  <text key={`k${r}${c}`} x={P + c * C + 5} y={P + r * C + 13} fontSize={9.5} fontWeight={700} fill="var(--ink)">
    {t}
  </text>
);

const hl = (r: number, c: number) => (
  <rect key={`h${r}${c}`} x={P + c * C} y={P + r * C} width={C} height={C} fill="var(--blue-soft)" />
);

/** Regla 1: fila sin repetir. */
export function RuleRow() {
  return (
    <Board n={4}>
      {[0, 1, 2, 3].map((c) => hl(1, c))}
      {digit(1, 0, 3, "var(--blue)")}
      {digit(1, 1, 1, "var(--blue)")}
      {digit(1, 2, 4, "var(--blue)")}
      {digit(1, 3, 2, "var(--blue)")}
    </Board>
  );
}

/** Regla 2: columna sin repetir. */
export function RuleCol() {
  return (
    <Board n={4}>
      {[0, 1, 2, 3].map((r) => hl(r, 2))}
      {digit(0, 2, 4, "var(--blue)")}
      {digit(1, 2, 2, "var(--blue)")}
      {digit(2, 2, 1, "var(--blue)")}
      {digit(3, 2, 3, "var(--blue)")}
    </Board>
  );
}

/** Regla 3: la jaula cumple su operación. */
export function RuleCage() {
  return (
    <Board n={4}>
      {hl(0, 0)}
      {hl(0, 1)}
      {hl(1, 0)}
      <path
        d={`M${P} ${P} H${P + 2 * C} V${P + C} H${P + C} V${P + 2 * C} H${P} Z`}
        fill="none"
        stroke="var(--ink)"
        strokeWidth={3.5}
        strokeLinejoin="miter"
      />
      {clue(0, 0, "6×")}
      {digit(0, 0, 1, "var(--blue)")}
      {digit(0, 1, 3, "var(--blue)")}
      {digit(1, 0, 2, "var(--blue)")}
    </Board>
  );
}

/** Pipeline: foto → lectura → modelo → solución. */
export function PipelineDiagram() {
  return (
    <svg viewBox="0 0 760 150" className="h-auto w-full" role="img" aria-label="Flujo: foto, lectura, modelo matemático, solución">
      {[
        { x: 10, label: "Foto o PDF", sub: "entrada" },
        { x: 200, label: "Lectura", sub: "tablero + pistas" },
        { x: 390, label: "Modelo", sub: "reglas (CSP)" },
        { x: 580, label: "Solución", sub: "sobre tu imagen" },
      ].map((b, i) => (
        <g key={b.label}>
          <rect x={b.x} y={30} width={170} height={90} rx={6} fill="#fff" stroke="var(--ink)" strokeWidth={2} />
          <text x={b.x + 85} y={72} textAnchor="middle" fontSize={17} fontWeight={600} fill="var(--ink)">{b.label}</text>
          <text x={b.x + 85} y={96} textAnchor="middle" fontSize={12} fill="var(--ink-3)" fontFamily="var(--font-geist-mono), monospace">{b.sub}</text>
          <text x={b.x + 12} y={48} fontSize={11} fill="var(--blue)" fontFamily="var(--font-geist-mono), monospace">0{i + 1}</text>
          {i < 3 && (
            <g stroke="var(--blue)" strokeWidth={2} fill="none">
              <line x1={b.x + 170} y1={75} x2={b.x + 196} y2={75} />
              <polyline points={`${b.x + 190},69 ${b.x + 196},75 ${b.x + 190},81`} />
            </g>
          )}
        </g>
      ))}
      {/* bucle de corrección */}
      <g stroke="var(--ink-3)" strokeWidth={1.5} fill="none" strokeDasharray="4 4">
        <path d="M475 120 V140 H285 V120" />
        <polyline points="279,126 285,120 291,126" />
      </g>
      <text x={380} y={147} textAnchor="middle" fontSize={11} fill="var(--ink-3)" fontFamily="var(--font-geist-mono), monospace">
        si no cuadra, se corrige la lectura
      </text>
    </svg>
  );
}
