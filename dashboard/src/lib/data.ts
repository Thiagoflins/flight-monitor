import { promises as fs } from "fs";
import path from "path";
import { parseHistoryCsv } from "./csv";
import type { FlightRecord } from "./types";

/**
 * Carrega e parseia o histórico de preços (data/history.csv).
 *
 * - Em produção (ex: Vercel): se HISTORY_CSV_URL estiver definida, busca o
 *   CSV remotamente (ex: raw.githubusercontent.com/<user>/<repo>/main/data/history.csv).
 *   Se o repositório for privado, defina também GITHUB_TOKEN — o token é
 *   enviado como "Authorization: Bearer <token>".
 * - Em desenvolvimento: se HISTORY_CSV_URL não estiver definida, lê o arquivo
 *   local em ../data/history.csv (relativo à pasta dashboard/).
 */
export async function getFlightHistory(): Promise<FlightRecord[]> {
  const csvText = await loadCsvText();
  return parseHistoryCsv(csvText);
}

async function loadCsvText(): Promise<string> {
  const remoteUrl = process.env.HISTORY_CSV_URL;
  if (remoteUrl) {
    return fetchRemoteCsv(remoteUrl);
  }
  return readLocalCsv();
}

async function fetchRemoteCsv(url: string): Promise<string> {
  const headers: Record<string, string> = {};
  const token = process.env.GITHUB_TOKEN;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    headers,
    // Os preços já são de cache na origem e o monitor roda a cada poucas
    // horas — não precisamos buscar a cada requisição.
    next: { revalidate: 60 * 15 },
  });

  if (!response.ok) {
    throw new Error(
      `Falha ao buscar history.csv em HISTORY_CSV_URL (${response.status} ${response.statusText})`
    );
  }

  return response.text();
}

async function readLocalCsv(): Promise<string> {
  const localPath = path.join(process.cwd(), "..", "data", "history.csv");
  try {
    return await fs.readFile(localPath, "utf-8");
  } catch {
    // Ainda sem histórico (monitor.py nunca rodou) — trate como CSV vazio.
    return "";
  }
}
