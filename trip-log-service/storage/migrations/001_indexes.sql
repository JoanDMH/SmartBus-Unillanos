-- DEV-A2 — Optimización de Consultas Temporales en PostgreSQL
-- Autor: SmartBus Unillanos / JoanDMH
-- Fecha: 2026-06-08
--
-- Estrategia: índices compuestos + vista materializada como fallback a TimescaleDB.
-- TimescaleDB NO está disponible en Azure Database for PostgreSQL Flexible Server
-- bajo la suscripción Azure for Students (tier Basic / Burstable). Esta migración
-- implementa las optimizaciones equivalentes con SQL nativo.
--
-- Ejecutar: psql -U smartbus -d smartbus_db -f 001_indexes.sql
-- Idempotente: usa IF NOT EXISTS y OR REPLACE donde corresponde.

-- ═══════════════════════════════════════════════════════════════════
--  1. ÍNDICES COMPUESTOS
-- ═══════════════════════════════════════════════════════════════════

-- Consulta más frecuente del motor de predicción:
--   SELECT ... FROM trips WHERE route_id = X ORDER BY departure_time DESC
CREATE INDEX IF NOT EXISTS idx_trips_route_time
    ON trips (route_id, departure_time DESC);

-- Consulta del scheduler de anomalías (cleanup_anomalies):
--   WHERE bus_id = X AND route_id = Y AND departure_time BETWEEN ...
CREATE INDEX IF NOT EXISTS idx_trips_bus_route_time
    ON trips (bus_id, route_id, departure_time DESC);

-- Consulta del drift_check semanal:
--   WHERE departure_time >= NOW() - INTERVAL '7 days'
CREATE INDEX IF NOT EXISTS idx_trips_departure_time
    ON trips (departure_time DESC);

-- Consulta de anomalías pendientes de revisión:
--   WHERE notes LIKE '%ANOMALÍA%'
-- Usamos índice GIN sobre texto cuando la columna notes no es nula
CREATE INDEX IF NOT EXISTS idx_trips_notes_anomaly
    ON trips (id)
    WHERE notes LIKE '%ANOMALÍA%';


-- ═══════════════════════════════════════════════════════════════════
--  2. VISTA MATERIALIZADA: trips_hourly_stats
-- ═══════════════════════════════════════════════════════════════════
-- Pre-agrega conteos por hora para acelerar las consultas del motor de
-- predicción (Prophet/XGBoost necesita series de tiempo por hora).
-- Se refresca CONCURRENTLY para no bloquear lecturas durante el refresh.

CREATE MATERIALIZED VIEW IF NOT EXISTS trips_hourly_stats AS
SELECT
    route_id,
    DATE_TRUNC('hour', departure_time)          AS hour_bucket,
    COUNT(*)                                    AS trip_count,
    SUM(passenger_count)                        AS total_passengers,
    AVG(passenger_count)                        AS avg_passengers,
    MAX(passenger_count)                        AS max_passengers,
    -- Clima más frecuente en la hora (para features del modelo)
    MODE() WITHIN GROUP (ORDER BY weather)      AS dominant_weather
FROM trips
WHERE departure_time IS NOT NULL
  AND notes NOT LIKE '%ANOMALÍA%'  -- excluye registros marcados como anómalos
GROUP BY route_id, DATE_TRUNC('hour', departure_time)
WITH DATA;

-- Índice único requerido para REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS idx_trips_hourly_stats_pk
    ON trips_hourly_stats (route_id, hour_bucket);

-- Índice de apoyo para consultas de rango temporal
CREATE INDEX IF NOT EXISTS idx_trips_hourly_stats_time
    ON trips_hourly_stats (hour_bucket DESC);


-- ═══════════════════════════════════════════════════════════════════
--  3. REFRESCO DE LA VISTA MATERIALIZADA
-- ═══════════════════════════════════════════════════════════════════
-- NOTA: NO se usa trigger para el refresh.
--
-- PostgreSQL no permite REFRESH MATERIALIZED VIEW CONCURRENTLY dentro
-- de un bloque de transacción (error: "cannot run inside a transaction
-- block"). Dado que los triggers siempre operan dentro de una transacción,
-- usar CONCURRENTLY en un trigger crashearía la aplicación en cada INSERT.
--
-- Estrategia correcta: APScheduler ejecuta el refresh cada 10 minutos
-- fuera de cualquier transacción activa. Ver:
--   trip-log-service/services/scheduler.py → job "refresh_hourly_stats"
--
-- Refresco manual (para inicialización o emergencias):
--   REFRESH MATERIALIZED VIEW CONCURRENTLY trips_hourly_stats;


-- ═══════════════════════════════════════════════════════════════════
--  4. VERIFICACIÓN
-- ═══════════════════════════════════════════════════════════════════
-- Ejecutar para confirmar que los índices se crearon correctamente:
--
--   \d trips
--   \d trips_hourly_stats
--   SELECT * FROM trips_hourly_stats LIMIT 5;
--
-- EXPLAIN ANALYZE en consulta de predicción esperada:
--   EXPLAIN ANALYZE
--   SELECT hour_bucket, avg_passengers
--   FROM trips_hourly_stats
--   WHERE route_id = 1
--     AND hour_bucket >= NOW() - INTERVAL '30 days'
--   ORDER BY hour_bucket;
