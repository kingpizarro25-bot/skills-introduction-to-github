import { getConfig } from "@/config/env";
import type { AIProvider, ProviderId, ProviderInfo } from "@/types/ai";
import { AnthropicProvider } from "./anthropic";
import { GeminiProvider } from "./gemini";
import { MockProvider } from "./mock";
import { OpenAIProvider } from "./openai";
import { PerplexityProvider } from "./perplexity";

/**
 * The single place the rest of the system learns which providers exist.
 *
 * TO ADD A PROVIDER (e.g. Gemini, Grok, a local model):
 *   1. Write `src/providers/gemini.ts` implementing `AIProvider`.
 *   2. Add its key/model/base-url to `src/config/env.ts` and `.env.example`.
 *   3. Add one line to `ALL_PROVIDERS` below.
 * Nothing in `src/orchestrator/` needs to change.
 */
const ALL_PROVIDERS: AIProvider[] = [
  new OpenAIProvider(),
  new AnthropicProvider(),
  new PerplexityProvider(),
  new GeminiProvider(),
  new MockProvider(),
];

const MOCK_IDS = new Set(["mock"]);

/** Providers not switched off via DISABLED_PROVIDERS. */
export function listProviders(): AIProvider[] {
  const disabled = new Set(getConfig().disabledProviders);
  return ALL_PROVIDERS.filter((p) => !disabled.has(p.id))
    // The mock provider is hidden entirely unless explicitly enabled.
    .filter((p) => !MOCK_IDS.has(p.id) || p.isConfigured());
}

export function getProvider(id: ProviderId): AIProvider | undefined {
  return listProviders().find((p) => p.id === id);
}

/**
 * Resolve a provider for actual use. Returns a reason string instead of a
 * provider when it cannot be used — the caller surfaces that verbatim rather
 * than substituting another model.
 */
export function requireProvider(
  id: ProviderId,
): { provider: AIProvider } | { error: string } {
  const disabled = new Set(getConfig().disabledProviders);
  if (disabled.has(id)) return { error: `Provider '${id}' is disabled by DISABLED_PROVIDERS.` };

  const provider = getProvider(id);
  if (!provider) return { error: `Unknown provider '${id}'.` };
  if (!provider.isConfigured()) return { error: `Provider not configured (${provider.name}).` };
  return { provider };
}

/** Dashboard-facing view: what exists, what is usable, and why not. */
export function describeProviders(): ProviderInfo[] {
  const disabled = new Set(getConfig().disabledProviders);
  return ALL_PROVIDERS.filter((p) => !MOCK_IDS.has(p.id) || p.isConfigured()).map((p) => {
    const isDisabled = disabled.has(p.id);
    const configured = p.isConfigured();
    return {
      id: p.id,
      name: p.name,
      model: p.model,
      configured,
      enabled: configured && !isDisabled,
      status: isDisabled
        ? "Disabled by configuration"
        : configured
          ? "Ready"
          : "Provider not configured",
      mock: MOCK_IDS.has(p.id),
    };
  });
}

export function isMockProvider(id: ProviderId): boolean {
  return MOCK_IDS.has(id);
}
