export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-neutral-300 bg-white px-6 py-16 text-center">
      <p className="text-3xl">🛫</p>
      <h2 className="mt-3 text-lg font-semibold text-neutral-800">Ainda sem dados para mostrar</h2>
      <p className="mt-1 max-w-sm text-sm text-neutral-500">
        Assim que o monitor (<code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs">monitor.py</code>)
        rodar pelo menos uma vez e gerar registros em{" "}
        <code className="rounded bg-neutral-100 px-1.5 py-0.5 text-xs">data/history.csv</code>, os
        gráficos e a tabela aparecem aqui automaticamente.
      </p>
    </div>
  );
}
