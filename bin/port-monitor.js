#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get the directory where this package is installed
const packageDir = path.dirname(__dirname);

// Python scripts paths
const scripts = {
  basic: path.join(packageDir, 'port_monitor.py'),
  enhanced: path.join(packageDir, 'port_monitor_enhanced.py'),
  interactive: path.join(packageDir, 'port_monitor_interactive.py'),
  pm: path.join(packageDir, 'pm')
};

function showHelp() {
  console.log(`
🚀 Port Open Monitor - npm edition

Usage:
  port-monitor [options]        # Run enhanced port monitor
  pm-port [options]             # Same as port-monitor

Options:
  -i, --interactive            # Interactive mode with process selection
  -q, --quick                  # Quick view mode
  -m, --monitor [interval]     # Auto-monitoring mode (default: 60s)
  -t, --time <seconds>         # Set monitoring interval
  -h, --help                   # Show this help

Examples:
  port-monitor                 # Basic enhanced view
  port-monitor -i              # Interactive mode
  port-monitor -m              # Auto-monitor (60s interval)
  port-monitor -m -t 30        # Auto-monitor (30s interval)

Original Python scripts are also available:
  ${scripts.basic}
  ${scripts.enhanced}
  ${scripts.interactive}

Requirements:
  - Python 3.x
  - psutil: pip install psutil
  - rich: pip install rich
`);
}

function checkPythonDependencies() {
  // Check if Python is available
  const python = spawn('python3', ['--version'], { stdio: 'pipe' });
  
  python.on('error', () => {
    console.error('❌ Python 3 is required but not found in PATH');
    console.error('Please install Python 3: https://www.python.org/downloads/');
    process.exit(1);
  });
}

function runPythonScript(scriptPath, args = []) {
  checkPythonDependencies();
  
  if (!fs.existsSync(scriptPath)) {
    console.error(`❌ Script not found: ${scriptPath}`);
    process.exit(1);
  }

  const python = spawn('python3', [scriptPath, ...args], {
    stdio: 'inherit',
    cwd: packageDir
  });

  python.on('error', (err) => {
    console.error('❌ Failed to run Python script:', err.message);
    process.exit(1);
  });

  python.on('close', (code) => {
    process.exit(code);
  });
}

// Parse command line arguments
const args = process.argv.slice(2);

if (args.includes('-h') || args.includes('--help')) {
  showHelp();
  process.exit(0);
}

// Determine which script to run and with what arguments
let scriptPath = scripts.enhanced; // Default to enhanced version
let scriptArgs = [];

if (args.includes('-i') || args.includes('--interactive')) {
  scriptPath = scripts.interactive;
  scriptArgs.push('-i');
}

if (args.includes('-q') || args.includes('--quick')) {
  scriptArgs.push('-q');
}

if (args.includes('-m') || args.includes('--monitor')) {
  scriptArgs.push('-m');
  
  const timeIndex = args.indexOf('-t') !== -1 ? args.indexOf('-t') : args.indexOf('--time');
  if (timeIndex !== -1 && args[timeIndex + 1]) {
    scriptArgs.push('-t', args[timeIndex + 1]);
  }
}

// Run the appropriate Python script
runPythonScript(scriptPath, scriptArgs);