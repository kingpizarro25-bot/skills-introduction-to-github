import type { ProviderResult } from "@/types/ai";

/**
 * Citations arrive inside a provider's response — untrusted text that the
 * dashboard puts into an `href`. Anything that is not plain http(s) is dropped,
 * so a hostile or compromised provider cannot hand the user a `javascript:` or
 * `data:` link to click.
 */
export function isSafeUrl(value: unknown): value is string {
  if (typeof value !== "string") return false;
  try {
    const { protocol } = new URL(value);
    return protocol === "http:" || protocol === "https:";
  } catch {
    return false;
  }
}

/** The citation URLs of a result that are safe to render as links. */
export function safeCitations(result: ProviderResult): string[] {
  if (!result.ok) return [];
  const raw = (result.meta as { citations?: unknown } | undefined)?.citations;
  return Array.isArray(raw) ? raw.filter(isSafeUrl) : [];
}
