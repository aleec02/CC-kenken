"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle, Check, Download, FileText, Image as ImageIcon, Loader2, RotateCcw, Upload, X,
} from "lucide-react";
import {
  ACCEPTED_EXT, ApiError, health, prepareUpload, solveImage, validateFile, type SolveImageResponse,
} from "@/lib/api";
import { Item, Stagger } from "@/components/motion";

type Phase = "idle" | "ready" | "solving" | "done" | "error";
type View = "overlay" | "board" | "debug";

const ease = [0.22, 1, 0.36, 1] as const;

// Mensajes que rotan mientras el servidor trabaja.
const PROGRESS = ["Optimizando la imagen…", "Buscando el tablero…", "Leyendo las pistas…", "Resolviendo el puzzle…", "Dibujando la solución…"];

const OP_LABEL: Record<string, string> = { "+": "+", "-": "−", "*": "×", "/": "÷", "=": "", "?": "?" };

export default function Solver() {
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<SolveImageResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [view, setView] = useState<View>("overlay");
  const [dragging, setDragging] = useState(false);
  const [online, setOnline] = useState<boolean | null>(null);

  // Estado del servidor (se revisa al entrar y cada 15 s).
  useEffect(() => {
    const ctrl = new AbortController();
    const check = () => health(ctrl.signal).then(setOnline);
    check();
    const id = setInterval(check, 15000);
    return () => { clearInterval(id); ctrl.abort(); };
  }, []);

  // Mensajes de progreso.
  useEffect(() => {
    if (phase !== "solving") return;
    const id = setInterval(() => setProgress((p) => Math.min(p + 1, PROGRESS.length - 1)), 700);
    return () => clearInterval(id);
  }, [phase]);

  // Vista previa del archivo (solo imágenes).
  const preview = useMemo(
    () => (file && file.type !== "application/pdf" ? URL.createObjectURL(file) : null),
    [file],
  );
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const pick = useCallback((f: File | null) => {
    setResult(null);
    setError(null);
    if (!f) { setFile(null); setPhase("idle"); return; }
    const err = validateFile(f);
    if (err) { setFile(null); setError(err); setPhase("error"); return; }
    setFile(f);
    setPhase("ready");
  }, []);

  async function solve() {
    if (!file) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setProgress(0);
    setPhase("solving");
    setError(null);
    setResult(null);
    try {
      const upload = await prepareUpload(file);
      const res = await solveImage(upload, ctrl.signal);
      setResult(res);
      setView(res.images?.overlay ? "overlay" : "board");
      setPhase("done");
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(e instanceof ApiError ? e : new ApiError("unknown", "Ocurrió un error inesperado.", String(e)));
      setPhase("error");
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setPhase(file ? "ready" : "idle");
  }

  function reset() {
    abortRef.current?.abort();
    setFile(null);
    setResult(null);
    setError(null);
    setPhase("idle");
    if (inputRef.current) inputRef.current.value = "";
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files?.[0] ?? null);
  };

  return (
    <main className="flex flex-1 flex-col">
      <section className="border-b border-line">
        <div className="mx-auto w-full max-w-6xl px-5 py-12 sm:px-8 lg:py-16">
          <Stagger mode="mount">
            <Item as="p" className="font-mono text-xs uppercase tracking-[0.16em] text-blue">Solver</Item>
            <Item as="h1" className="mt-4 text-3xl font-semibold tracking-tight text-ink sm:text-5xl">
              Sube tu KenKen
            </Item>
            <Item className="mt-4 max-w-xl text-[15px] leading-7 text-ink-2 sm:text-base">
              Una foto del celular o imagen. Recibirás la solución dibujada sobre tu imagen.
            </Item>
          </Stagger>
        </div>
      </section>

      <section className="flex-1">
        <div className="mx-auto w-full max-w-6xl px-5 py-10 sm:px-8 lg:py-14">
          <AnimatePresence mode="wait">
            {phase !== "done" ? (
              <motion.div
                key="upload"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.4, ease }}
                className="mx-auto max-w-2xl"
              >
                <input
                  ref={inputRef}
                  type="file"
                  accept={ACCEPTED_EXT.join(",")}
                  className="sr-only"
                  onChange={(e) => pick(e.target.files?.[0] ?? null)}
                />

                {/* Dropzone */}
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => phase !== "solving" && inputRef.current?.click()}
                  onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
                  onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onDrop={onDrop}
                  className={`relative flex min-h-[260px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                    dragging ? "border-blue bg-blue-soft" : "border-line bg-white hover:border-ink-3"
                  } ${phase === "solving" ? "pointer-events-none" : ""}`}
                >
                  <AnimatePresence mode="wait">
                    {!file ? (
                      <motion.div key="empty" {...fade} className="flex flex-col items-center">
                        <div className="flex h-12 w-12 items-center justify-center rounded-md border border-line-2 text-ink">
                          <Upload size={22} strokeWidth={1.75} />
                        </div>
                        <p className="mt-5 text-lg font-medium text-ink">Arrastra el archivo aquí</p>
                        <p className="mt-1 text-sm text-ink-2">o haz clic para elegirlo desde tu dispositivo</p>
                        <p className="mt-5 font-mono text-xs text-ink-3">PNG · JPG · WEBP · BMP · PDF · máx. 15 MB</p>
                        <p className="mt-1 text-xs text-ink-3">Las fotos pesadas se optimizan automáticamente antes de enviarse.</p>
                      </motion.div>
                    ) : (
                      <motion.div key="file" {...fade} className="flex w-full flex-col items-center gap-5 sm:flex-row sm:text-left">
                        <div className="flex h-28 w-28 shrink-0 items-center justify-center overflow-hidden rounded-md border border-line bg-paper-2">
                          {preview ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={preview} alt="" className="h-full w-full object-cover" />
                          ) : (
                            <FileText size={32} className="text-ink-3" strokeWidth={1.5} />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate font-medium text-ink">{file.name}</p>
                          <p className="mt-1 text-sm text-ink-2">{(file.size / 1024).toFixed(0)} KB · listo para resolver</p>
                          {phase !== "solving" && (
                            <button
                              onClick={(e) => { e.stopPropagation(); reset(); }}
                              className="mt-3 inline-flex items-center gap-1.5 text-sm text-ink-2 underline-offset-4 hover:text-bad hover:underline"
                            >
                              <X size={14} /> Quitar archivo
                            </button>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Acciones */}
                <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <AnimatePresence mode="wait">
                    {phase === "solving" ? (
                      <motion.p key={progress} {...fade} className="inline-flex items-center gap-2 text-sm text-ink-2">
                        <Loader2 size={16} className="animate-spin text-blue" />
                        {PROGRESS[progress]}
                      </motion.p>
                    ) : (
                      <motion.p key="hint" {...fade} className="text-sm text-ink-3">
                        {file ? "Cuando quieras, pulsa Resolver." : "Consejo: que el tablero se vea completo y con buena luz."}
                      </motion.p>
                    )}
                  </AnimatePresence>
                  <div className="flex gap-2">
                    {phase === "solving" ? (
                      <button onClick={cancel} className="h-11 rounded-md border border-line-2 px-5 text-[15px] font-medium text-ink hover:bg-paper-2">
                        Cancelar
                      </button>
                    ) : (
                      <button
                        onClick={solve}
                        disabled={!file || online === false}
                        className="inline-flex h-11 items-center gap-2 rounded-md bg-ink px-6 text-[15px] font-medium text-paper transition-colors hover:bg-blue disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Resolver
                      </button>
                    )}
                  </div>
                </div>

                {/* Error */}
                <AnimatePresence>
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      role="alert"
                      className="mt-6 flex gap-3 rounded-lg border border-bad/30 bg-bad-soft p-5"
                    >
                      <AlertTriangle size={20} className="mt-0.5 shrink-0 text-bad" />
                      <div>
                        <p className="font-medium text-ink">{error.message}</p>
                        {error.hint && <p className="mt-1 text-sm leading-6 text-ink-2">{error.hint}</p>}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {online === false && !error && (
                  <p className="mt-6 flex items-start gap-2.5 rounded-lg border border-warn/30 bg-warn-soft p-4 text-sm leading-6 text-ink-2">
                    <span className="mt-2 inline-block h-2 w-2 shrink-0 rounded-full bg-bad" />
                    <span>
                      <strong className="font-medium text-ink">Servidor apagado.</strong>{" "}
                      Revisamos la conexión automáticamente; el botón Resolver se activará solo cuando vuelva.
                    </span>
                  </p>
                )}
              </motion.div>
            ) : (
              result && (
                <Results key="results" result={result} view={view} setView={setView} onReset={reset} fileName={file?.name ?? "kenken"} />
              )
            )}
          </AnimatePresence>
        </div>
      </section>
    </main>
  );
}

const fade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.2 },
};

function Results({
  result, view, setView, onReset, fileName,
}: { result: SolveImageResponse; view: View; setView: (v: View) => void; onReset: () => void; fileName: string }) {
  const { solution, extraction, corrections, timings, images } = result;
  const solved = solution.solved && solution.grid;
  const n = extraction.puzzle.size;
  const lowConf = extraction.detections.filter((d) => d.confidence < 0.85);

  const allViews: { id: View; label: string; src?: string }[] = [
    { id: "overlay", label: "Sobre tu imagen", src: images?.overlay },
    { id: "board", label: "Tablero limpio", src: images?.board },
    { id: "debug", label: "Qué detectamos", src: images?.debug },
  ];
  const views = allViews.filter((v) => v.src);
  const current = views.find((v) => v.id === view) ?? views[0];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease }}
    >
      {/* Resumen */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.16em] text-ink-3">
            {solved ? <Check size={14} className="text-ok" /> : <AlertTriangle size={14} className="text-bad" />}
            Resultado
          </p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">
            {solved
              ? solution.unique === false
                ? "Encontramos una solución, pero no es la única"
                : "Resuelto"
              : solution.status === "UNKNOWN"
                ? "Se agotó el tiempo"
                : "El OCR no logró identificar correctamente"}
          </h2>
          <p className="mt-2 max-w-xl text-[15px] leading-7 text-ink-2">
            {solved
              ? solution.unique === false
                ? "Un KenKen bien leído tiene una sola solución. Probablemente alguna pista se leyó mal; revisa la pestaña “Qué detectamos”."
                : `Tablero de ${n}×${n} con ${extraction.puzzle.cages.length} jaulas, resuelto en ${(timings.total_ms / 1000).toFixed(2)} s.`
              : solution.status === "UNKNOWN"
                ? "El solver no terminó dentro del límite. Prueba con una imagen más nítida."
                : "Leímos el tablero, pero el OCR no logró descifrar todos los símbolos o números. Por favor, intenta con otra imagen."}
          </p>
        </div>
        <button onClick={onReset} className="inline-flex h-11 shrink-0 items-center gap-2 rounded-md border border-line-2 px-5 text-[15px] font-medium text-ink hover:bg-paper-2">
          <RotateCcw size={16} /> Resolver otro
        </button>
      </div>

      {/* Avisos */}
      <Stagger className="mt-8 space-y-3">
        {corrections.length > 0 && (
          <Item className="rounded-lg border border-warn/30 bg-warn-soft p-5">
            <p className="font-medium text-ink">Corregimos {corrections.length} {corrections.length === 1 ? "pista" : "pistas"} para que el puzzle tuviera solución</p>
            <ul className="mt-2 grid gap-1 text-sm text-ink-2 sm:grid-cols-2">
              {corrections.map((c, i) => (
                <li key={i} className="font-mono">
                  fila {c.cell[0] + 1}, col {c.cell[1] + 1}: <s>{c.read}</s> → <strong className="text-ink">{c.corrected}</strong>
                </li>
              ))}
            </ul>
          </Item>
        )}
        {lowConf.length > 0 && (
          <Item className="rounded-lg border border-line bg-paper-2 p-5">
            <p className="font-medium text-ink">{lowConf.length} {lowConf.length === 1 ? "pista con lectura dudosa" : "pistas con lectura dudosa"}</p>
            <ul className="mt-2 grid gap-1 text-sm text-ink-2 sm:grid-cols-2">
              {lowConf.map((d, i) => (
                <li key={i} className="font-mono">
                  fila {d.clue_cell[0] + 1}, col {d.clue_cell[1] + 1}: “{d.ocr_text}” · {(d.confidence * 100).toFixed(0)} % seguro
                </li>
              ))}
            </ul>
          </Item>
        )}
      </Stagger>

      {/* Imágenes + grilla */}
      <div className="mt-8 grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <Stagger className="rounded-lg border border-line bg-white">
          <Item className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
            <div className="flex gap-1">
              {views.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setView(v.id)}
                  className={`relative rounded-md px-3 py-1.5 text-sm transition-colors ${view === v.id ? "text-ink" : "text-ink-3 hover:text-ink"}`}
                >
                  {v.label}
                  {view === v.id && <motion.span layoutId="view-tab" className="absolute inset-x-3 -bottom-[13px] h-0.5 bg-blue" />}
                </button>
              ))}
            </div>
            {current?.src && (
              <a
                href={current.src}
                download={`${fileName.replace(/\.[^.]+$/, "")}_${current.id}.png`}
                className="inline-flex items-center gap-1.5 text-sm text-ink-2 hover:text-blue"
              >
                <Download size={15} /> Descargar
              </a>
            )}
          </Item>
          <Item className="p-4">
            <AnimatePresence mode="wait">
              {current?.src ? (
                <motion.img
                  key={current.id}
                  src={current.src}
                  alt={current.label}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.25 }}
                  className="mx-auto max-h-[640px] w-auto max-w-full rounded-md"
                />
              ) : (
                <div className="flex h-64 items-center justify-center text-ink-3"><ImageIcon /></div>
              )}
            </AnimatePresence>
          </Item>
        </Stagger>

        <div className="space-y-6">
          {solution.grid && (
            <motion.div
              initial="hidden"
              animate="show"
              variants={{ show: { transition: { staggerChildren: 0.02, delayChildren: 0.2 } } }}
              className="rounded-lg border border-line bg-white p-5"
            >
              <p className="font-mono text-xs uppercase tracking-[0.14em] text-ink-3">Solución</p>
              <div className="mt-4 grid aspect-square gap-px border-2 border-ink bg-line" style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}>
                {solution.grid.flatMap((row, r) =>
                  row.map((v, c) => (
                    <motion.div
                      key={`${r}-${c}`}
                      variants={{ hidden: { opacity: 0, scale: 0.7 }, show: { opacity: 1, scale: 1 } }}
                      className="flex items-center justify-center bg-white font-mono text-lg font-semibold text-ink sm:text-xl"
                    >
                      {v}
                    </motion.div>
                  )),
                )}
              </div>
            </motion.div>
          )}

          <div className="rounded-lg border border-line bg-white p-5">
            <p className="font-mono text-xs uppercase tracking-[0.14em] text-ink-3">Detalles</p>
            <dl className="mt-4 divide-y divide-line text-sm">
              <Row k="Tamaño" v={`${n} × ${n}`} />
              <Row k="Jaulas" v={String(extraction.puzzle.cages.length)} />
              <Row k="Lectura de la imagen" v={`${timings.vision_ms.toFixed(0)} ms`} />
              <Row k="Resolución" v={`${timings.solver_ms.toFixed(1)} ms`} />
              <Row k="Solución única" v={solution.unique === null ? "no verificado" : solution.unique ? "sí" : "no"} />
              <Row k="Estado del solver" v={solution.status} mono />
            </dl>
          </div>

          <details className="group rounded-lg border border-line bg-white">
            <summary className="cursor-pointer list-none px-5 py-4 font-mono text-xs uppercase tracking-[0.14em] text-ink-3 group-open:border-b group-open:border-line">
              Pistas leídas ({extraction.puzzle.cages.length})
            </summary>
            <ul className="grid gap-1 p-5 text-sm sm:grid-cols-2">
              {extraction.puzzle.cages.map((cg, i) => (
                <li key={i} className="flex justify-between gap-3 font-mono text-ink-2">
                  <span>f{cg.cells[0][0] + 1} c{cg.cells[0][1] + 1}</span>
                  <span className="text-ink">{cg.target}{OP_LABEL[cg.op] ?? cg.op}</span>
                </li>
              ))}
            </ul>
          </details>
        </div>
      </div>
    </motion.div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex justify-between gap-4 py-2.5">
      <dt className="text-ink-2">{k}</dt>
      <dd className={`text-right text-ink ${mono ? "font-mono text-xs" : "font-medium"}`}>{v}</dd>
    </div>
  );
}
