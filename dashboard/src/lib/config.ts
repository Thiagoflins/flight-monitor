import { promises as fs } from "fs";
import path from "path";

/**
 * Lê o `config.json` (raiz do repo) e devolve os nomes das rotas ativas.
 *
 * - Em produção: deriva a URL do config a partir de HISTORY_CSV_URL,
 *   trocando "/data/history.csv" por "/config.json".
 * - Em dev: lê `../config.json` direto do disco.
 *
 * Usado pelo dashboard para filtrar `history.csv` (append-only) e mostrar
 * só o que está sendo monitorado hoje.
 */
export async function getActiveRouteNames(): Promise<string[]> {
  const text = await loadConfigText();
  if (!text) return [];
  try {
    const json = JSON.parse(text);
    const routes = Array.isArray(json?.routes) ? json.routes : [];
    return routes
      .map((r: { name?: string }) => r?.name)
      .filter((n: unknown): n is string => typeof n === "string" && n.length > 0);
  } catch {
    return [];
  }
}

async function loadConfigText(): Promise<string> {
  const historyUrl = process.env.HISTORY_CSV_URL;
  if (historyUrl) {
    const configUrl = historyUrl.replace(/\/data\/history\.csv$/, "/config.json");
    const headers: Record<string, string> = {};
    const token = process.env.GITHUB_TOKEN;
    if (token) headers.Authorization = `Bearer ${token}`;

    const response = await fetch(configUrl, {
      headers,
      next: { revalidate: 60 * 15 },
    });
    if (!response.ok) {
      throw new Error(
        `Falha ao buscar config.json (${response.status} ${response.statusText})`,
      );
    }
    return response.text();
  }

  const localPath = path.join(process.cwd(), "..", "config.json");
  try {
    return await fs.readFile(localPath, "utf-8");
  } catch {
    return "";
  }
}
