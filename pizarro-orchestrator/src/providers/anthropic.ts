import { getConfig } from "@/config/env";
import type { AIProvider, AIResponse, ProviderOptions } from "@/types/ai";
import { ProviderError, nowIso, notConfigured, postJson, resolveLimits } from "./base";

interface MessagesResponse {
  model?: string;
  content?: Array<{ type?: string; text?: string }>;
  stop_reason?: string;
  usage?: { input_tokens?: number; output_tokens?: number };
}

/** Anthropic Messages API adapter. */
export class AnthropicProvider implements AIProvider {
  readonly id = "anthropic";
  readonly name = "Claude";

  get model(): string {
    return getConfig().ANTHROPIC_MODEL;
  }

  isConfigured(): boolean {
    return Boolean(getConfig().ANTHROPIC_API_KEY);
  }

  async sendMessage(prompt: string, options: ProviderOptions = {}): Promise<AIResponse> {
    const config = getConfig();
    if (!config.ANTHROPIC_API_KEY) throw notConfigured(this.name, "ANTHROPIC_API_KEY");

    const limits = resolveLimits(options);
    const started = Date.now();

    const data = await postJson<MessagesResponse>(
      {
        url: `${config.ANTHROPIC_BASE_URL}/messages`,
        headers: {
          "x-api-key": config.ANTHROPIC_API_KEY,
          "anthropic-version": "2023-06-01",
        },
        body: {
          model: this.model,
          // max_tokens is required by the Messages API.
          max_tokens: limits.maxOutputTokens,
          messages: [{ role: "user", content: prompt }],
          ...(options.system ? { system: options.system } : {}),
          ...(limits.temperature !== undefined ? { temperature: limits.temperature } : {}),
        },
      },
      limits,
      options.signal,
    );

    const text = (data.content ?? [])
      .filter((block) => block.type === "text" && typeof block.text === "string")
      .map((block) => block.text as string)
      .join("\n")
      .trim();

    if (!text) {
      throw new ProviderError("server_error", "Claude returned an empty completion", {
        retryable: false,
      });
    }

    return {
      ok: true,
      provider: this.id,
      providerName: this.name,
      model: data.model ?? this.model,
      text,
      latencyMs: Date.now() - started,
      timestamp: nowIso(),
      finishReason: data.stop_reason,
      usage: {
        inputTokens: data.usage?.input_tokens,
        outputTokens: data.usage?.output_tokens,
      },
    };
  }
}
