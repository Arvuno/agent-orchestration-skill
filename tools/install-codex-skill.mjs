#!/usr/bin/env node
import { chmodSync, cpSync, existsSync, mkdirSync, renameSync, rmSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const PKG_ROOT = resolve(__dirname, '..');
const SKILL_NAME = 'agent-orchestration-skill';
const SKILL_SRC = join(PKG_ROOT, 'skills', SKILL_NAME);
const quiet = process.argv.includes('--quiet') || process.env.AOC_POSTINSTALL_QUIET === '1';
const strict = process.argv.includes('--strict') || process.env.AOC_POSTINSTALL_STRICT === '1';

function log(message) {
  if (!quiet) console.log(message);
}

function warn(message) {
  if (!quiet) console.warn(message);
}

function isDirectory(path) {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

function homeDir() {
  const home = process.env.HOME || process.env.USERPROFILE || '';
  if (!home) throw new Error('Unable to resolve HOME for Codex skill install.');
  return resolve(home);
}

function backupIfPresent(path, skillsDir) {
  if (!existsSync(path)) return;
  const backupRoot = join(skillsDir, `.aoc-backup-${new Date().toISOString().replace(/[-:TZ.]/g, '').slice(0, 14)}`);
  mkdirSync(backupRoot, { recursive: true });
  renameSync(path, join(backupRoot, path.split(/[\\/]/).pop()));
}

function installCodexSkill() {
  if (!isDirectory(SKILL_SRC)) {
    throw new Error(`Missing bundled skill directory: ${SKILL_SRC}`);
  }
  const codexHome = join(homeDir(), '.codex');
  const skillsDir = join(codexHome, 'skills');
  const dst = join(skillsDir, SKILL_NAME);
  mkdirSync(skillsDir, { recursive: true });

  for (const stale of ['agentic-orchestration-control']) {
    backupIfPresent(join(skillsDir, stale), skillsDir);
  }

  rmSync(dst, { recursive: true, force: true });
  cpSync(SKILL_SRC, dst, { recursive: true, force: true });
  for (const rel of [
    'bin/agentic-orchestration-control',
    'bin/agentic-orchestration-gui',
    'bin/agentic-orchestration-usage',
    'bin/aoc',
    'bin/aoc-gui',
    'bin/aoc-usage',
    'scripts/codex_leaf_exec.sh',
  ]) {
    const p = join(dst, rel);
    if (existsSync(p)) chmodSync(p, 0o755);
  }
  log(`Installed Codex skill: ${dst}`);
  return dst;
}

try {
  installCodexSkill();
} catch (err) {
  const message = `AOC Codex skill global install failed: ${err instanceof Error ? err.message : String(err)}`;
  if (strict) {
    console.error(message);
    process.exit(1);
  }
  warn(`${message}. Run \`aoc install-skill --strict\` after fixing permissions.`);
}
