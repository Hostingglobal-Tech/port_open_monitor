#!/bin/bash
# Port Monitor 간편 실행 스크립트

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 인자가 없으면 기본 표시
if [ $# -eq 0 ]; then
    python3 "$SCRIPT_DIR/port_monitor_enhanced.py"
    exit 0
fi

# 첫 번째 인자 처리
case "$1" in
    i|interactive|-i|--interactive)
        python3 "$SCRIPT_DIR/port_monitor_enhanced.py" --interactive
        ;;
    m|monitor|-m|--monitor)
        # 두 번째 인자가 있으면 간격으로 사용
        if [ -n "$2" ] && [[ "$2" =~ ^[0-9]+$ ]]; then
            python3 "$SCRIPT_DIR/port_monitor_interactive.py" --interval "$2"
        else
            python3 "$SCRIPT_DIR/port_monitor_interactive.py"
        fi
        ;;
    k|kill)
        # 두 번째 인자가 있으면 포트 번호로 처리
        if [ -n "$2" ]; then
            # 먼저 포트 정보 표시
            python3 "$SCRIPT_DIR/port_monitor_enhanced.py"
            echo ""
            # kill 명령 실행
            PORT=$2
            PID=$(echo 'ak@5406454' | sudo -S ss -tulnp "( sport = :$PORT )" | grep -oP 'pid=\K\d+' | head -1)
            if [ -n "$PID" ]; then
                echo "Killing process on port $PORT (PID: $PID)..."
                echo 'ak@5406454' | sudo -S kill -15 $PID
                echo "✓ Process killed"
            else
                echo "✗ No process found on port $PORT"
            fi
        else
            echo "Usage: pm kill <port>"
        fi
        ;;
    h|help|--help)
        echo "Port Monitor - Quick Commands"
        echo "=============================="
        echo "Usage: pm [command]"
        echo ""
        echo "Commands:"
        echo "  (no args)      - Show current port usage"
        echo "  i, interactive - Interactive mode"
        echo "  m, monitor [sec] - Interactive monitor with kill (default: 60 seconds)"
        echo "  k, kill <port> - Kill process on specified port"
        echo "  h, help        - Show this help"
        echo ""
        echo "Examples:"
        echo "  pm            # Show ports"
        echo "  pm i          # Interactive mode"
        echo "  pm m          # Monitor every 60 seconds (with kill)"
        echo "  pm m 30       # Monitor every 30 seconds (with kill)"
        echo "  pm kill 4001  # Kill process on port 4001"
        ;;
    *)
        python3 "$SCRIPT_DIR/port_monitor_enhanced.py" "$@"
        ;;
esac