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

interface ChatCompletionResponse {
  model?: string;
  choices?: Array<{ message?: { content?: string | null }; finish_reason?: string }>;
  usage?: { prompt_tokens?: number; completion_tokens?: number };
}

/** OpenAI Chat Completions adapter. */
export class OpenAIProvider implements AIProvider {
  readonly id = "openai";
  readonly name = "OpenAI";

  get model(): string {
    return getConfig().OPENAI_MODEL;
  }

  isConfigured(): boolean {
    return Boolean(getConfig().OPENAI_API_KEY);
  }

  async sendMessage(prompt: string, options: ProviderOptions = {}): Promise<AIResponse> {
    const config = getConfig();
    if (!config.OPENAI_API_KEY) throw notConfigured(this.name, "OPENAI_API_KEY");

    const limits = resolveLimits(options);
    const started = Date.now();

    const send = (tokenParam: "max_completion_tokens" | "max_tokens") =>
      postJson<ChatCompletionResponse>(
        {
          url: `${config.OPENAI_BASE_URL}/chat/completions`,
          headers: bearer(config.OPENAI_API_KEY!),
          body: {
            model: this.model,
            messages: chatMessages(prompt, options.system),
            [tokenParam]: limits.maxOutputTokens,
            ...(limits.temperature !== undefined ? { temperature: limits.temperature } : {}),
          },
        },
        limits,
        options.signal,
      );

    let data: ChatCompletionResponse;
    try {
      data = await send("max_completion_tokens");
    } catch (err) {
      // Older deployments only accept `max_tokens`; newer reasoning models only
      // accept `max_completion_tokens`. Try the legacy name once before failing.
      if (err instanceof ProviderError && err.code === "bad_request" && /max_completion_tokens/i.test(err.message)) {
        data = await send("max_tokens");
      } else {
        throw err;
      }
    }

    const text = data.choices?.[0]?.message?.content?.trim();
    if (!text) {
      throw new ProviderError("server_error", "OpenAI returned an empty completion", {
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
      finishReason: data.choices?.[0]?.finish_reason,
      usage: {
        inputTokens: data.usage?.prompt_tokens,
        outputTokens: data.usage?.completion_tokens,
      },
    };
  }
}
