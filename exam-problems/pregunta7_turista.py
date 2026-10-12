from ortools.sat.python import cp_model
import itertools
import math

"""# Turista: 20 lugares, 4 días, 5 lugares por día, un circuito (TSP) por día
   X: x[i][d] = 1 si el lugar i se visita el día d
      y[i][j][d] = 1 si el día d se va del lugar i al lugar j (arco dirigido)
      r[i][d] = 1 si el lugar i es la raíz (inicio) del tour del día d
      u[i][d] en [1,5]: orden de visita del lugar i en el tour del día d (MTZ)
   C1: cada lugar en exactamente un día ; C2: cada día exactamente 5 lugares
   C3: grados de entrada y salida = x[i][d] (arcos solo entre lugares del mismo día)
   C4: MTZ condicional a los arcos activos (elimina subtours)
   Objetivo: minimizar la distancia euclidiana total de los 4 días
   Parte 2: partición exacta en grupos de 5 (certifica que la solución MTZ es óptima)
"""

# Los 20 lugares del TSP del curso (tsp.py, semana 5)
locations = [(22.75, 83.58), (33.92, 76.74), (22.58, 29.68), (25.37, 46.79), (9.25, 67.19), (37.56, 52.95),
             (86.97, 1.89), (13.96, 16.41), (89.52, 98.57), (89.55, 79.3), (19.06, 93.83), (51.2, 84.64),
             (15.66, 3.6), (82.16, 37.57), (56.08, 41.8), (58.93, 15.44), (73.54, 29.36), (32.21, 40.46),
             (49.43, 26.72), (3.43, 14.81)]
n = len(locations)   # 20 lugares
D = 4                # días
K = 5                # lugares por día


def distance(x1, y1, x2, y2):
    # distancia euclidiana x100 redondeada a entero (CP-SAT trabaja con enteros), como en tsp.py
    return int(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2) * 100 + 0.5)


dist = [[distance(*locations[i], *locations[j]) for j in range(n)] for i in range(n)]

#crear CSP
model = cp_model.CpModel()

#variables y dominios
x = [[model.NewBoolVar('x' + str(i) + '_' + str(d)) for d in range(D)] for i in range(n)]
r = [[model.NewBoolVar('r' + str(i) + '_' + str(d)) for d in range(D)] for i in range(n)]
u = [[model.NewIntVar(1, K, 'u' + str(i) + '_' + str(d)) for d in range(D)] for i in range(n)]
y = {}
for d in range(D):
    for i in range(n):
        for j in range(n):
            if i != j:
                y[i, j, d] = model.NewBoolVar('y' + str(i) + '_' + str(j) + '_' + str(d))

#restricciones
##C1: cada lugar se asigna a exactamente un día
for i in range(n):
    model.Add(sum(x[i]) == 1)
##C2: cada día tiene exactamente 5 lugares
for d in range(D):
    model.Add(sum(x[i][d] for i in range(n)) == K)

##C3: grados. Un arco del día d solo puede unir lugares de ese día,
##    y cada lugar del día tiene exactamente 1 arco de salida y 1 de entrada (0 si no es del día)
for d in range(D):
    for i in range(n):
        for j in range(n):
            if i != j:
                model.AddImplication(y[i, j, d], x[i][d])
                model.AddImplication(y[i, j, d], x[j][d])
        model.Add(sum(y[i, j, d] for j in range(n) if j != i) == x[i][d])   # grado de salida
        model.Add(sum(y[j, i, d] for j in range(n) if j != i) == x[i][d])   # grado de entrada

##C4: MTZ. Una raíz por día (u = 1); si el arco i->j está activo y j no es la raíz,
##    entonces u[j] = u[i] + 1. Con u en [1,5] un ciclo que no pasa por la raíz es imposible.
for d in range(D):
    model.Add(sum(r[i][d] for i in range(n)) == 1)
    for i in range(n):
        model.AddImplication(r[i][d], x[i][d])
        model.Add(u[i][d] == 1).OnlyEnforceIf(r[i][d])
        for j in range(n):
            if i != j:
                model.Add(u[j][d] == u[i][d] + 1).OnlyEnforceIf([y[i, j, d], r[j][d].Not()])

##ruptura de simetría
##  (a) la raíz de cada día es su lugar de menor índice (quita las 5 rotaciones del tour)
for d in range(D):
    for i in range(n):
        for j in range(i):
            model.AddImplication(r[i][d], x[j][d].Not())
##  (b) los días son intercambiables -> se ordenan por su raíz (raíz del día d < raíz del día d+1)
raiz = [sum(i * r[i][d] for i in range(n)) for d in range(D)]
for d in range(D - 1):
    model.Add(raiz[d] < raiz[d + 1])

#función objetivo
model.Minimize(sum(dist[i][j] * y[i, j, d] for (i, j, d) in y))

#crear solver
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 120
solver.parameters.num_workers = 8
status = solver.Solve(model)

print('Estado:', solver.StatusName(status))
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print('Distancia total: %.2f unidades' % (solver.ObjectiveValue() / 100))
    print('Cota inferior:   %.2f unidades' % (solver.BestObjectiveBound() / 100))
    for d in range(D):
        lugares = [i for i in range(n) if solver.Value(x[i][d])]
        inicio = next(i for i in lugares if solver.Value(r[i][d]))
        tour, actual = [inicio], inicio
        while True:
            actual = next(j for j in lugares if j != actual and solver.Value(y[actual, j, d]))
            tour.append(actual)
            if actual == inicio:
                break
        largo = sum(dist[tour[k]][tour[k + 1]] for k in range(len(tour) - 1)) / 100
        orden = [solver.Value(u[i][d]) for i in tour[:-1]]
        print('  Día %i: %s  (%.2f unidades, u = %s)' % (d, ' -> '.join(map(str, tour)), largo, orden))
    print('Walltime: %.4f ms' % (solver.WallTime() * 1000))


# ---------------------------------------------------------------- Parte 2: certificado de optimalidad
# El modelo MTZ termina por tiempo (FEASIBLE). Para probar el óptimo se descompone el problema:
#   1) para cada grupo de 5 lugares (C(20,5) = 15504) se calcula su mejor tour por enumeración
#      (fijando el primer lugar y un sentido: 4!/2 = 12 tours por grupo)
#   2) CP-SAT elige 4 grupos disjuntos que cubren los 20 lugares (partición exacta) con costo mínimo
grupos, costo, mejor_tour = [], [], []
for g in itertools.combinations(range(n), K):
    mejor = None
    for p in itertools.permutations(g[1:]):
        if p[0] > p[-1]:
            continue   # mismo tour en sentido contrario
        t = (g[0],) + p
        c = sum(dist[t[k]][t[(k + 1) % K]] for k in range(K))
        if mejor is None or c < mejor[0]:
            mejor = (c, t)
    grupos.append(g)
    costo.append(mejor[0])
    mejor_tour.append(mejor[1])

#crear CSP
model = cp_model.CpModel()

#variables y dominios: z[s] = 1 si el grupo s es uno de los 4 días
z = [model.NewBoolVar('z' + str(s)) for s in range(len(grupos))]

#restricciones: cada lugar está en exactamente un grupo elegido (=> exactamente 4 grupos)
for i in range(n):
    model.Add(sum(z[s] for s, g in enumerate(grupos) if i in g) == 1)

#función objetivo
model.Minimize(sum(costo[s] * z[s] for s in range(len(grupos))))

#crear solver
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 120
solver.parameters.num_workers = 8
status = solver.Solve(model)

print('\nParte 2 - partición exacta:', solver.StatusName(status))
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print('Distancia total: %.2f unidades' % (solver.ObjectiveValue() / 100))
    print('Cota inferior:   %.2f unidades' % (solver.BestObjectiveBound() / 100))
    for s in range(len(grupos)):
        if solver.Value(z[s]):
            t = mejor_tour[s]
            print('  %s -> %i  (%.2f unidades)' % (' -> '.join(map(str, t)), t[0], costo[s] / 100))
    print('Walltime: %.4f ms' % (solver.WallTime() * 1000))
