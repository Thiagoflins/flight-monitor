"use client";

import { useMemo, useState } from "react";
import type { FlightRecord } from "@/lib/types";
import { PriceChart } from "@/components/PriceChart";
import { SummaryCards } from "@/components/SummaryCards";
import { RecentTable } from "@/components/RecentTable";
import { EmptyState } from "@/components/EmptyState";

interface DashboardProps {
  records: FlightRecord[];
}

export function Dashboard({ records }: DashboardProps) {
  const routeNames = useMemo(() => {
    const names = Array.from(new Set(records.map((record) => record.routeName)));
    return names.sort((a, b) => a.localeCompare(b, "pt-BR"));
  }, [records]);

  const [selectedRoute, setSelectedRoute] = useState<string | null>(routeNames[0] ?? null);

  const routeRecords = useMemo(() => {
    if (!selectedRoute) return [];
    return records
      .filter((record) => record.routeName === selectedRoute)
      .sort((a, b) => new Date(a.checkedAt).getTime() - new Date(b.checkedAt).getTime());
  }, [records, selectedRoute]);

  if (records.length === 0) {
    return <EmptyState />;
  }

  return (
    <div className="space-y-6">
      <div>
        <label htmlFor="route-select" className="mb-1 block text-sm font-medium text-neutral-600">
          Rota monitorada
        </label>
        <select
          id="route-select"
          value={selectedRoute ?? ""}
          onChange={(event) => setSelectedRoute(event.target.value)}
          className="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-neutral-500 focus:outline-none sm:max-w-xs"
        >
          {routeNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      <SummaryCards records={routeRecords} />

      <section className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm sm:p-6">
        <h2 className="mb-4 text-base font-semibold text-neutral-800">Evolução do preço</h2>
        <PriceChart records={routeRecords} />
      </section>

      <RecentTable records={routeRecords} />
    </div>
  );
}
