import { buildOkoRequestHeaders, resolveRequestUrl } from "@/features/services/requestJson";

export interface OkoSseEvent {
  id: string;
  event: string;
  data: unknown;
}

export interface OkoSseStream {
  close: () => void;
}

interface ConnectOptions {
  path: string;
  onEvent: (event: OkoSseEvent) => void;
  onError?: (error: unknown) => void;
}

interface ParsedEventFrame {
  id: string;
  event: string;
  data: string;
}

function parseEventFrame(frame: string): ParsedEventFrame | null {
  const lines = frame.split("\n");

  let id = "";
  let event = "message";
  const dataLines: string[] = [];

  for (const rawLine of lines) {
    const line = String(rawLine || "");
    if (!line || line.startsWith(":")) {
      continue;
    }

    const splitIndex = line.indexOf(":");
    const field = splitIndex >= 0 ? line.slice(0, splitIndex).trim() : line.trim();
    const value = splitIndex >= 0 ? line.slice(splitIndex + 1).trimStart() : "";

    if (field === "id") {
      id = value;
      continue;
    }
    if (field === "event") {
      event = value || "message";
      continue;
    }
    if (field === "data") {
      dataLines.push(value);
    }
  }

  if (!dataLines.length) {
    return null;
  }

  return {
    id,
    event,
    data: dataLines.join("\n"),
  };
}

export function connectOkoSseStream(options: ConnectOptions): OkoSseStream {
  const { path, onEvent, onError } = options;
  const abortController = new AbortController();

  (async () => {
    const response = await fetch(resolveRequestUrl(path), {
      method: "GET",
      headers: {
        Accept: "text/event-stream",
        ...buildOkoRequestHeaders(),
      },
      credentials: "include",
      cache: "no-store",
      signal: abortController.signal,
    });

    if (!response.ok) {
      throw new Error(`SSE stream request failed: ${response.status}`);
    }

    if (!response.body) {
      throw new Error("SSE stream has no body");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder
        .decode(value, { stream: true })
        .replaceAll("\r\n", "\n")
        .replaceAll("\r", "\n");
      let separatorIndex = buffer.indexOf("\n\n");
      while (separatorIndex >= 0) {
        const frame = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);

        const parsed = parseEventFrame(frame);
        if (parsed) {
          let payload: unknown = parsed.data;
          try {
            payload = JSON.parse(parsed.data);
          } catch {
            // Keep raw payload when server sends non-JSON event data.
          }

          onEvent({
            id: parsed.id,
            event: parsed.event,
            data: payload,
          });
        }

        separatorIndex = buffer.indexOf("\n\n");
      }
    }
  })().catch((error: unknown) => {
    if (abortController.signal.aborted) {
      return;
    }
    onError?.(error);
  });

  return {
    close: () => {
      abortController.abort();
    },
  };
}
