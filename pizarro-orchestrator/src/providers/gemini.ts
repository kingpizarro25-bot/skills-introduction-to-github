import { getConfig } from "@/config/env";
import type { AIProvider, AIResponse, ProviderOptions } from "@/types/ai";
import { ProviderError, nowIso, notConfigured, postJson, resolveLimits } from "./base";

/**
 * Google Gemini adapter (generateContent).
 *
 * Gemini's wire format differs from the other three: messages are `contents`
 * with `parts`, the system prompt is a separate `systemInstruction`, limits live
 * under `generationConfig`, and the model name goes in the URL path rather than
 * the body. All of that is contained here — the orchestrator sees the same
 * `AIResponse` it gets from every other provider.
 */

interface GenerateContentResponse {
  modelVersion?: string;
  candidates?: Array<{
    content?: { parts?: Array<{ text?: string }> };
    finishReason?: string;
  }>;
  usageMetadata?: { promptTokenCount?: number; candidatesTokenCount?: number };
  /** Set when the *prompt* was rejected outright, so no candidate is returned. */
  promptFeedback?: { blockReason?: string };
}

export class GeminiProvider implements AIProvider {
  readonly id = "gemini";
  readonly name = "Gemini";

  get model(): string {
    return getConfig().GEMINI_MODEL;
  }

  isConfigured(): boolean {
    return Boolean(getConfig().GEMINI_API_KEY);
  }

  async sendMessage(prompt: string, options: ProviderOptions = {}): Promise<AIResponse> {
    const config = getConfig();
    if (!config.GEMINI_API_KEY) throw notConfigured(this.name, "GEMINI_API_KEY");

    const limits = resolveLimits(options);
    const started = Date.now();

    const data = await postJson<GenerateContentResponse>(
      {
        // The model is part of the path here, unlike the other providers.
        url: `${config.GEMINI_BASE_URL}/models/${this.model}:generateContent`,
        // Sent as a header rather than a query param so the key never lands in
        // a URL, where proxies and access logs would capture it.
        headers: { "x-goog-api-key": config.GEMINI_API_KEY },
        body: {
          contents: [{ role: "user", parts: [{ text: prompt }] }],
          ...(options.system
            ? { systemInstruction: { parts: [{ text: options.system }] } }
            : {}),
          generationConfig: {
            maxOutputTokens: limits.maxOutputTokens,
            ...(limits.temperature !== undefined ? { temperature: limits.temperature } : {}),
          },
        },
      },
      limits,
      options.signal,
    );

    const candidate = data.candidates?.[0];
    const text = (candidate?.content?.parts ?? [])
      .map((part) => part.text)
      .filter((t): t is string => typeof t === "string")
      .join("")
      .trim();

    if (!text) {
      // Gemini returns 200 with no text when a safety filter fires or the
      // output hits the token cap mid-thought. Say which, instead of a bare
      // "empty response" — and never retry, since a retry changes nothing.
      const reason =
        data.promptFeedback?.blockReason ?? candidate?.finishReason ?? "unknown reason";
      throw new ProviderError(
        "server_error",
        `Gemini returned no text (${reason}).` +
          (reason === "MAX_TOKENS" ? " Try raising MAX_OUTPUT_TOKENS." : ""),
        { retryable: false },
      );
    }

    return {
      ok: true,
      provider: this.id,
      providerName: this.name,
      model: data.modelVersion ?? this.model,
      text,
      latencyMs: Date.now() - started,
      timestamp: nowIso(),
      finishReason: candidate?.finishReason,
      usage: {
        inputTokens: data.usageMetadata?.promptTokenCount,
        outputTokens: data.usageMetadata?.candidatesTokenCount,
      },
    };
  }
}
