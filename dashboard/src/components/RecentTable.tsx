import type { FlightRecord } from "@/lib/types";
import { formatCurrency, formatDateTime } from "@/lib/format";

interface RecentTableProps {
  records: FlightRecord[];
  limit?: number;
}

export function RecentTable({ records, limit = 10 }: RecentTableProps) {
  const recent = [...records].reverse().slice(0, limit);

  if (recent.length === 0) {
    return null;
  }

  return (
    <section className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm sm:p-6">
      <h2 className="mb-4 text-base font-semibold text-neutral-800">Últimos registros</h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead>
            <tr className="border-b border-neutral-200 text-xs uppercase tracking-wide text-neutral-500">
              <th className="py-2 pr-4 font-medium">Checagem</th>
              <th className="py-2 pr-4 font-medium">Preço</th>
              <th className="py-2 pr-4 font-medium">Companhia</th>
              <th className="py-2 pr-4 font-medium">Paradas</th>
              <th className="py-2 font-medium">Link</th>
            </tr>
          </thead>
          <tbody>
            {recent.map((record, index) => (
              <tr key={`${record.checkedAt}-${index}`} className="border-b border-neutral-100 last:border-0">
                <td className="py-2 pr-4 text-neutral-600">{formatDateTime(record.checkedAt)}</td>
                <td className="py-2 pr-4 font-medium text-neutral-900">
                  {formatCurrency(record.price, record.currency)}
                </td>
                <td className="py-2 pr-4 text-neutral-600">{record.airline}</td>
                <td className="py-2 pr-4 text-neutral-600">{formatTransfers(record.transfers)}</td>
                <td className="py-2">
                  {record.link ? (
                    <a
                      href={record.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 underline-offset-2 hover:underline"
                    >
                      ver oferta
                    </a>
                  ) : (
                    <span className="text-neutral-300">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function formatTransfers(transfers: number | null): string {
  if (transfers === null) return "—";
  if (transfers === 0) return "voo direto";
  return `${transfers} parada${transfers > 1 ? "s" : ""}`;
}
