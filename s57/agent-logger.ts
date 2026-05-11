import type { Plugin } from "@opencode-ai/plugin";
import { appendFileSync, existsSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { homedir } from "os";

const HISTORY_FILE = join(
  homedir(),
  ".local/state/opencode/assistant-history.jsonl",
);

/**
 * Agent Logger Plugin
 * ====================
 * Escribe cada mensaje del asistente a assistant-history.jsonl.
 * agent-watch lo monitorea y lo muestra en el Monitor TUI.
 */
const AgentLoggerPlugin: Plugin = async () => {
  // Asegurar que el directorio exista
  const dir = dirname(HISTORY_FILE);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  return {
    "chat.message": async (_input, output) => {
      const message = output.message;
      if (message.role !== "assistant") return;

      // Extraer texto de los parts (tipo "text")
      const textParts = output.parts.filter((p: any) => p.type === "text");
      if (textParts.length === 0) return;

      const fullText = textParts
        .map((p: any) => p.text)
        .join("\n")
        .trim();
      if (!fullText) return;

      // Construir payload
      const entry = {
        type: "assistant",
        agent: message.agent ?? "orchestrator",
        model: message.modelID ?? "",
        provider: message.providerID ?? "",
        level: "ASSISTANT",
        content: fullText.slice(0, 1000),
        sessionID: message.sessionID,
        cost: (message as any).cost ?? 0,
        tokens: (message as any).tokens ?? {},
      };

      try {
        appendFileSync(HISTORY_FILE, JSON.stringify(entry) + "\n");
      } catch {
        // Si falla, ignorar silenciosamente
      }
    },
  };
};

export default AgentLoggerPlugin;
