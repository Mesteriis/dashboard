export function ensureAbsoluteHttpUrl(rawValue) {
  const trimmed = String(rawValue || "").trim();
  if (!trimmed) {
    throw new Error("URL не может быть пустым");
  }

  const withProtocol = /^https?:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed}`;
  let parsed;
  try {
    parsed = new URL(withProtocol);
  } catch {
    throw new Error(`Некорректный URL: ${trimmed}`);
  }

  if (!["http:", "https:"].includes(parsed.protocol)) {
    throw new Error(`Разрешены только http/https URL: ${trimmed}`);
  }

  return parsed.toString();
}

export function originFromHttpUrl(rawValue) {
  const trimmed = String(rawValue || "").trim();
  if (!trimmed) return "";

  const withProtocol = /^https?:\/\//i.test(trimmed)
    ? trimmed
    : `https://${trimmed}`;
  try {
    const parsed = new URL(withProtocol);
    if (!["http:", "https:"].includes(parsed.protocol)) return "";
    return parsed.origin;
  } catch {
    return "";
  }
}
