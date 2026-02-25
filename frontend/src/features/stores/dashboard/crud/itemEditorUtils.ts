import type { DashboardItemHealthcheck } from "@/features/stores/dashboard/storeTypes";

export function createDashboardCrudItemEditorUtils() {
  function normalizeStringList(rawValue: unknown): string[] {
    if (Array.isArray(rawValue)) {
      return rawValue
        .map((value) => String(value || "").trim())
        .filter(Boolean);
    }
    return String(rawValue || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean);
  }

  function parseBooleanFlag(rawValue: unknown): boolean | null {
    if (typeof rawValue === "boolean") return rawValue;
    if (typeof rawValue === "string") {
      const normalized = rawValue.trim().toLowerCase();
      if (["1", "true", "yes", "on"].includes(normalized)) return true;
      if (["0", "false", "no", "off"].includes(normalized)) return false;
      return null;
    }
    if (typeof rawValue === "number") {
      if (rawValue === 1) return true;
      if (rawValue === 0) return false;
    }
    return null;
  }

  function resolveHealthcheckTlsVerify(
    healthcheck: DashboardItemHealthcheck | undefined,
  ): boolean {
    if (!healthcheck || typeof healthcheck !== "object") return true;
    const explicitTlsVerify = parseBooleanFlag(healthcheck.tls_verify);
    if (explicitTlsVerify != null) return explicitTlsVerify;
    const legacyVerifyTls = parseBooleanFlag(healthcheck.verify_tls);
    if (legacyVerifyTls != null) return legacyVerifyTls;
    const insecureSkipVerify = parseBooleanFlag(healthcheck.insecure_skip_verify);
    if (insecureSkipVerify != null) return !insecureSkipVerify;
    return true;
  }

  function clampNumber(
    value: unknown,
    fallback: number,
    min: number,
    max: number,
  ): number {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return fallback;
    const integerValue = Math.trunc(numeric);
    return Math.min(max, Math.max(min, integerValue));
  }

  return {
    clampNumber,
    normalizeStringList,
    parseBooleanFlag,
    resolveHealthcheckTlsVerify,
  };
}
