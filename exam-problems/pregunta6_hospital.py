from ortools.sat.python import cp_model

"""# Hospital: turnos de 3 especialistas (sobre-restringido)
   Turnos: Mañana=1, Tarde=2, Noche=3 ; Ei en {1,2,3}
   C1: AllDifferent(E1,E2,E3)   (dura)
   C2: E1 == 1                   C3: E2 == 1
   C4: E1 + E2 == 5              C5: E3 < E2
"""

turnos = {1: 'Mañana', 2: 'Tarde', 3: 'Noche'}

# ---------------------------------------------------------------- Parte 1: CSP duro
#crear CSP
model = cp_model.CpModel()

#variables y dominios
E1 = model.NewIntVar(1, 3, 'E1')
E2 = model.NewIntVar(1, 3, 'E2')
E3 = model.NewIntVar(1, 3, 'E3')

#restricciones (todas duras)
model.AddAllDifferent([E1, E2, E3])   # C1
model.Add(E1 == 1)                    # C2
model.Add(E2 == 1)                    # C3
model.Add(E1 + E2 == 5)               # C4
model.Add(E3 < E2)                    # C5

#crear solver
solver = cp_model.CpSolver()
status = solver.Solve(model)
print('Parte 1 - CSP duro:', solver.StatusName(status))
print('Walltime: %.4f ms' % (solver.WallTime() * 1000))

# si el modelo es infactible no se detiene: se relajan C2..C5 como soft constraints
# (feedback del INFEASIBLE -> modelo relajado, como el loop de autocorrección)
if status == cp_model.INFEASIBLE:
    print('Modelo infactible -> se relajan C2..C5 como restricciones suaves\n')


# ---------------------------------------------------------------- Partes 2 y 3: soft constraints + COP
#crear CSP
model = cp_model.CpModel()

#variables y dominios
E1 = model.NewIntVar(1, 3, 'E1')
E2 = model.NewIntVar(1, 3, 'E2')
E3 = model.NewIntVar(1, 3, 'E3')

#variables booleanas de penalización: vk = 1 <-> se viola Ck
v2 = model.NewBoolVar('v2')
v3 = model.NewBoolVar('v3')
v4 = model.NewBoolVar('v4')
v5 = model.NewBoolVar('v5')

#restricciones
model.AddAllDifferent([E1, E2, E3])   # C1 se mantiene dura

#reificación bidireccional: vk=0 -> Ck se cumple ; vk=1 -> Ck se viola
model.Add(E1 == 1).OnlyEnforceIf(v2.Not())        # C2
model.Add(E1 != 1).OnlyEnforceIf(v2)
model.Add(E2 == 1).OnlyEnforceIf(v3.Not())        # C3
model.Add(E2 != 1).OnlyEnforceIf(v3)
model.Add(E1 + E2 == 5).OnlyEnforceIf(v4.Not())   # C4
model.Add(E1 + E2 != 5).OnlyEnforceIf(v4)
model.Add(E3 < E2).OnlyEnforceIf(v5.Not())        # C5
model.Add(E3 >= E2).OnlyEnforceIf(v5)

#penalización ponderada
pesos = {'C2': 3, 'C3': 1, 'C4': 2, 'C5': 1}      # disponibilidad > carga > preferencia, rotación
penalizacion = model.NewIntVar(0, sum(pesos.values()), 'penalizacion')
model.Add(penalizacion == pesos['C2'] * v2 + pesos['C3'] * v3 + pesos['C4'] * v4 + pesos['C5'] * v5)


# enumerar todas las asignaciones factibles con su penalización (comprueba el óptimo a mano)
class HospitalSolutionPrinter(cp_model.CpSolverSolutionCallback):
    def __init__(self, variables, violadas, penalizacion):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self.__variables = variables
        self.__violadas = violadas
        self.__penalizacion = penalizacion
        self.__solution_count = 0

    def on_solution_callback(self):
        self.__solution_count += 1
        print('  %-28s violadas: %-14s penalización = %i' % (
            ', '.join('%s=%s' % (v, turnos[self.Value(v)]) for v in self.__variables),
            ' '.join('C%i' % k for k, v in zip(range(2, 6), self.__violadas) if self.Value(v)) or '-',
            self.Value(self.__penalizacion)))

    def solution_count(self):
        return self.__solution_count


print('Todas las asignaciones (C1 dura):')
solver = cp_model.CpSolver()
solution_printer = HospitalSolutionPrinter([E1, E2, E3], [v2, v3, v4, v5], penalizacion)
solver.parameters.enumerate_all_solutions = True
status = solver.Solve(model, solution_printer)
print('Número de soluciones: %i\n' % solution_printer.solution_count())

#función objetivo
model.Minimize(penalizacion)

#crear solver
solver = cp_model.CpSolver()
status = solver.Solve(model)

if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    print('Partes 2-3 - COP:', solver.StatusName(status))
    print('  E1 ->', turnos[solver.Value(E1)])
    print('  E2 ->', turnos[solver.Value(E2)])
    print('  E3 ->', turnos[solver.Value(E3)])
    print('  Violadas: C2=%i C3=%i C4=%i C5=%i' % (
        solver.Value(v2), solver.Value(v3), solver.Value(v4), solver.Value(v5)))
    print('  Penalización total:', int(solver.ObjectiveValue()))
    print('Walltime: %.4f ms' % (solver.WallTime() * 1000))
