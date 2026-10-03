// Cliente de la API del backend (contrato: README principal §7.2).
// El backend corre con `kenken serve` en http://127.0.0.1:8000.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export const ACCEPTED_EXT = [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".pdf"];
export const MAX_BYTES = 15 * 1024 * 1024;

// El backend serverless (Vercel) acepta como máximo 4.5 MB por petición. Las fotos que
// superen esto se recomprimen en el navegador antes de subirlas (ver prepareUpload); los
// PDF no se pueden recomprimir, así que se validan contra este límite directamente.
const UPLOAD_SAFE_BYTES = 4 * 1024 * 1024;
const RESIZE_MAX_DIM = 2000; // el backend igualmente reescala a 1600 px: no se pierde nitidez real

export type Op = "+" | "-" | "*" | "/" | "=" | "?";

export interface Cage { target: number; op: Op; cells: [number, number][] }
export interface Puzzle { size: number; cages: Cage[] }
export interface CageDetection { clue_cell: [number, number]; ocr_text: string; confidence: number }

export interface ExtractResponse {
  puzzle: Puzzle;
  detections: CageDetection[];
  grid_corners: [number, number][];
  image_size: [number, number];
  warnings: string[];
  timings: { vision_ms: number };
  images: { debug: string } | null;
}

export interface SolverStats {
  encoding: string; wall_time_ms: number; branches: number; conflicts: number;
  num_variables: number; num_constraints: number;
}

export interface SolveResponse {
  status: "OPTIMAL" | "FEASIBLE" | "INFEASIBLE" | "UNKNOWN" | string;
  solved: boolean;
  grid: number[][] | null;
  unique: boolean | null;
  puzzle: Puzzle;
  stats: SolverStats;
  images: { board: string } | null;
}

export interface Correction { cell: [number, number]; read: string; corrected: string }

export interface SolveImageResponse {
  extraction: ExtractResponse;
  solution: SolveResponse;
  corrections: Correction[];
  timings: { vision_ms: number; solver_ms: number; total_ms: number };
  images: { overlay: string; board: string; debug: string } | null;
}

/** Error con un mensaje pensado para la persona que usa la app, no para el desarrollador. */
export class ApiError extends Error {
  code: string;
  hint?: string;
  constructor(code: string, message: string, hint?: string) {
    super(message);
    this.code = code;
    this.hint = hint;
  }
}

const FRIENDLY: Record<string, [string, string]> = {
  offline: [
    "No pudimos conectar con el servidor.",
    "Comprueba que el backend esté encendido (en una terminal: kenken serve) y vuelve a intentarlo.",
  ],
  invalid_input: [
    "No pudimos leer ese archivo.",
    "Usa una imagen (.png, .jpg, .webp, .bmp) o un PDF de menos de 15 MB.",
  ],
  extraction_failed: [
    "No encontramos un tablero en la imagen.",
    "Procura que el KenKen se vea completo, con buena luz y sin demasiada inclinación. Si es un PDF, el puzzle debe estar en la primera página.",
  ],
  invalid_puzzle: [
    "Leímos el tablero, pero algo no cuadra.",
    "Algunas jaulas o pistas salieron inconsistentes. Prueba con una foto más nítida o más de frente.",
  ],
  too_large: ["El archivo es demasiado grande.", "El máximo es 15 MB. Reduce la resolución o comprime la imagen."],
  payload_too_large: [
    "El archivo pesa demasiado para subirlo así.",
    "Si es un PDF, prueba exportarlo más liviano o toma una foto en su lugar; las fotos se optimizan solas.",
  ],
  bad_type: ["Ese tipo de archivo no está soportado.", "Acepta imágenes (.png, .jpg, .webp, .bmp) y PDF."],
  unknown: ["Ocurrió un error inesperado.", "Vuelve a intentarlo. Si persiste, revisa la consola del servidor."],
};

export function friendly(code: string, raw?: string): ApiError {
  const [msg, hint] = FRIENDLY[code] ?? FRIENDLY.unknown;
  return new ApiError(code, msg, raw && code === "unknown" ? `${hint} (${raw})` : hint);
}

/** Validación en el cliente antes de subir nada. */
export function validateFile(file: File): ApiError | null {
  const ext = "." + (file.name.split(".").pop() ?? "").toLowerCase();
  if (!ACCEPTED_EXT.includes(ext)) return friendly("bad_type");
  if (file.size > MAX_BYTES) return friendly("too_large");
  if (file.size === 0) return friendly("invalid_input");
  return null;
}

/**
 * Recomprime una foto demasiado pesada antes de subirla (reescalado + JPEG de menor
 * calidad) para que quepa en el límite de la función serverless. Los PDF y los archivos
 * ya livianos se devuelven sin cambios; si la compresión falla, se devuelve el original
 * y es el servidor quien reporta el error.
 */
export async function prepareUpload(file: File): Promise<File> {
  if (!file.type.startsWith("image/") || file.size <= UPLOAD_SAFE_BYTES) return file;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, RESIZE_MAX_DIM / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    const ctx = canvas.getContext("2d");
    if (!ctx) return file;
    ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    for (const quality of [0.85, 0.7, 0.55, 0.4]) {
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", quality));
      if (blob && blob.size <= UPLOAD_SAFE_BYTES) {
        const name = file.name.replace(/\.[^.]+$/, "") + ".jpg";
        return new File([blob], name, { type: "image/jpeg" });
      }
    }
  } catch {
    // createImageBitmap/canvas sin soporte: seguimos con el archivo original
  }
  return file;
}

export async function health(signal?: AbortSignal): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/api/health`, { signal, cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

export async function solveImage(file: File, signal?: AbortSignal): Promise<SolveImageResponse> {
  const body = new FormData();
  body.append("file", file);
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/solve-image?images=true`, { method: "POST", body, signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    throw friendly("offline");
  }
  if (res.status === 413) throw friendly("payload_too_large");
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const code = typeof data?.error === "string" ? data.error : "unknown";
    throw friendly(code, data?.message ?? res.statusText);
  }
  return data as SolveImageResponse;
}
