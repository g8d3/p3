"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.runAudit = runAudit;
const child_process_1 = require("child_process");
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const util_1 = require("util");
const execAsync = (0, util_1.promisify)(child_process_1.exec);
async function runAudit(sourceCode, contractName) {
    const tempDir = path_1.default.join(__dirname, '../../temp');
    if (!fs_1.default.existsSync(tempDir)) {
        fs_1.default.mkdirSync(tempDir);
    }
    const filePath = path_1.default.join(tempDir, `${contractName}.sol`);
    fs_1.default.writeFileSync(filePath, sourceCode);
    try {
        // Assume slither is installed
        const { stdout, stderr } = await execAsync(`slither ${filePath} --json -`);
        const output = stdout + stderr;
        // Parse JSON output (simplified)
        // Slither outputs JSON, parse it
        const results = JSON.parse(output);
        const vulnerabilities = results.map((result) => ({
            severity: result.severity || 'unknown',
            title: result.title || 'Issue',
            description: result.description || '',
            line: result.line || 0,
        }));
        return {
            vulnerabilities,
            output,
        };
    }
    catch (error) {
        return {
            vulnerabilities: [],
            output: error.message,
        };
    }
    finally {
        // Clean up
        fs_1.default.unlinkSync(filePath);
    }
}
