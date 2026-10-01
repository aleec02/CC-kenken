"""Fase 2: modelo de Programación por Restricciones (CP) para KenKen con OR-Tools CP-SAT.

# CSP KenKen (X, D, C)
   X: grilla[i][j]                      para i, j en 0..n-1   (valor de la celda i,j)
   D: grilla[i][j] en {1, ..., n}
   C1: AllDifferent(grilla[i][0..n-1])  para cada fila i      (global)
   C2: AllDifferent(grilla[0..n-1][j])  para cada columna j   (global)
   C3: para cada jaula J con objetivo t y operación op:
       "="   x = t                                             (unaria)
       "+"   sum(x_k para k en J) = t                          (global: suma)
       "*"   prod(x_k para k en J) = t                         (global: multiplicación)
       "-"   |a - b| = t   reificada:  b_orden => a - b = t,   no b_orden => b - a = t
       "/"   max/min = t   reificada:  b_orden => a = t*b,     no b_orden => b = t*a
       "?"   operación ilegible (OCR): un booleano por operación candidata,
             ExactlyOne(booleanos) y cada restricción reificada en su booleano.

Codificaciones de las jaulas (comparar en el informe):
   "arith": las restricciones aritméticas de C3.
   "table": cada jaula se convierte en una restricción de tabla (AddAllowedAssignments)
            con las tuplas que cumplen la aritmética y que son distintas en celdas de la
            misma fila/columna -> consistencia de arco generalizada por jaula.

# COP de corrección de OCR (ver resolver_con_alternativas)
   X, D, C1, C2 como arriba; cada jaula k tiene lecturas candidatas a con costo c_ka.
   y_ka en {0,1}:  ExactlyOne(y_k*),  y_ka => C3(lectura a)  (reificada)
   función objetivo: minimizar sum(c_ka * y_ka)
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .puzzle import Cage, Puzzle

MAX_TUPLAS_TABLA = 200_000   # sobre este tamaño la jaula usa la codificación aritmética
LIMITE_SOLUCIONES = 2        # para saber si la solución es única basta encontrar 2


@dataclass
class ResultadoCP:
    estado: str                          # OPTIMAL, FEASIBLE, INFEASIBLE, MODEL_INVALID, UNKNOWN
    grilla: list[list[int]] | None       # solución (None si no hay)
    walltime: float                      # segundos, solver.WallTime()
    unica: bool | None = None            # None si no se verificó
    estadisticas: dict = field(default_factory=dict)

    @property
    def resuelto(self) -> bool:
        return self.grilla is not None


class ContadorSoluciones(cp_model.CpSolverSolutionCallback):
    """Cuenta soluciones distintas (como VarArraySolutionPrinter del curso) y detiene la
    búsqueda al llegar al límite. Se cuentan grillas distintas: dos asignaciones que solo
    difieren en variables auxiliares (booleanos de orden/operación) son la misma solución."""

    def __init__(self, grilla, limite=LIMITE_SOLUCIONES):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__grilla = grilla
        self.__limite = limite
        self.__soluciones = set()

    def on_solution_callback(self):
        valores = tuple(self.Value(x) for fila in self.__grilla for x in fila)
        self.__soluciones.add(valores)
        if len(self.__soluciones) >= self.__limite:
            self.StopSearch()

    def solution_count(self):
        return len(self.__soluciones)


# --------------------------------------------------------------------------- restricciones
def tuplas_validas(jaula: Cage, n: int) -> list[tuple[int, ...]]:
    """Tuplas de valores de la jaula que cumplen su aritmética y son distintas en celdas
    que comparten fila o columna (usadas por la codificación "table")."""
    celdas = jaula.cells
    conflictos = [
        (a, b)
        for a, b in itertools.combinations(range(len(celdas)), 2)
        if celdas[a][0] == celdas[b][0] or celdas[a][1] == celdas[b][1]
    ]
    tuplas = []
    for valores in itertools.product(range(1, n + 1), repeat=len(celdas)):
        if any(valores[a] == valores[b] for a, b in conflictos):
            continue
        if jaula.evaluate(list(valores)):
            tuplas.append(valores)
    return tuplas


def agregar_operacion(model, op, t, xs, nombre, n, condicion=None):
    """Restricción aritmética de una jaula. Si `condicion` es un booleano, la restricción
    solo se exige cuando es verdadero (OnlyEnforceIf)."""
    def exigir(restriccion, literales=()):
        literales = list(literales) + ([condicion] if condicion is not None else [])
        return restriccion.OnlyEnforceIf(literales) if literales else restriccion

    if op == "=":
        exigir(model.Add(xs[0] == t))
    elif op == "+":
        exigir(model.Add(sum(xs) == t))
    elif op == "*":
        if condicion is None:
            model.AddMultiplicationEquality(t, xs)
        else:
            # AddMultiplicationEquality no acepta OnlyEnforceIf: se reifica a través de
            # una variable auxiliar con el producto.
            producto = model.NewIntVar(1, n ** len(xs), 'producto_' + nombre)
            model.AddMultiplicationEquality(producto, xs)
            exigir(model.Add(producto == t))
    elif op in ("-", "/"):
        a, b = xs
        orden = model.NewBoolVar('orden_' + nombre)    # orden <-> a es el mayor
        if op == "-":
            exigir(model.Add(a - b == t), [orden])          # orden=1 -> a - b = t
            exigir(model.Add(b - a == t), [orden.Not()])    # orden=0 -> b - a = t
        else:
            exigir(model.Add(a == t * b), [orden])          # orden=1 -> a = t*b
            exigir(model.Add(b == t * a), [orden.Not()])    # orden=0 -> b = t*a
    else:
        raise ValueError(f"Operación no soportada: {op!r}")


def agregar_jaula(model, jaula: Cage, xs, nombre, n, codificacion="arith"):
    """C3 para una jaula, con la codificación elegida."""
    if (codificacion == "table" and jaula.op != "="
            and n ** len(jaula.cells) <= MAX_TUPLAS_TABLA):
        tuplas = tuplas_validas(jaula, n)
        if tuplas:
            model.AddAllowedAssignments(xs, tuplas)
        else:
            model.AddBoolOr([])   # ninguna tupla cumple la jaula: modelo infactible
        return
    operaciones = jaula.candidate_ops()
    if len(operaciones) == 1:
        agregar_operacion(model, operaciones[0], jaula.target, xs, nombre, n)
        return
    # operación desconocida: un booleano por operación candidata (reificación)
    eleccion = [model.NewBoolVar('op_' + nombre + '_' + op) for op in operaciones]
    model.AddExactlyOne(eleccion)
    for op, b in zip(operaciones, eleccion):
        agregar_operacion(model, op, jaula.target, xs, nombre + '_' + op, n, condicion=b)


# --------------------------------------------------------------------------- modelo CSP
def crear_variables(model, n):
    #variables y dominios
    grilla = []
    for i in range(n):
        fila = []
        for j in range(n):
            fila += [model.NewIntVar(1, n, 'x' + str(i) + '_' + str(j))]
        grilla += [fila]
    return grilla


def agregar_cuadrado_latino(model, grilla, n):
    ##C1: toda fila tiene valores distintos
    for i in range(n):
        model.AddAllDifferent(grilla[i])
    ##C2: toda columna tiene valores distintos
    for j in range(n):
        columna = [grilla[i][j] for i in range(n)]
        model.AddAllDifferent(columna)


def crear_modelo(puzzle: Puzzle, codificacion: str = "arith"):
    """Construye el CSP del puzzle (parametrizado: cualquier n y cualquier conjunto de
    jaulas). Retorna (model, grilla)."""
    if codificacion not in ("arith", "table"):
        raise ValueError("codificacion debe ser 'arith' o 'table'")
    errores = puzzle.validate()
    if errores:
        raise ValueError("Puzzle inválido:\n  " + "\n  ".join(errores))

    n = puzzle.size
    #crear CSP
    model = cp_model.CpModel()
    grilla = crear_variables(model, n)
    #restricciones
    agregar_cuadrado_latino(model, grilla, n)
    ##C3: jaulas
    for k, jaula in enumerate(puzzle.cages):
        xs = [grilla[i][j] for i, j in jaula.cells]
        agregar_jaula(model, jaula, xs, 'jaula' + str(k), n, codificacion)
    return model, grilla


def _estadisticas(model, solver, codificacion):
    return {
        "codificacion": codificacion,
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "num_variables": len(model.Proto().variables),
        "num_restricciones": len(model.Proto().constraints),
    }


def contar_soluciones(model, grilla, limite=LIMITE_SOLUCIONES, tiempo_limite=10.0) -> int | None:
    """'Todas las soluciones' como en el curso (SearchForAllSolutions), deteniéndose al
    llegar a `limite`. enumerate_all_solutions + Solve(model, callback) es la forma actual
    de SearchForAllSolutions en OR-Tools. Retorna None si se agotó el tiempo sin
    terminar la enumeración."""
    solver = cp_model.CpSolver()
    solver.parameters.enumerate_all_solutions = True
    solver.parameters.max_time_in_seconds = tiempo_limite
    contador = ContadorSoluciones(grilla, limite)
    status = solver.Solve(model, contador)
    if status == cp_model.UNKNOWN or (status == cp_model.FEASIBLE and contador.solution_count() < limite):
        return None
    return contador.solution_count()


def resolver(puzzle: Puzzle, codificacion: str = "arith", tiempo_limite: float = 30.0,
             verificar_unicidad: bool = True, workers: int = 8) -> ResultadoCP:
    """Una solución + walltime y, opcionalmente, verificación de unicidad."""
    model, grilla = crear_modelo(puzzle, codificacion)
    n = puzzle.size

    #crear solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = tiempo_limite
    solver.parameters.num_workers = workers
    status = solver.Solve(model)

    resultado = ResultadoCP(solver.StatusName(status), None, solver.WallTime(),
                            estadisticas=_estadisticas(model, solver, codificacion))
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        resultado.grilla = [[solver.Value(grilla[i][j]) for j in range(n)] for i in range(n)]
        if verificar_unicidad:
            total = contar_soluciones(model, grilla, tiempo_limite=tiempo_limite)
            resultado.unica = None if total is None else total == 1
    return resultado


# --------------------------------------------------------------------------- COP
def resolver_con_alternativas(n: int, alternativas: list[list[tuple[Cage, float]]],
                              tiempo_limite: float = 30.0, workers: int = 8):
    """COP que corrige errores de OCR: elige una lectura por jaula minimizando el costo
    total (-log p de las lecturas) sujeto a que el puzzle sea un KenKen válido.
    `alternativas[k]` = [(jaula, costo), ...] con la lectura más probable primero.
    Retorna (ResultadoCP, puzzle corregido, lista de correcciones)."""
    #crear CSP
    model = cp_model.CpModel()
    grilla = crear_variables(model, n)
    #restricciones
    agregar_cuadrado_latino(model, grilla, n)
    eleccion = []      # eleccion[k] = booleanos y_k* (None si la jaula tiene 1 lectura)
    costos = []
    for k, lecturas in enumerate(alternativas):
        xs = [grilla[i][j] for i, j in lecturas[0][0].cells]
        if len(lecturas) == 1:
            agregar_jaula(model, lecturas[0][0], xs, 'jaula' + str(k), n)
            eleccion += [None]
            continue
        y = [model.NewBoolVar('y' + str(k) + '_' + str(a)) for a in range(len(lecturas))]
        model.AddExactlyOne(y)
        for a, ((jaula, costo), y_ka) in enumerate(zip(lecturas, y)):
            agregar_operacion(model, jaula.op, jaula.target, xs,
                              'jaula' + str(k) + '_' + str(a), n, condicion=y_ka)
            costos += [int(round(costo * 100)) * y_ka]
        eleccion += [y]
    #función objetivo
    if costos:
        model.Minimize(sum(costos))

    #crear solver
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = tiempo_limite
    solver.parameters.num_workers = workers
    status = solver.Solve(model)

    resultado = ResultadoCP(solver.StatusName(status), None, solver.WallTime(),
                            estadisticas=_estadisticas(model, solver, "cop-alternativas"))
    if not (status == cp_model.OPTIMAL or status == cp_model.FEASIBLE):
        return resultado, None, []

    resultado.grilla = [[solver.Value(grilla[i][j]) for j in range(n)] for i in range(n)]
    resultado.estadisticas["objetivo"] = solver.ObjectiveValue() / 100 if costos else 0.0
    jaulas, correcciones = [], []
    for lecturas, y in zip(alternativas, eleccion):
        if y is None:
            jaulas += [lecturas[0][0]]
            continue
        a = next(a for a, y_ka in enumerate(y) if solver.Value(y_ka))
        if a != 0:
            correcciones += [(lecturas[0][0], lecturas[a][0])]
        jaulas += [lecturas[a][0]]
    return resultado, Puzzle(n, jaulas), correcciones
