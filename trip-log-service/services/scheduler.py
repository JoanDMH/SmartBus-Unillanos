"""DEV-A1 — APScheduler: jobs automáticos de mantenimiento de datos.

Jobs configurados:
  1. cleanup_anomalies  → diario a las 02:00 UTC
     Detecta y marca registros anómalos en la tabla `trips`:
       - passenger_count = 0 sin nota explicativa
       - registros duplicados (mismo bus, mismo route, diferencia ≤ 5 min)
       - departure_time en el futuro (> ahora + 10 min de margen)
     El job NO borra registros — los marca con una nota de auditoría para
     revisión humana, siguiendo el principio de non-destructive data management.

  2. drift_check        → semanal, lunes a las 03:00 UTC  (DEV-E2)
     Calcula data drift (Kolmogorov-Smirnov) y concept drift sobre las
     predicciones de los últimos 7 días. Se implementa aquí para reutilizar
     la sesión de BD, pero la lógica de KS queda como stub hasta que el
     modelo acumule predicciones reales.

Dependencias: apscheduler>=3.10, sqlalchemy (sync, para jobs background).
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from storage.database import async_session

logger = logging.getLogger(__name__)

# Instancia global — iniciada en el lifespan de FastAPI
scheduler = AsyncIOScheduler(timezone="UTC")


# ── Job 1: Limpieza nocturna de anomalías ────────────────────────────────

async def cleanup_anomalies() -> None:
    """Marca registros anómalos con nota de auditoría. Corre a las 02:00 UTC."""
    logger.info("[Scheduler] Iniciando limpieza nocturna de anomalías...")
    now = datetime.now(timezone.utc)
    audit_tag = f"[ANOMALÍA DETECTADA {now.strftime('%Y-%m-%d')}]"
    flagged = 0

    async with async_session() as session:
        # 1. Conteo de pasajeros = 0 sin nota
        result = await session.execute(text("""
            UPDATE trips
            SET notes = :tag || ' passenger_count=0 sin justificación'
            WHERE passenger_count = 0
              AND (notes IS NULL OR notes NOT LIKE '%ANOMALÍA%')
            RETURNING id
        """), {"tag": audit_tag})
        flagged += len(result.fetchall())

        # 2. departure_time en el futuro (más de 10 minutos adelante)
        result = await session.execute(text("""
            UPDATE trips
            SET notes = :tag || ' departure_time futuro: ' || departure_time::text
            WHERE departure_time > :threshold
              AND (notes IS NULL OR notes NOT LIKE '%ANOMALÍA%')
            RETURNING id
        """), {"tag": audit_tag, "threshold": now + timedelta(minutes=10)})
        flagged += len(result.fetchall())

        # 3. Duplicados: mismo bus + route + departure_time dentro de ±5 min
        #    Se marca el registro más reciente (created_at mayor)
        result = await session.execute(text("""
            UPDATE trips t
            SET notes = :tag || ' posible duplicado'
            FROM (
                SELECT a.id
                FROM trips a
                JOIN trips b ON a.id <> b.id
                    AND a.bus_id     = b.bus_id
                    AND a.route_id   = b.route_id
                    AND ABS(EXTRACT(EPOCH FROM (a.departure_time - b.departure_time))) <= 300
                    AND a.created_at > b.created_at
            ) dups
            WHERE t.id = dups.id
              AND (t.notes IS NULL OR t.notes NOT LIKE '%ANOMALÍA%')
            RETURNING t.id
        """), {"tag": audit_tag})
        flagged += len(result.fetchall())

        await session.commit()

    if flagged:
        logger.warning(f"[Scheduler] Limpieza completada: {flagged} registro(s) marcados como anómalos.")
    else:
        logger.info("[Scheduler] Limpieza completada: no se encontraron anomalías.")


# ── Job 2: Refresco de vista materializada (cada 10 min) ─────────────────
# IMPORTANTE: REFRESH MATERIALIZED VIEW CONCURRENTLY no puede ejecutarse
# dentro de una transacción (PostgreSQL lo rechaza con error). APScheduler
# corre este job fuera de cualquier transacción activa, lo cual es correcto.

async def refresh_hourly_stats() -> None:
    """Refresca trips_hourly_stats sin bloquear lecturas. Corre cada 10 minutos."""
    async with async_session() as session:
        try:
            # La sesión SQLAlchemy abre una transacción implícita. La cerramos
            # con COMMIT antes de ejecutar el REFRESH para cumplir la restricción
            # de PostgreSQL que prohíbe CONCURRENTLY dentro de transacciones.
            await session.execute(text("COMMIT"))
            await session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY trips_hourly_stats"))
            logger.debug("[Scheduler] trips_hourly_stats refrescada correctamente.")
        except Exception as exc:
            logger.warning(f"[Scheduler] Error refrescando trips_hourly_stats: {exc}")


# ── Job 3: Detección de drift semanal (stub DEV-E2) ──────────────────────

async def drift_check() -> None:
    """Calcula drift de datos y de concepto. Corre los lunes a las 03:00 UTC."""
    logger.info("[Scheduler] Iniciando verificación semanal de drift...")

    async with async_session() as session:
        # Obtener distribución de passenger_count de los últimos 7 días
        result = await session.execute(text("""
            SELECT passenger_count
            FROM trips
            WHERE departure_time >= NOW() - INTERVAL '7 days'
            ORDER BY departure_time DESC
        """))
        recent_counts = [row[0] for row in result.fetchall()]

    if len(recent_counts) < 30:
        logger.info(f"[Scheduler] Drift check: datos insuficientes ({len(recent_counts)} registros en últimos 7 días). Mínimo: 30.")
        return

    # Estadísticas básicas de la distribución reciente
    mean_recent = sum(recent_counts) / len(recent_counts)
    logger.info(f"[Scheduler] Drift check: {len(recent_counts)} viajes recientes, media={mean_recent:.1f} pasajeros.")

    # TODO (DEV-E2): Implementar prueba KS contra distribución del dataset de entrenamiento
    # cuando el modelo acumule predicciones reales. Por ahora logueamos la distribución
    # para monitoreo manual en Azure Monitor.
    logger.info(f"[Scheduler] Drift check completado. Revisar métricas en Azure Monitor.")


# ── Configuración del scheduler ──────────────────────────────────────────

def setup_scheduler() -> AsyncIOScheduler:
    """Registra los jobs y devuelve el scheduler listo para iniciar."""

    scheduler.add_job(
        cleanup_anomalies,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="cleanup_anomalies",
        name="Limpieza nocturna de anomalías",
        replace_existing=True,
        misfire_grace_time=3600,  # tolera hasta 1h de retraso (reinicio del contenedor)
    )

    scheduler.add_job(
        refresh_hourly_stats,
        trigger="interval",
        minutes=10,
        id="refresh_hourly_stats",
        name="Refresco vista materializada trips_hourly_stats",
        replace_existing=True,
        misfire_grace_time=300,  # tolera hasta 5 min de retraso
    )

    scheduler.add_job(
        drift_check,
        trigger=CronTrigger(day_of_week="mon", hour=3, minute=0, timezone="UTC"),
        id="drift_check",
        name="Verificación semanal de drift",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    logger.info(
        "[Scheduler] Jobs registrados: "
        "cleanup_anomalies (02:00 UTC daily), "
        "refresh_hourly_stats (cada 10 min), "
        "drift_check (03:00 UTC mondays)."
    )
    return scheduler
