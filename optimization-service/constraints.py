"""DEV-C2 — Restricciones operativas del servicio de transporte Unillanos.

Define las constantes y la función que añade restricciones duras al modelo
PuLP antes de resolver. Las restricciones reflejan:
  - Capacidad por tipo de bus (normativa Servitranstur)
  - Descanso obligatorio de conductores (Codigo Sustantivo del Trabajo + Res. 160/2005)
  - Tiempo de recorrido Ruta Parque (40 min ida + 40 min regreso)
  - Flota disponible (parametro configurable)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import pulp


# -- Capacidades por tipo de bus ----------------------------------------------

BUS_CAPACITY: Dict[str, int] = {
    "articulado": 60,
    "estandar": 40,
}

DEFAULT_BUS_TYPE: str = "estandar"

# -- Parametros de la Ruta Parque ---------------------------------------------

ROUTE_DURATION_MIN: int = 80          # 40 min ida + 40 min regreso
MIN_HEADWAY_MIN: int = 10
MAX_HEADWAY_MIN: int = 60

# -- Normativa laboral de conductores -----------------------------------------

DRIVER_MAX_CONTINUOUS_HOURS: float = 4.0
DRIVER_MIN_BREAK_MIN: int = 30
DRIVER_MAX_DAILY_HOURS: float = 8.0


@dataclass
class FleetConfig:
    """Configuracion operativa de la flota disponible."""
    available_buses: int = 3
    bus_type: str = DEFAULT_BUS_TYPE
    available_drivers: int = 6
    operating_hours: List[int] = field(default_factory=lambda: list(range(5, 22)))

    @property
    def bus_capacity(self) -> int:
        return BUS_CAPACITY.get(self.bus_type, BUS_CAPACITY[DEFAULT_BUS_TYPE])


def add_operational_constraints(
    prob: pulp.LpProblem,
    dispatches: Dict[int, pulp.LpVariable],
    demand: Dict[int, float],
    fleet: FleetConfig,
) -> None:
    """Agrega restricciones duras al modelo PuLP.

    Modifica `prob` in-place. Todas las restricciones trabajan sobre horas
    del calendario real, no sobre posiciones de array, para evitar falsos
    solapamientos cuando hay cortes de servicio (ej. pausa al mediodia).

    Args:
        prob: Problema PuLP inicializado con funcion objetivo.
        dispatches: {hora_calendario: LpVariable} — solo horas activas.
        demand: {hora: pasajeros_esperados}.
        fleet: Configuracion de la flota.
    """
    capacity = fleet.bus_capacity

    for hour, var in dispatches.items():
        d = demand.get(hour, 0.0)

        # R1 — Cobertura de demanda
        prob += (
            var * capacity >= d,
            f"cobertura_demanda_h{hour}",
        )

        # R2 — Flota disponible
        prob += (
            var <= fleet.available_buses,
            f"flota_disponible_h{hour}",
        )

        # R3 — No negativo (explicito por documentacion)
        prob += (
            var >= 0,
            f"no_negativo_h{hour}",
        )

    hours = sorted(dispatches.keys())

    # R4 — Conductores disponibles:
    #   Un ciclo completo dura ROUTE_DURATION_MIN min (~80 min, ~2 franjas).
    #   Dos despachos en horas h y h+1 solapan conductores.
    #   Despachos separados por >= 2h en el calendario NO solapan.
    #
    #   CORRECCION vs. version anterior: solo aplicar cuando la diferencia
    #   real en el calendario es exactamente 1 hora (horas consecutivas),
    #   no cuando son simplemente adyacentes en el array de horas activas.
    #   Si hours = [6,7,8,12,13], el par (8,12) NO es consecutivo aunque
    #   sean vecinos en el array, por lo que no se restringe.
    for i, hour in enumerate(hours):
        if i == 0:
            continue
        prev_hour = hours[i - 1]
        if hour - prev_hour == 1:
            prob += (
                dispatches[hour] + dispatches[prev_hour] <= fleet.available_drivers,
                f"conductores_disponibles_h{hour}",
            )

    # R5 — Descanso de conductores:
    #   No puede haber despacho continuo por mas de DRIVER_MAX_CONTINUOUS_HOURS
    #   horas seguidas en el calendario.
    #
    #   CORRECCION: solo aplicar la ventana cuando cubre exactamente
    #   max_continuous horas reales (window[-1] - window[0] == max_continuous).
    #   Si hay un salto de servicio (ej. 8 -> 12), window[-1] - window[0] > 4
    #   y la restriccion se omite correctamente para esa ventana.
    max_continuous = int(DRIVER_MAX_CONTINUOUS_HOURS)
    for i in range(len(hours) - max_continuous):
        window = hours[i: i + max_continuous + 1]
        if len(window) < max_continuous + 1:
            continue
        if window[-1] - window[0] != max_continuous:
            continue
        prob += (
            pulp.lpSum(dispatches[h] for h in window) <= fleet.available_buses * max_continuous,
            f"descanso_conductores_desde_h{window[0]}",
        )
