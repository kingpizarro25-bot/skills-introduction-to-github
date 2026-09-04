import { getConfig } from "@/config/env";
import type { AIProvider, AIResponse, ProviderOptions } from "@/types/ai";
import {
  ProviderError,
  bearer,
  chatMessages,
  nowIso,
  notConfigured,
  postJson,
  resolveLimits,
} from "./base";

interface PerplexityResponse {
  model?: string;
  choices?: Array<{ message?: { content?: string | null }; finish_reason?: string }>;
  usage?: { prompt_tokens?: number; completion_tokens?: number };
  /** Perplexity grounds answers in sources and returns them alongside the text. */
  citations?: string[];
  search_results?: Array<{ url?: string }>;
}

/** Perplexity adapter (OpenAI-compatible chat completions endpoint). */
export class PerplexityProvider implements AIProvider {
  readonly id = "perplexity";
  readonly name = "Perplexity";

  get model(): string {
    return getConfig().PERPLEXITY_MODEL;
  }

  isConfigured(): boolean {
    return Boolean(getConfig().PERPLEXITY_API_KEY);
  }

  async sendMessage(prompt: string, options: ProviderOptions = {}): Promise<AIResponse> {
    const config = getConfig();
    if (!config.PERPLEXITY_API_KEY) throw notConfigured(this.name, "PERPLEXITY_API_KEY");

    const limits = resolveLimits(options);
    const started = Date.now();

    const data = await postJson<PerplexityResponse>(
      {
        url: `${config.PERPLEXITY_BASE_URL}/chat/completions`,
        headers: bearer(config.PERPLEXITY_API_KEY),
        body: {
          model: this.model,
          messages: chatMessages(prompt, options.system),
          max_tokens: limits.maxOutputTokens,
          ...(limits.temperature !== undefined ? { temperature: limits.temperature } : {}),
        },
      },
      limits,
      options.signal,
    );

    const text = data.choices?.[0]?.message?.content?.trim();
    if (!text) {
      throw new ProviderError("server_error", "Perplexity returned an empty completion", {
        retryable: false,
      });
    }

    const citations =
      data.citations ??
      data.search_results?.map((r) => r.url).filter((u): u is string => Boolean(u));

    return {
      ok: true,
      provider: this.id,
      providerName: this.name,
      model: data.model ?? this.model,
      text,
      latencyMs: Date.now() - started,
      timestamp: nowIso(),
      finishReason: data.choices?.[0]?.finish_reason,
      usage: {
        inputTokens: data.usage?.prompt_tokens,
        outputTokens: data.usage?.completion_tokens,
      },
      ...(citations?.length ? { meta: { citations } } : {}),
    };
  }
}
