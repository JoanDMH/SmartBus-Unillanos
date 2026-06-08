/**
 * DEV-D1 — DemandChart
 * Gráfico de líneas dual con Recharts:
 *   - Línea azul: demanda predicha por el modelo (IA)
 *   - Línea verde: ocupación real observada (viajes registrados)
 *   - Área sombreada: banda de confianza [confidence_low, confidence_high]
 *
 * Props:
 *   predictions  [{ hour, predicted_passengers, confidence_low, confidence_high }]
 *   realData     [{ hour, real_passengers }]  — null values se omiten
 *   loading      bool
 */

import {
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

const HOUR_LABELS = Array.from({ length: 24 }, (_, h) =>
  `${String(h).padStart(2, '0')}:00`
);

function buildChartData(predictions, realData) {
  return Array.from({ length: 24 }, (_, h) => {
    const pred = predictions?.find((p) => p.hour === h);
    const real = realData?.find((r) => r.hour === h);
    return {
      hour: HOUR_LABELS[h],
      predicted: pred?.predicted_passengers ?? null,
      confLow: pred?.confidence_low ?? null,
      confHigh: pred?.confidence_high ?? null,
      // Recharts Area necesita [low, high] como array para la banda
      band: pred ? [pred.confidence_low, pred.confidence_high] : null,
      real: real?.real_passengers ?? null,
    };
  });
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: 'var(--card-bg, #1c2128)',
      border: '1px solid var(--border, #30363d)',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
    }}>
      <p style={{ color: 'var(--text-secondary, #8b949e)', marginBottom: 6 }}>{label}</p>
      {payload.map((entry) => (
        entry.value !== null && (
          <p key={entry.name} style={{ color: entry.color, margin: '2px 0' }}>
            {entry.name === 'predicted' && `Predicho: ${entry.value} pas.`}
            {entry.name === 'real' && `Real: ${entry.value} pas.`}
          </p>
        )
      ))}
    </div>
  );
};

export default function DemandChart({ predictions = [], realData = [], loading = false }) {
  if (loading) {
    return (
      <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!predictions.length) {
    return (
      <div style={{ height: 280, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary, #8b949e)', fontSize: 14 }}>
        Sin datos de predicción para esta fecha.
      </div>
    );
  }

  const data = buildChartData(predictions, realData);

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, left: -8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #30363d)" />
        <XAxis
          dataKey="hour"
          tick={{ fontSize: 11, fill: 'var(--text-secondary, #8b949e)' }}
          tickLine={false}
          interval={2}
        />
        <YAxis
          tick={{ fontSize: 11, fill: 'var(--text-secondary, #8b949e)' }}
          tickLine={false}
          axisLine={false}
          domain={[0, 'auto']}
          unit=" pas."
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          formatter={(value) => value === 'predicted' ? 'Predicho (IA)' : 'Real observado'}
        />

        {/* Banda de confianza */}
        <Area
          type="monotone"
          dataKey="band"
          fill="#388bfd"
          fillOpacity={0.12}
          stroke="none"
          legendType="none"
          connectNulls
        />

        {/* Línea predicha */}
        <Line
          type="monotone"
          dataKey="predicted"
          stroke="#388bfd"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          connectNulls
        />

        {/* Línea real */}
        <Line
          type="monotone"
          dataKey="real"
          stroke="#3fb950"
          strokeWidth={2}
          strokeDasharray="5 3"
          dot={{ r: 3, fill: '#3fb950' }}
          connectNulls
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
