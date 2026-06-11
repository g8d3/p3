import { execSync } from "child_process"

const DEFAULT_TIMEOUT = 30_000

export default {
  description: "Bash con timeout automático de 30s. Nunca se traba.",
  args: {
    command: { type: "string", description: "Comando a ejecutar" },
    description: { type: "string", description: "Descripción" },
    timeout: { type: "number", description: "Timeout en ms (default 30000)" },
    workdir: { type: "string", description: "Directorio de trabajo" },
  },
  async execute(args: any, ctx: any) {
    const ms = args.timeout ?? DEFAULT_TIMEOUT
    const dir = args.workdir ?? ctx.directory
    const cmd = args.command

    try {
      return execSync(cmd, {
        cwd: dir, timeout: ms, encoding: "utf-8",
        shell: "/bin/bash", killSignal: "SIGTERM",
        maxBuffer: 10 * 1024 * 1024, windowsHide: true,
      })
    } catch (e: any) {
      if (e.code === "ETIMEDOUT" || e.killed) {
        return `⏱️ TIMEOUT ${ms / 1000}s: "${cmd}"`
      }
      return (e.stderr || e.message || "").toString().trim() || `exit ${e.status ?? "?"}`
    }
  },
}
