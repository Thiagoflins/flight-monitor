import Papa from "papaparse";
import type { FlightRecord } from "./types";

/**
 * Faz o parse do data/history.csv gerado pelo monitor.py.
 *
 * Colunas esperadas: checked_at, route_name, origin, destination,
 * departure_at, return_at, price, currency, airline, transfers, link.
 *
 * É tolerante a linhas malformadas: qualquer linha sem os campos mínimos
 * (checked_at, route_name e price numérico) é simplesmente ignorada, em vez
 * de quebrar o parse inteiro.
 */
export function parseHistoryCsv(csvText: string): FlightRecord[] {
  const trimmed = csvText.trim();
  if (!trimmed) return [];

  const result = Papa.parse<Record<string, string>>(trimmed, {
    header: true,
    skipEmptyLines: true,
  });

  const records: FlightRecord[] = [];

  for (const row of result.data) {
    const price = parseNumber(row.price);
    if (!row.checked_at || !row.route_name || price === null) {
      continue;
    }

    records.push({
      checkedAt: row.checked_at,
      routeName: row.route_name,
      origin: row.origin ?? "",
      destination: row.destination ?? "",
      departureAt: row.departure_at ?? "",
      returnAt: row.return_at ? row.return_at : null,
      price,
      currency: (row.currency || "brl").toUpperCase(),
      airline: row.airline || "—",
      transfers: parseNumber(row.transfers),
      link: row.link || "",
    });
  }

  return records;
}

function parseNumber(value: string | undefined): number | null {
  if (value === undefined || value === null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
