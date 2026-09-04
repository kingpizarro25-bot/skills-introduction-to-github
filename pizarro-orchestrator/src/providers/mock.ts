import { getConfig } from "@/config/env";
import type { AIProvider, AIResponse, ProviderOptions } from "@/types/ai";
import { nowIso, resolveLimits } from "./base";

/**
 * DEVELOPMENT-ONLY fake provider.
 *
 * It exists so the workflow engine and dashboard can be exercised without
 * spending money or holding real keys. It is off unless ENABLE_MOCK_PROVIDER=true,
 * every response it produces is prefixed with a banner, and `mock: true` is
 * carried through the API so the UI can mark it. It is never used as a
 * substitute for a provider that failed or is unconfigured.
 */
export const MOCK_BANNER = "[MOCK RESPONSE — NOT A REAL MODEL]";

export class MockProvider implements AIProvider {
  readonly id = "mock";
  readonly name = "Mock (DEV ONLY — not a real model)";
  readonly model = "mock-1";

  isConfigured(): boolean {
    return getConfig().ENABLE_MOCK_PROVIDER;
  }

  async sendMessage(prompt: string, options: ProviderOptions = {}): Promise<AIResponse> {
    const limits = resolveLimits(options);
    const started = Date.now();
    // A tiny delay keeps parallel/latency behaviour realistic in the UI.
    await new Promise((resolve) => setTimeout(resolve, 25));

    const preview = prompt.length > 240 ? `${prompt.slice(0, 240)}…` : prompt;
    return {
      ok: true,
      provider: this.id,
      providerName: this.name,
      model: this.model,
      text: `${MOCK_BANNER}\n\nThis text was generated locally, not by any AI provider.\n\nTask received:\n${preview}`,
      latencyMs: Date.now() - started,
      timestamp: nowIso(),
      finishReason: "stop",
      meta: { mock: true, maxOutputTokens: limits.maxOutputTokens },
    };
  }
}
