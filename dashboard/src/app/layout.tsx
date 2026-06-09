import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Monitor de Passagens — Painel",
  description: "Acompanhamento da evolução de preços de passagens aéreas monitoradas.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
