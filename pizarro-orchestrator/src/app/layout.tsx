import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pizarro Multi-AI Orchestrator",
  description: "Coordinate OpenAI, Claude and Perplexity behind one workflow engine.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
