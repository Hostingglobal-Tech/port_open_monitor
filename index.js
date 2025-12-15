#!/usr/bin/env node

/**
 * Port Open Monitor - Main entry point
 * 
 * This is a Node.js wrapper for Python-based port monitoring tools.
 * It provides a convenient npm package interface for the underlying Python scripts.
 */

const { spawn } = require('child_process');
const path = require('path');

const packageDir = __dirname;

/**
 * Run the enhanced port monitor (default behavior)
 * @param {string[]} args - Command line arguments
 */
function runPortMonitor(args = []) {
  const scriptPath = path.join(packageDir, 'port_monitor_enhanced.py');
  
  const python = spawn('python3', [scriptPath, ...args], {
    stdio: 'inherit',
    cwd: packageDir
  });

  python.on('error', (err) => {
    console.error('❌ Failed to run port monitor:', err.message);
    console.error('Make sure Python 3 is installed and available in PATH');
    process.exit(1);
  });

  python.on('close', (code) => {
    process.exit(code);
  });
}

module.exports = {
  runPortMonitor
};

// If called directly, run the port monitor
if (require.main === module) {
  const args = process.argv.slice(2);
  runPortMonitor(args);
}