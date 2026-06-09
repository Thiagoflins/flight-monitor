import { getFlightHistory } from "@/lib/data";
import { getActiveRouteNames } from "@/lib/config";
import type { FlightRecord } from "@/lib/types";
import { Dashboard } from "@/components/Dashboard";

export const revalidate = 900; // 15 minutos — alinhado ao fetch remoto do CSV

export default async function Home() {
  let records: FlightRecord[] = [];
  let error: string | null = null;

  try {
    const [allRecords, activeNames] = await Promise.all([
      getFlightHistory(),
      getActiveRouteNames(),
    ]);
    // history.csv é append-only; filtra para mostrar só rotas ativas no config.json.
    const activeSet = new Set(activeNames);
    records = activeSet.size === 0
      ? allRecords
      : allRecords.filter((r) => activeSet.has(r.routeName));
  } catch (err) {
    error = err instanceof Error ? err.message : "Erro desconhecido ao carregar os dados.";
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 sm:py-10">
      <header className="mb-6 sm:mb-10">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">✈️ Monitor de Passagens</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Evolução dos preços coletados automaticamente para as rotas monitoradas.
        </p>
      </header>

      {error && (
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Não foi possível carregar os dados: {error}
        </div>
      )}

      <Dashboard records={records} />
    </main>
  );
}
