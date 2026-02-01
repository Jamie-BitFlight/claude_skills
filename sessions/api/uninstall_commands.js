#!/usr/bin/env node

// ==== IMPORTS ===== //

// ===== STDLIB ===== //
const fs = require('node:fs');
const path = require('node:path');
const readline = require('node:readline');
//--//

// ===== LOCAL ===== //
//--//

//-#

// ==== GLOBALS ===== //

// Colors for terminal output
const Colors = {
  RESET: '\x1b[0m',
  RED: '\x1b[31m',
  GREEN: '\x1b[32m',
  YELLOW: '\x1b[33m',
  CYAN: '\x1b[36m',
  BOLD: '\x1b[1m',
};

//-#

// ==== FUNCTIONS ===== //

function color(text, colorCode) {
  return `${colorCode}${text}${Colors.RESET}`;
}

function getProjectRoot() {
  if (process.env.CLAUDE_PROJECT_DIR) {
    return process.env.CLAUDE_PROJECT_DIR;
  }
  return process.cwd();
}

function createBackup(projectRoot) {
  const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace(/T/, '-').split('.')[0];
  const backupDir = path.join(projectRoot, '.claude', `.backup-uninstall-${timestamp}`);

  console.log(
    color(`\n💾 Creating backup at ${path.relative(projectRoot, backupDir)}/...`, Colors.CYAN),
  );

  fs.mkdirSync(backupDir, { recursive: true });

  // Backup all task files
  const tasksSrc = path.join(projectRoot, 'sessions', 'tasks');
  let taskCount = 0;
  if (fs.existsSync(tasksSrc)) {
    const tasksDest = path.join(backupDir, 'tasks');
    copyDirectory(tasksSrc, tasksDest);

    taskCount = countFiles(tasksSrc, '.md');
    const backedUpCount = countFiles(tasksDest, '.md');

    if (taskCount !== backedUpCount) {
      console.log(
        color(
          `   ✗ Backup verification failed: ${backedUpCount}/${taskCount} files backed up`,
          Colors.RED,
        ),
      );
      throw new Error('Backup verification failed - aborting to prevent data loss');
    }

    console.log(color(`   ✓ Backed up ${taskCount} task files`, Colors.GREEN));
  }

  // Backup all agents
  const agentsSrc = path.join(projectRoot, '.claude', 'agents');
  let agentCount = 0;
  if (fs.existsSync(agentsSrc)) {
    const agentsDest = path.join(backupDir, 'agents');
    copyDirectory(agentsSrc, agentsDest);

    agentCount = fs.readdirSync(agentsSrc).filter((f) => f.endsWith('.md')).length;
    const backedUpAgents = fs.readdirSync(agentsDest).filter((f) => f.endsWith('.md')).length;

    if (agentCount !== backedUpAgents) {
      console.log(
        color(
          `   ✗ Backup verification failed: ${backedUpAgents}/${agentCount} agents backed up`,
          Colors.RED,
        ),
      );
      throw new Error('Backup verification failed - aborting to prevent data loss');
    }

    console.log(color(`   ✓ Backed up ${agentCount} agent files`, Colors.GREEN));
  }

  // Backup hook scripts
  const hooksSrc = path.join(projectRoot, 'sessions', 'hooks');
  let hookCount = 0;
  if (fs.existsSync(hooksSrc)) {
    const hooksDest = path.join(backupDir, 'hooks');
    copyDirectory(hooksSrc, hooksDest);

    hookCount = fs
      .readdirSync(hooksSrc)
      .filter((f) => f.endsWith('.py') || f.endsWith('.js')).length;
    const backedUpHooks = fs
      .readdirSync(hooksDest)
      .filter((f) => f.endsWith('.py') || f.endsWith('.js')).length;

    if (hookCount !== backedUpHooks) {
      console.log(
        color(
          `   ✗ Backup verification failed: ${backedUpHooks}/${hookCount} hooks backed up`,
          Colors.RED,
        ),
      );
      throw new Error('Backup verification failed - aborting to prevent data loss');
    }

    console.log(color(`   ✓ Backed up ${hookCount} hook scripts`, Colors.GREEN));
  }

  // Backup config file
  const configSrc = path.join(projectRoot, 'sessions', 'sessions-config.json');
  if (fs.existsSync(configSrc)) {
    const configDest = path.join(backupDir, 'sessions-config.json');
    fs.copyFileSync(configSrc, configDest);
    console.log(color('   ✓ Backed up sessions-config.json', Colors.GREEN));
  }

  return backupDir;
}

function countFiles(dir, extension) {
  let count = 0;

  function traverse(currentPath) {
    const items = fs.readdirSync(currentPath);
    for (const item of items) {
      const fullPath = path.join(currentPath, item);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        traverse(fullPath);
      } else if (fullPath.endsWith(extension)) {
        count++;
      }
    }
  }

  traverse(dir);
  return count;
}

function copyDirectory(src, dest) {
  if (!fs.existsSync(src)) {
    return;
  }

  fs.mkdirSync(dest, { recursive: true });

  const items = fs.readdirSync(src);
  for (const item of items) {
    const srcPath = path.join(src, item);
    const destPath = path.join(dest, item);
    const stat = fs.statSync(srcPath);

    if (stat.isDirectory()) {
      copyDirectory(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function removeClaudeMdReference(projectRoot) {
  const claudePath = path.join(projectRoot, 'CLAUDE.md');
  const reference = '@sessions/CLAUDE.sessions.md';

  if (!fs.existsSync(claudePath)) {
    return;
  }

  try {
    const content = fs.readFileSync(claudePath, 'utf-8');

    if (!content.includes(reference)) {
      return;
    }

    // Remove the reference line and surrounding blank lines
    const lines = content.split('\n');
    const newLines = [];
    let i = 0;
    while (i < lines.length) {
      if (lines[i].includes(reference)) {
        // Skip the reference line
        i++;
        // Skip trailing blank line if present
        if (i < lines.length && lines[i].trim() === '') {
          i++;
        }
      } else {
        newLines.push(lines[i]);
        i++;
      }
    }

    fs.writeFileSync(claudePath, newLines.join('\n'), 'utf-8');
    console.log(color('   ✓ Removed reference from CLAUDE.md', Colors.GREEN));
  } catch (e) {
    console.log(color(`   ⚠️  Could not update CLAUDE.md: ${e.message}`, Colors.YELLOW));
  }
}

function removeSessionsHooks(projectRoot) {
  const settingsPath = path.join(projectRoot, '.claude', 'settings.json');

  if (!fs.existsSync(settingsPath)) {
    return;
  }

  try {
    const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf-8'));

    if (!settings.hooks) {
      return;
    }

    // Sessions hook patterns to remove
    const sessionsPatterns = ['sessions/hooks/', 'sessions\\hooks\\'];

    // Filter out sessions hooks
    let modified = false;
    for (const hookType of Object.keys(settings.hooks)) {
      const originalCount = settings.hooks[hookType].length;

      // Filter hook configurations
      const filteredHooks = [];
      for (const hookConfig of settings.hooks[hookType]) {
        if (hookConfig.hooks) {
          // Filter individual hooks within the config
          const filteredInner = [];
          for (const hook of hookConfig.hooks) {
            if (hook.command) {
              // Check if this is a sessions hook
              const isSessions = sessionsPatterns.some((pattern) => hook.command.includes(pattern));
              if (!isSessions) {
                filteredInner.push(hook);
              }
            } else {
              filteredInner.push(hook);
            }
          }

          // Only keep config if it has remaining hooks
          if (filteredInner.length > 0) {
            hookConfig.hooks = filteredInner;
            filteredHooks.push(hookConfig);
          }
        } else {
          filteredHooks.push(hookConfig);
        }
      }

      settings.hooks[hookType] = filteredHooks;

      if (filteredHooks.length !== originalCount) {
        modified = true;
      }
    }

    // Remove statusline if it points to sessions
    if (
      settings.statusLine &&
      typeof settings.statusLine === 'string' &&
      settings.statusLine.includes('sessions/statusline')
    ) {
      delete settings.statusLine;
      modified = true;
    }

    if (modified) {
      fs.writeFileSync(settingsPath, JSON.stringify(settings, null, 2), 'utf-8');
      console.log(color('   ✓ Removed sessions hooks from settings.json', Colors.GREEN));
    }
  } catch (e) {
    console.log(color(`   ⚠️  Could not update settings.json: ${e.message}`, Colors.YELLOW));
  }
}

function removeSessionsDirectory(projectRoot) {
  const sessionsDir = path.join(projectRoot, 'sessions');

  if (!fs.existsSync(sessionsDir)) {
    return;
  }

  try {
    fs.rmSync(sessionsDir, { recursive: true, force: true });
    console.log(color('   ✓ Removed sessions/ directory', Colors.GREEN));
  } catch (e) {
    console.log(color(`   ✗ Could not remove sessions/: ${e.message}`, Colors.RED));
    throw e;
  }
}

function removeSessionsCommand(projectRoot) {
  const commandPath = path.join(projectRoot, '.claude', 'commands', 'sessions.md');

  if (!fs.existsSync(commandPath)) {
    return;
  }

  try {
    fs.unlinkSync(commandPath);
    console.log(color('   ✓ Removed /sessions slash command', Colors.GREEN));
  } catch (e) {
    console.log(color(`   ⚠️  Could not remove sessions command: ${e.message}`, Colors.YELLOW));
  }
}

async function promptUser(question) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer);
    });
  });
}

async function handleUninstallCommand(args, _jsonOutput = false, _fromSlash = false) {
  if (args.length > 0 && args[0] === 'help') {
    const helpText = `
# Sessions Uninstaller

Safely removes cc-sessions framework from your project while preserving your work.

## Usage

    /sessions uninstall           # Run interactive uninstaller
    /sessions uninstall --dry-run # Preview what would be removed

## What Gets Removed

- sessions/ directory (after backup)
- Sessions hooks from .claude/settings.json
- Sessions statusline from .claude/settings.json (if configured)
- @sessions/CLAUDE.sessions.md reference from CLAUDE.md
- /sessions slash command (.claude/commands/sessions.md)

## What Gets Preserved

Your tasks and agent customizations are backed up to:
    .claude/.backup-uninstall-YYYYMMDD-HHMMSS/

After uninstall completes, run:
    pip uninstall cc-sessions
    OR
    npm uninstall -g cc-sessions
`;
    return helpText.trim();
  }

  const dryRun = args.includes('--dry-run');
  const projectRoot = getProjectRoot();

  console.log(
    color('\n╔════════════════════════════════════════════════════════════════╗', Colors.CYAN),
  );
  console.log(
    color('║           CC-SESSIONS UNINSTALLER                             ║', Colors.CYAN),
  );
  console.log(
    color('╚════════════════════════════════════════════════════════════════╝\n', Colors.CYAN),
  );

  if (dryRun) {
    console.log(color('🔍 DRY RUN MODE - No changes will be made\n', Colors.YELLOW));
  }

  // Check what exists
  const sessionsDir = path.join(projectRoot, 'sessions');
  if (!fs.existsSync(sessionsDir)) {
    console.log(color('ℹ️  No sessions/ directory found. Nothing to uninstall.', Colors.CYAN));
    return '';
  }

  console.log(color('📋 The following will be removed:', Colors.CYAN));
  console.log('   • sessions/ directory (tasks and agents will be backed up)');
  console.log('   • Sessions hooks from .claude/settings.json');
  console.log('   • Sessions statusline from .claude/settings.json (if configured)');
  console.log('   • @sessions/CLAUDE.sessions.md reference from CLAUDE.md');
  console.log('   • /sessions slash command\n');

  if (dryRun) {
    console.log(color('✓ Dry run complete. Run without --dry-run to proceed.', Colors.GREEN));
    return '';
  }

  // Confirm
  console.log(
    color('⚠️  This will remove the cc-sessions framework from this project.', Colors.YELLOW),
  );
  const response = await promptUser(color('Continue? (yes/no): ', Colors.BOLD));

  if (!['yes', 'y'].includes(response.toLowerCase())) {
    console.log(color('\n❌ Uninstall cancelled.', Colors.YELLOW));
    return '';
  }

  try {
    console.log();

    // Create backup
    const backupDir = createBackup(projectRoot);

    // Remove components
    console.log(color('\n🗑️  Removing cc-sessions components...', Colors.CYAN));
    removeClaudeMdReference(projectRoot);
    removeSessionsHooks(projectRoot);
    removeSessionsCommand(projectRoot);
    removeSessionsDirectory(projectRoot);

    // Success message
    console.log(color('\n✅ cc-sessions uninstalled successfully!\n', Colors.GREEN));
    console.log(color('📁 Your work has been backed up to:', Colors.CYAN));
    console.log(color(`   ${path.relative(projectRoot, backupDir)}/`, Colors.BOLD));
    console.log(color('   (includes tasks, agents, hooks, and configuration)\n', Colors.CYAN));
    console.log(color('📦 To complete uninstall, run:', Colors.CYAN));
    console.log(color('   pip uninstall cc-sessions', Colors.BOLD));
    console.log(color('   OR', Colors.CYAN));
    console.log(color('   npm uninstall -g cc-sessions\n', Colors.BOLD));

    return '';
  } catch (e) {
    console.log(color(`\n❌ Uninstall failed: ${e.message}`, Colors.RED));
    if (typeof backupDir !== 'undefined') {
      console.log(
        color(
          `\n📁 Your backup is safe at: ${path.relative(projectRoot, backupDir)}/`,
          Colors.YELLOW,
        ),
      );
    }
    throw e;
  }
}

//-#

// ==== EXPORTS ===== //
module.exports = { handleUninstallCommand };
