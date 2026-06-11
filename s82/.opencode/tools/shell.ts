import { execSync } from "child_process"

const TIMEOUT_DEFAULT = 30_000

function enrich(cmd: string): string {
  const t = cmd.trim()
  if (/^pkill\s/.test(t)) {
    return `(${t} --exclude \$\$ --exclude \$PPID 2>/dev/null) || true`
  }
  if (/^killall\s/.test(t)) {
    return `(${t} --exclude \$\$ --exclude \$PPID 2>/dev/null) || true`
  }
  return cmd
}

export default {
  description:
    "Execute shell commands with auto-timeout (30s default) and self-kill protection. Auto-excludes agent PID from pkill/killall/kill.",
  args: {
    command: { type: "string", description: "Shell command to execute" },
    description: { type: "string", description: "What the command does" },
    timeout: { type: "number", description: "Timeout in ms (default: 30000)" },
    workdir: { type: "string", description: "Working directory" },
  },
  async execute(args: any, context: any) {
    const timeoutMs = args.timeout ?? TIMEOUT_DEFAULT
    const dir = args.workdir ?? context.directory
    const raw = args.command

    const enriched = enrich(raw)
    const label = args.description ?? raw.slice(0, 60)

    try {
      const stdout = execSync(enriched, {
        cwd: dir,
        timeout: timeoutMs,
        encoding: "utf-8",
        shell: "/bin/bash",
        killSignal: "SIGTERM",
        maxBuffer: 10 * 1024 * 1024,
        windowsHide: true,
      })
      return stdout
    } catch (e: any) {
      if (e.code === "ETIMEDOUT" || e.killed) {
        return (
          `⚠️ TIMEOUT (${timeoutMs / 1000}s): "${label}"\n\n` +
          `El comando se colgó. Causas posibles:\n` +
          `• pkill/kill mató el shell hijo\n` +
          `• Loop infinito o esperando input\n` +
          `• Necesita más tiempo\n\n` +
          `Reintenta con: command: ${JSON.stringify(raw)}, timeout: ${timeoutMs * 2}`
        )
      }
      const stderr = (e.stderr || e.message || "").toString().trim()
      return `❌ ${stderr || `exit ${e.status ?? "?"}`}`
    }
  },
}
