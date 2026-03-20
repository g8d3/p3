#!/usr/bin/env node
/**
 * test-login-sites.js
 *
 * Tests google-sso-login.js against multiple AI services and writes results to CSV.
 * Logs out between tests to ensure clean state.
 */

const { execSync } = require("child_process");
const fs = require("fs");

const SERVICES = [
  { name: "ElevenLabs", signInUrl: "https://elevenlabs.io/app/sign-in", pattern: "elevenlabs.io/app" },
  { name: "Groq", signInUrl: "https://console.groq.com/login", pattern: "console.groq.com" },
  { name: "Mistral", signInUrl: "https://console.mistral.ai/login", pattern: "console.mistral.ai" },
  { name: "Cohere", signInUrl: "https://dashboard.cohere.com/welcome/login", pattern: "dashboard.cohere.com" },
  { name: "HuggingFace", signInUrl: "https://huggingface.co/login", pattern: "huggingface.co" },
  { name: "OpenRouter", signInUrl: "https://openrouter.ai/login", pattern: "openrouter.ai" },
  { name: "AI21", signInUrl: "https://studio.ai21.com/v2/login", pattern: "studio.ai21.com" },
  { name: "DeepSeek", signInUrl: "https://platform.deepseek.com/login", pattern: "platform.deepseek.com" },
  { name: "GoogleAIStudio", signInUrl: "https://aistudio.google.com/", pattern: "aistudio.google.com" },
  { name: "Anthropic", signInUrl: "https://console.anthropic.com/login", pattern: "console.anthropic.com" },
];

const CSV_PATH = __dirname + "/login-test-results.csv";
const TIMEOUT = "90000";

function run(cmd) {
  try {
    return execSync(cmd, { timeout: 120000, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] });
  } catch (e) {
    return e.stdout || e.stderr || e.message;
  }
}

async function main() {
  const results = [];

  // CSV header
  const header = "service,sign_in_url,post_login_pattern,login_result,final_url,has_google_sso,error,timestamp";
  console.log(header);
  results.push(header);

  for (const svc of SERVICES) {
    console.log(`\n${"=".repeat(60)}`);
    console.log(`Testing: ${svc.name}`);
    console.log(`${"=".repeat(60)}`);

    // Logout first
    console.log("  Logging out...");
    run(`node ${__dirname}/logout-app.js ${new URL(svc.signInUrl).origin}`);

    // Login
    console.log("  Logging in...");
    const output = run(
      `node ${__dirname}/google-sso-login.js --timeout ${TIMEOUT} "${svc.signInUrl}" "${svc.pattern}"`
    );

    // Parse result
    const loginSuccess = output.includes("LOGIN SUCCESSFUL");
    const alreadyLoggedIn = output.includes("ALREADY LOGGED IN");
    const btnNotFound = output.includes("Google sign-in button not found");
    const timeout = output.includes("timed out");

    let result, error;
    if (loginSuccess || alreadyLoggedIn) {
      result = alreadyLoggedIn ? "already_logged_in" : "success";
      error = "";
    } else if (btnNotFound) {
      result = "no_google_sso";
      error = "No Google SSO button found";
    } else if (timeout) {
      result = "timeout";
      error = "Flow timed out";
    } else {
      result = "failed";
      error = output.split("\n").slice(-5).join(" | ").replace(/"/g, "'");
    }

    // Extract final URL
    const urlMatch = output.match(/(?:Signed in at:|Got:)\s+(https?:\/\/\S+)/);
    const finalUrl = urlMatch ? urlMatch[1] : "";

    const hasGoogleSso = !btnNotFound;
    const timestamp = new Date().toISOString();

    const row = `"${svc.name}","${svc.signInUrl}","${svc.pattern}","${result}","${finalUrl}","${hasGoogleSso}","${error}","${timestamp}"`;
    console.log(`\n  Result: ${result}`);
    results.push(row);
  }

  // Write CSV
  fs.writeFileSync(CSV_PATH, results.join("\n") + "\n");
  console.log(`\n\n✅ Results written to ${CSV_PATH}`);
}

main().catch((err) => {
  console.error("Fatal:", err.message);
  process.exit(1);
});
