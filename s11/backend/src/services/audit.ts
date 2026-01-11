import { exec } from 'child_process';
import fs from 'fs';
import path from 'path';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface AuditResult {
  vulnerabilities: Array<{
    severity: string;
    title: string;
    description: string;
    line: number;
  }>;
  output: string;
}

export async function runAudit(sourceCode: string, contractName: string): Promise<AuditResult> {
  const tempDir = path.join(__dirname, '../../temp');
  if (!fs.existsSync(tempDir)) {
    fs.mkdirSync(tempDir);
  }

  const filePath = path.join(tempDir, `${contractName}.sol`);
  fs.writeFileSync(filePath, sourceCode);

  try {
    // Assume slither is installed
    const { stdout, stderr } = await execAsync(`slither ${filePath} --json -`);
    const output = stdout + stderr;

    // Parse JSON output (simplified)
    // Slither outputs JSON, parse it
    const results = JSON.parse(output);

    const vulnerabilities = results.map((result: any) => ({
      severity: result.severity || 'unknown',
      title: result.title || 'Issue',
      description: result.description || '',
      line: result.line || 0,
    }));

    return {
      vulnerabilities,
      output,
    };
  } catch (error: any) {
    return {
      vulnerabilities: [],
      output: error.message,
    };
  } finally {
    // Clean up
    fs.unlinkSync(filePath);
  }
}