#!/usr/bin/env node

const { spawn, exec } = require('child_process');
const util = require('util');
const execAsync = util.promisify(exec);

console.log('🚀 Installing Port Open Monitor...');

async function checkPython() {
  try {
    const { stdout } = await execAsync('python3 --version');
    console.log('✅ Python 3 found:', stdout.trim());
    return true;
  } catch (error) {
    console.log('❌ Python 3 not found');
    return false;
  }
}

async function checkPip() {
  try {
    await execAsync('pip3 --version');
    console.log('✅ pip3 found');
    return true;
  } catch (error) {
    console.log('❌ pip3 not found');
    return false;
  }
}

async function installPythonDependencies() {
  console.log('📦 Installing Python dependencies...');
  
  const dependencies = ['psutil', 'rich'];
  
  for (const dep of dependencies) {
    try {
      console.log(`Installing ${dep}...`);
      await execAsync(`pip3 install ${dep}`);
      console.log(`✅ ${dep} installed successfully`);
    } catch (error) {
      console.log(`❌ Failed to install ${dep}:`, error.message);
      console.log(`Please install manually: pip3 install ${dep}`);
    }
  }
}

async function main() {
  const hasPython = await checkPython();
  const hasPip = await checkPip();
  
  if (!hasPython) {
    console.log(`
❌ Python 3 is required but not found.
Please install Python 3:
- Ubuntu/Debian: sudo apt install python3
- macOS: brew install python3
- Windows: Download from https://www.python.org/downloads/
`);
    process.exit(1);
  }
  
  if (!hasPip) {
    console.log(`
❌ pip3 is required but not found.
Please install pip:
- Ubuntu/Debian: sudo apt install python3-pip
- macOS: pip is included with Python from Homebrew
`);
    process.exit(1);
  }
  
  await installPythonDependencies();
  
  console.log(`
✅ Port Open Monitor installed successfully!

Usage:
  port-monitor              # Enhanced port monitoring
  port-monitor -i           # Interactive mode
  port-monitor -m           # Auto-monitoring mode
  port-monitor --help       # Show help

Happy monitoring! 🎯
`);
}

main().catch(console.error);