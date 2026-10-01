# KenKen: Visión Computacional + Constraint Programming (CC58 – Trabajo 1)

Pipeline end-to-end: **foto del KenKen → extracción (OpenCV + OCR k-NN) → modelo CP (OR-Tools CP-SAT) → solución proyectada sobre la foto**.

## Instalación
```bash
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```
No requiere Tesseract: el clasificador de glifos se entrena la primera vez con las fuentes del sistema (cache en `~/.cache/kenken`).

## Uso
```bash
python -m kenken foto.jpg -o output          # pipeline completo (añadir --show para ver ventana)
python -m kenken --json puzzle.json          # solo Fase 2 (resolver un JSON)
python -m kenken foto.jpg --encoding table   # codificación de jaulas con restricciones tabla
python tools/make_dataset.py --out data/synthetic --count 28   # dataset sintético con ground truth
python tools/evaluate.py --dataset data/synthetic               # métricas sobre un dataset
python tools/evaluate.py --synthetic 40                         # métricas sobre puzzles aleatorios
python -m pytest -q                                             # tests
```
Salidas en `output/`: `*_puzzle.json` (Fase 1), `*_solution.json`, `*_debug.png` (bordes/lecturas detectadas), `*_overlay.png` (solución sobre la foto), `*_board.png`, `*_summary.png`.

## Estructura
| Módulo | Fase | Contenido |
|---|---|---|
| `kenken/vision/preprocess.py` | 1 | escala de grises, corrección de iluminación, binarización, localización de la grilla, homografía |
| `kenken/vision/grid.py` | 1 | tamaño N (perfiles de líneas), bordes gruesos/delgados (2-means), jaulas (union-find) |
| `kenken/vision/ocr.py` | 1 | segmentación de glifos, k-NN, gramática `dígitos+op`, N-best |
| `kenken/vision/extract.py` | 1 | imagen → `Puzzle` (JSON), reparaciones de consistencia |
| `kenken/solver.py` | 2 | modelo CP-SAT: AllDifferent, suma, multiplicación, restricciones reificadas (−, ÷, op desconocido), tabla; COP de corrección de OCR |
| `kenken/visualize.py`, `pipeline.py` | 3 | integración automática y visualización |
| `kenken/generator.py`, `render.py` | – | generador de puzzles únicos + aumentaciones tipo foto |

## Modelo CP (resumen)
- Variables `x[r][c] ∈ {1..N}`; `AllDifferent` por fila y columna.
- Jaulas: `=`, `sum = t`, `AddMultiplicationEquality`, y para `−`/`÷` un booleano reificado de orden (`b ⇒ a−b=t`, `¬b ⇒ b−a=t`).
- Operador ilegible `?`: un booleano por operador candidato + `ExactlyOne` (reificación).
- Si la lectura más probable es infactible: **COP** que elige una lectura alternativa por jaula minimizando `Σ −log p(lectura)`.

## Resultados actuales (sintéticos, 160 imágenes no vistas)
size 100% · jaulas 100% · bordes 100% · pistas 95% · resuelto end-to-end 94% (100% en imágenes limpias).

### Limitaciones conocidas
- Una lectura errónea pero *satisfacible* (p. ej. `3÷` leído como `3+`) no se detecta: el modelo resuelve el puzzle equivocado.
- Pistas muy pequeñas (9×9 con celdas de ~70 px) en fotos degradadas concentran los errores de OCR.
- Líneas delgadas de 1 px gris claro con degradación fuerte pueden confundir el tamaño N con un divisor (≈1/300 casos).

## Dataset
`data/synthetic/` contiene imágenes generadas + JSON de verdad. **Falta añadir ≥10 fotos reales** (capturas de kenkenpuzzle.com / Simon Tatham "Keen", impresas y fotografiadas con distinta luz/ángulo) con su JSON anotado a mano para evaluar con `tools/evaluate.py --dataset`.
