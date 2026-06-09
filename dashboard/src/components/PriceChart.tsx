"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { FlightRecord } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/format";

interface PriceChartProps {
  records: FlightRecord[];
}

export function PriceChart({ records }: PriceChartProps) {
  if (records.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-neutral-400">
        Ainda não há dados suficientes para montar o gráfico desta rota.
      </p>
    );
  }

  const currency = records[0].currency;
  const data = records.map((record) => ({
    label: formatDate(record.checkedAt),
    price: record.price,
  }));

  return (
    <div className="h-72 w-full sm:h-96">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#6b7280" }} minTickGap={24} />
          <YAxis
            tick={{ fontSize: 12, fill: "#6b7280" }}
            width={76}
            tickFormatter={(value: number) => formatCurrency(value, currency)}
          />
          <Tooltip
            formatter={(value: number) => [formatCurrency(value, currency), "Preço"]}
            labelFormatter={(label: string) => `Checagem: ${label}`}
            contentStyle={{ borderRadius: 8, borderColor: "#e5e7eb", fontSize: 13 }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
