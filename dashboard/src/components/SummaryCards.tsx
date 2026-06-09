import type { FlightRecord } from "@/lib/types";
import { formatCurrency, formatDateTime } from "@/lib/format";

interface SummaryCardsProps {
  records: FlightRecord[];
}

export function SummaryCards({ records }: SummaryCardsProps) {
  if (records.length === 0) {
    return null;
  }

  const currency = records[0].currency;
  const lowest = records.reduce((min, record) => (record.price < min.price ? record : min), records[0]);
  const latest = records[records.length - 1];
  const previous = records.length > 1 ? records[records.length - 2] : null;

  const variation = previous ? latest.price - previous.price : null;
  const variationPct =
    previous && previous.price !== 0 && variation !== null ? (variation / previous.price) * 100 : null;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
      <Card
        label="Menor preço já visto"
        value={formatCurrency(lowest.price, currency)}
        hint={`em ${formatDateTime(lowest.checkedAt)}`}
      />
      <Card
        label="Preço atual"
        value={formatCurrency(latest.price, currency)}
        hint={`última checagem: ${formatDateTime(latest.checkedAt)}`}
      />
      <VariationCard variation={variation} variationPct={variationPct} currency={currency} />
    </div>
  );
}

function Card({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-neutral-900">{value}</p>
      {hint && <p className="mt-1 text-xs text-neutral-400">{hint}</p>}
    </div>
  );
}

function VariationCard({
  variation,
  variationPct,
  currency,
}: {
  variation: number | null;
  variationPct: number | null;
  currency: string;
}) {
  if (variation === null || variationPct === null) {
    return (
      <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
        <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">Variação</p>
        <p className="mt-1 text-2xl font-bold text-neutral-300">—</p>
        <p className="mt-1 text-xs text-neutral-400">ainda não há checagem anterior para comparar</p>
      </div>
    );
  }

  const isUp = variation > 0;
  const isDown = variation < 0;
  const colorClass = isUp ? "text-red-600" : isDown ? "text-emerald-600" : "text-neutral-500";
  const arrow = isUp ? "↑" : isDown ? "↓" : "→";
  const sign = variation > 0 ? "+" : "";

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p className="text-xs font-medium uppercase tracking-wide text-neutral-500">
        Variação (vs. checagem anterior)
      </p>
      <p className={`mt-1 text-2xl font-bold ${colorClass}`}>
        {arrow} {Math.abs(variationPct).toFixed(1)}%
      </p>
      <p className="mt-1 text-xs text-neutral-400">
        {sign}
        {formatCurrency(variation, currency)}
      </p>
    </div>
  );
}
