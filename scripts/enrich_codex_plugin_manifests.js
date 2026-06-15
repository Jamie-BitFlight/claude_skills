#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const pluginsDir = path.join(root, "plugins");

function titleCaseFromKebab(name) {
  return name
    .split("-")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function detectCapabilities(pluginDir) {
  const capabilities = ["Interactive"];
  if (fs.existsSync(path.join(pluginDir, "skills"))) capabilities.push("Read");
  if (
    fs.existsSync(path.join(pluginDir, "commands")) ||
    fs.existsSync(path.join(pluginDir, "hooks")) ||
    fs.existsSync(path.join(pluginDir, "hooks.json")) ||
    fs.existsSync(path.join(pluginDir, ".mcp.json")) ||
    fs.existsSync(path.join(pluginDir, "mcp"))
  ) {
    capabilities.push("Write");
  }
  return [...new Set(capabilities)];
}

for (const entry of fs.readdirSync(pluginsDir, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  const pluginDir = path.join(pluginsDir, entry.name);
  const manifestPath = path.join(pluginDir, ".codex-plugin", "plugin.json");
  if (!fs.existsSync(manifestPath)) continue;

  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
  if (manifest.interface) continue;

  const displayName = titleCaseFromKebab(manifest.name);
  const description = manifest.description || `${displayName} plugin`;

  manifest.interface = {
    displayName,
    shortDescription: description,
    longDescription: description,
    developerName:
      manifest.author && typeof manifest.author === "object" && manifest.author.name
        ? manifest.author.name
        : "Unknown",
    category: "Developer Tools",
    capabilities: detectCapabilities(pluginDir),
  };

  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
}
