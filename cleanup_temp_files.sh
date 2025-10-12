#!/bin/bash

# Port Open Monitor - Temporary Files Cleanup Script
# This script moves temporary and test files to the organized TEMP directory

# 사용자 환경에 맞게 경로 수정 필요
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMP_DIR="$HOME/TEMP/port_open_monitor"

echo "=== Port Open Monitor Cleanup Script ==="
echo "Project Directory: $PROJECT_DIR"
echo "TEMP Directory: $TEMP_DIR"
echo

# Function to move files with confirmation
move_files() {
    local pattern="$1"
    local destination="$2"
    local description="$3"
    
    files=$(find "$PROJECT_DIR" -maxdepth 1 -name "$pattern" 2>/dev/null)
    
    if [ -n "$files" ]; then
        echo "Found $description files:"
        echo "$files"
        echo
        read -p "Move these files to $destination? (y/N): " confirm
        
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            mkdir -p "$destination"
            find "$PROJECT_DIR" -maxdepth 1 -name "$pattern" -exec mv {} "$destination/" \;
            echo "✓ Moved $description files to $destination"
        else
            echo "✗ Skipped $description files"
        fi
        echo
    fi
}

# Move different types of temporary files
move_files "*.bak" "$TEMP_DIR/backups" "backup"
move_files "*.old" "$TEMP_DIR/backups" "old backup"
move_files "*.backup" "$TEMP_DIR/backups" "backup"

move_files "*.log" "$TEMP_DIR/logs" "log"
move_files "*log*" "$TEMP_DIR/logs" "log-related"

move_files "*report*.txt" "$TEMP_DIR/reports" "report"
move_files "*report*.html" "$TEMP_DIR/reports" "HTML report"
move_files "*report*.json" "$TEMP_DIR/reports" "JSON report"

move_files "*test*" "$TEMP_DIR/tests" "test"
move_files "*debug*" "$TEMP_DIR/debug" "debug"
move_files "*.tmp" "$TEMP_DIR/debug" "temporary"

# Check for any remaining temporary files
echo "=== Remaining files in project directory ==="
ls -la "$PROJECT_DIR"
echo

echo "=== TEMP directory structure ==="
find "$TEMP_DIR" -type f | sort
echo

echo "Cleanup completed!"