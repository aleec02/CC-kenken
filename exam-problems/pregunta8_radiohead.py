from ortools.sat.python import cp_model
from pathlib import Path

"""# Composición asistida por restricciones: progresión de 16 acordes estilo Radiohead
   X: A[t] = acorde del compás t, t = 0..15 ; D: A[t] en {0, ..., K-1}
   C1: (A[t], A[t+1]) en la tabla de bigramas del corpus      (AddAllowedAssignments)
   C2: A[0] en {G, F}                                          (tónica de inicio)
   C3: A[15] en {G, C, F}                                      (reposo mayor final)
   C4: ningún acorde aparece más de 4 veces                    (conteo con reificación)
   C5: no plagio: ninguna ventana de N_PLAGIO acordes seguidos puede copiar un fragmento
       original (AddForbiddenAssignments en ventana deslizante, como el anti-plagio de vallejo.py)
       N_PLAGIO = 16 -> la progresión completa no puede ser una original (lo que pide la pregunta)
       N_PLAGIO = 4  -> versión estricta del curso (4-gramas); N_PLAGIO = 3 ya es infactible
"""

T = 16                     # compases
MAX_REPETICIONES = 4
N_PLAGIO = 16              # largo de la ventana anti-plagio
N_ALTERNATIVAS = 5         # progresiones alternativas a imprimir con el callback

# ---------------------------------------------------------------- 1. leer y tokenizar el corpus
archivo = Path(__file__).with_name('radiohead_chords.txt')
canciones = {}
nombre = None
for linea in archivo.read_text(encoding='utf-8').splitlines():
    linea = linea.strip()
    if not linea:
        continue
    if linea.startswith('#'):
        nombre = linea.split(':', 1)[1].strip()   # "# CANCION 1: Creep" -> "Creep"
    else:
        canciones[nombre] = linea.split()

for nombre, acordes in canciones.items():
    print('%-13s (%2i acordes): %s' % (nombre, len(acordes), ' '.join(acordes)))

# bigramas armónicos únicos (solo dentro de cada canción, no entre canciones)
bigramas = sorted({(acordes[t], acordes[t + 1]) for acordes in canciones.values() for t in range(len(acordes) - 1)})
print('\nBigramas únicos (%i):' % len(bigramas))
print('  ' + '  '.join('%s->%s' % b for b in bigramas))

# ---------------------------------------------------------------- 2. mapear acordes a enteros
vocabulario = sorted({a for acordes in canciones.values() for a in acordes})
K = len(vocabulario)
id_de = {a: k for k, a in enumerate(vocabulario)}
print('\nAcordes (%i): %s' % (K, ', '.join('%s=%i' % (a, id_de[a]) for a in vocabulario)))

tabla_permitida = [(id_de[a], id_de[b]) for a, b in bigramas]

# tabla de plagio: todos los n-gramas de N_PLAGIO acordes seguidos de cada canción
# (con N_PLAGIO = 16: la canción completa si tiene 16, o sus ventanas de 16 si es más larga)
plagiarism_table = sorted({tuple(id_de[a] for a in acordes[i:i + N_PLAGIO])
                           for acordes in canciones.values() for i in range(len(acordes) - N_PLAGIO + 1)})
print('Fragmentos originales prohibidos (%i acordes): %i' % (N_PLAGIO, len(plagiarism_table)))

# ---------------------------------------------------------------- 3. modelo CP
#crear CSP
model = cp_model.CpModel()

#variables y dominios
A = [model.NewIntVar(0, K - 1, 'A' + str(t)) for t in range(T)]

#restricciones
##C1: cada transición consecutiva debe existir en el corpus (restricción de tabla)
for t in range(T - 1):
    model.AddAllowedAssignments([A[t], A[t + 1]], tabla_permitida)

##C2: comienza en tónica G o F
model.AddAllowedAssignments([A[0]], [(id_de['G'],), (id_de['F'],)])

##C3: termina en un acorde de reposo mayor G, C o F
model.AddAllowedAssignments([A[T - 1]], [(id_de['G'],), (id_de['C'],), (id_de['F'],)])

##C4: ningún acorde más de 4 veces (b[t][k] <-> A[t] == k, reificación bidireccional)
for k in range(K):
    usos = []
    for t in range(T):
        b = model.NewBoolVar('es_' + vocabulario[k] + '_' + str(t))
        model.Add(A[t] == k).OnlyEnforceIf(b)
        model.Add(A[t] != k).OnlyEnforceIf(b.Not())
        usos += [b]
    model.Add(sum(usos) <= MAX_REPETICIONES)

##C5: no plagio: cada ventana deslizante de N_PLAGIO acordes es distinta de todo fragmento original
for i in range(T - N_PLAGIO + 1):
    model.AddForbiddenAssignments(A[i:i + N_PLAGIO], plagiarism_table)

#crear solver
solver = cp_model.CpSolver()
status = solver.Solve(model)

# ---------------------------------------------------------------- 4. decodificar e imprimir
print('\nEstado:', solver.StatusName(status))
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    progresion = [vocabulario[solver.Value(a)] for a in A]
    print('Progresión generada (16 compases):')
    for c in range(0, T, 4):
        print('  | ' + ' | '.join('%-4s' % a for a in progresion[c:c + 4]) + ' |')
    # verificación independiente de todas las reglas
    assert all((progresion[t], progresion[t + 1]) in set(bigramas) for t in range(T - 1))
    assert progresion[0] in ('G', 'F') and progresion[-1] in ('G', 'C', 'F')
    assert max(progresion.count(a) for a in set(progresion)) <= MAX_REPETICIONES
    assert all(tuple(id_de[a] for a in progresion[i:i + N_PLAGIO]) not in plagiarism_table
               for i in range(T - N_PLAGIO + 1))
    print('Verificación: todas las restricciones se cumplen')
    print('Walltime: %.4f ms' % (solver.WallTime() * 1000))


# ---------------------------------------------------------------- 5. alternativas con callback
class ProgresionSolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables, limite):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__limite = limite
        self.__solution_count = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        progresion = [vocabulario[self.Value(a)] for a in self.__variables]
        print('  #%i: %s' % (self.__solution_count,
                             ' | '.join(' '.join(progresion[c:c + 4]) for c in range(0, T, 4))))
        if self.__solution_count >= self.__limite:
            self.StopSearch()   # el espacio tiene miles de progresiones: se cortan las primeras

    def solution_count(self):
        return self.__solution_count


print('\nPrimeras %i progresiones válidas (enumerate_all_solutions):' % N_ALTERNATIVAS)
solver = cp_model.CpSolver()
solution_printer = ProgresionSolutionPrinter(A, N_ALTERNATIVAS)
solver.parameters.enumerate_all_solutions = True
status = solver.Solve(model, solution_printer)
print('Estado = %s, soluciones impresas: %i' % (solver.StatusName(status), solution_printer.solution_count()))
