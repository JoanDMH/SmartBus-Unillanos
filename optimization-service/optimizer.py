"""DEV-C1 — Motor de programación lineal entera para optimización de frecuencias.

Minimiza el costo total de operación semanal dado:
  - La demanda predicha por franja horaria (obtenida del endpoint /trips/ai/predict-demand)
  - Las restricciones operativas (capacidad, flota, conductores) de constraints.py

Función objetivo:
    Minimizar Σ_h ( costo_combustible × km_por_ciclo + costo_conductor_hora × horas_ciclo )
             × despachos[h]

Variables de decisión:
    despachos[h] ∈ ℤ≥0  — número de buses despachados en la hora h

Uso:
    from optimizer import solve_weekly_schedule
    result = solve_weekly_schedule(weekly_demand, fleet_config)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pulp

from constraints import FleetConfig, ROUTE_DURATION_MIN, add_operational_constraints

logger = logging.getLogger(__name__)

# ── Costos operativos (COP, valores referenciales Servitranstur 2026) ────────

KM_PER_CYCLE: float = 12.0          # km por ciclo completo (ida + regreso Ruta Parque)
FUEL_COST_PER_KM: float = 1_800.0   # COP/km (ACPM + mantenimiento)
DRIVER_COST_PER_HOUR: float = 9_500.0  # COP/hora (salario mínimo + prestaciones)
CYCLE_DURATION_HOURS: float = ROUTE_DURATION_MIN / 60.0  # horas por ciclo (~1.33 h)

COST_PER_DISPATCH: float = (
    FUEL_COST_PER_KM * KM_PER_CYCLE
    + DRIVER_COST_PER_HOUR * CYCLE_DURATION_HOURS
)


# ── Tipos de datos de resultado ──────────────────────────────────────────────

@dataclass
class HourlySchedule:
    """Resultado de optimización para una franja horaria."""
    hour: int                   # 0–23
    buses_dispatched: int       # variable de decisión resuelta
    demand_forecast: float      # pasajeros predichos
    passengers_covered: int     # buses × capacidad
    cost_cop: float             # costo operativo COP para esta franja


@dataclass
class WeeklyScheduleResult:
    """Resultado completo de la optimización semanal."""
    status: str                             # "Optimal", "Infeasible", "Unbounded", etc.
    total_cost_cop: float                   # costo total semanal en COP
    schedule_by_day: Dict[str, List[HourlySchedule]]  # {lunes: [...], martes: [...], ...}
    solver_message: Optional[str] = None

    @property
    def is_optimal(self) -> bool:
        return self.status == "Optimal"


# ── Motor principal ──────────────────────────────────────────────────────────

WEEKDAYS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]


def solve_daily_schedule(
    daily_demand: Dict[int, float],
    fleet: FleetConfig,
    day_label: str = "dia",
) -> tuple[str, List[HourlySchedule]]:
    """Resuelve el problema de optimización para un día.

    Args:
        daily_demand: {hora (0-23): pasajeros_predichos}. Solo las horas con
                      demanda > 0 se incluyen; el resto se fuerza a 0 buses.
        fleet: Configuración de flota y conductores.
        day_label: Etiqueta del día para nombrar las variables PuLP.

    Returns:
        (status_str, lista_de_HourlySchedule)
    """
    active_hours = sorted(h for h, d in daily_demand.items() if d > 0)

    if not active_hours:
        logger.warning(f"[Optimizer] {day_label}: sin demanda — generando horario vacío.")
        return "Optimal", []

    # Variables de decisión: enteros no negativos
    dispatches: Dict[int, pulp.LpVariable] = {
        h: pulp.LpVariable(
            name=f"buses_{day_label}_h{h:02d}",
            lowBound=0,
            cat=pulp.const.LpInteger,
        )
        for h in active_hours
    }

    # Problema de minimización
    prob = pulp.LpProblem(
        name=f"smartbus_schedule_{day_label}",
        sense=pulp.const.LpMinimize,
    )

    # Función objetivo: minimizar costo total de despachos
    prob += (
        pulp.lpSum(dispatches[h] * COST_PER_DISPATCH for h in active_hours),
        "costo_total_operacion",
    )

    # Restricciones operativas
    add_operational_constraints(
        prob=prob,
        dispatches=dispatches,
        demand={h: daily_demand.get(h, 0.0) for h in active_hours},
        fleet=fleet,
    )

    # Resolver con CBC (incluido en PuLP, sin dependencia externa)
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=30)
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    logger.info(f"[Optimizer] {day_label}: status={status}, "
                f"costo={pulp.value(prob.objective):,.0f} COP")

    if status != "Optimal":
        logger.warning(f"[Optimizer] {day_label}: solución no óptima ({status}). "
                       "Revisar restricciones de flota vs. demanda.")
        return status, []

    hourly: List[HourlySchedule] = []
    for h in active_hours:
        n_buses = int(round(pulp.value(dispatches[h]) or 0))
        covered = n_buses * fleet.bus_capacity
        hourly.append(HourlySchedule(
            hour=h,
            buses_dispatched=n_buses,
            demand_forecast=daily_demand.get(h, 0.0),
            passengers_covered=covered,
            cost_cop=n_buses * COST_PER_DISPATCH,
        ))

    return status, hourly


def solve_weekly_schedule(
    weekly_demand: Dict[str, Dict[int, float]],
    fleet: Optional[FleetConfig] = None,
) -> WeeklyScheduleResult:
    """Resuelve la optimización para toda la semana.

    Args:
        weekly_demand: {dia: {hora: pasajeros_predichos}}
                       Las claves de día deben ser: lunes, martes, miercoles,
                       jueves, viernes, sabado (domingo no opera Ruta Parque).
        fleet: Configuración de flota. Si None, usa los valores por defecto.

    Returns:
        WeeklyScheduleResult con el itinerario completo y el costo total.
    """
    if fleet is None:
        fleet = FleetConfig()

    logger.info(f"[Optimizer] Iniciando optimización semanal — "
                f"flota={fleet.available_buses} buses ({fleet.bus_type}), "
                f"{fleet.available_drivers} conductores.")

    total_cost = 0.0
    schedule_by_day: Dict[str, List[HourlySchedule]] = {}
    any_infeasible = False

    for day in WEEKDAYS:
        demand = weekly_demand.get(day, {})
        status, hourly = solve_daily_schedule(
            daily_demand=demand,
            fleet=fleet,
            day_label=day,
        )
        schedule_by_day[day] = hourly
        if status != "Optimal":
            any_infeasible = True
        total_cost += sum(h.cost_cop for h in hourly)

    overall_status = "Infeasible" if any_infeasible else "Optimal"
    logger.info(f"[Optimizer] Optimización semanal completa: "
                f"status={overall_status}, costo_total={total_cost:,.0f} COP")

    return WeeklyScheduleResult(
        status=overall_status,
        total_cost_cop=total_cost,
        schedule_by_day=schedule_by_day,
        solver_message=None if overall_status == "Optimal"
                       else "Uno o más días resultaron infeasible — revisar demanda vs. flota.",
    )
