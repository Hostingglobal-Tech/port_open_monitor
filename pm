#!/bin/bash
# Port Monitor 간편 실행 스크립트

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 포트 범위 옵션 처리
START_PORT=""
END_PORT=""

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case "$1" in
        --start-port)
            START_PORT="$2"
            shift 2
            ;;
        --end-port)
            END_PORT="$2"
            shift 2
            ;;
        *)
            break
            ;;
    esac
done

# 포트 범위 옵션 문자열 생성
PORT_OPTS=""
if [ -n "$START_PORT" ]; then
    PORT_OPTS="$PORT_OPTS --start-port $START_PORT"
fi
if [ -n "$END_PORT" ]; then
    PORT_OPTS="$PORT_OPTS --end-port $END_PORT"
fi

# 인자가 없으면 기본 표시
if [ $# -eq 0 ]; then
    python3 "$SCRIPT_DIR/port_monitor_enhanced.py" $PORT_OPTS
    exit 0
fi

# 첫 번째 인자 처리
case "$1" in
    i|interactive|-i|--interactive)
        python3 "$SCRIPT_DIR/port_monitor_enhanced.py" --interactive $PORT_OPTS
        ;;
    m|monitor|-m|--monitor)
        # 두 번째 인자가 있으면 간격으로 사용
        if [ -n "$2" ] && [[ "$2" =~ ^[0-9]+$ ]]; then
            python3 "$SCRIPT_DIR/port_monitor_interactive.py" --interval "$2" $PORT_OPTS
        else
            python3 "$SCRIPT_DIR/port_monitor_interactive.py" $PORT_OPTS
        fi
        ;;
    k|kill)
        # 두 번째 인자가 있으면 포트 번호로 처리
        if [ -n "$2" ]; then
            # 먼저 포트 정보 표시
            python3 "$SCRIPT_DIR/port_monitor_enhanced.py" $PORT_OPTS
            echo ""
            # kill 명령 실행
            PORT=$2
            # 환경변수에서 sudo 비밀번호 가져오기
            if [ -z "$SUDO_PASSWORD" ]; then
                echo "Error: SUDO_PASSWORD environment variable not set"
                echo "Please set it in ~/.bashrc: export SUDO_PASSWORD=\"your_password\""
                exit 1
            fi
            PID=$(echo "$SUDO_PASSWORD" | sudo -S ss -tulnp "( sport = :$PORT )" | grep -oP 'pid=\K\d+' | head -1)
            if [ -n "$PID" ]; then
                echo "Killing process on port $PORT (PID: $PID)..."
                echo "$SUDO_PASSWORD" | sudo -S kill -15 $PID
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
        echo "  --start-port N - Set start port for monitoring range"
        echo "  --end-port N   - Set end port for monitoring range"
        echo ""
        echo "Examples:"
        echo "  pm            # Show ports"
        echo "  pm i          # Interactive mode"
        echo "  pm m          # Monitor every 60 seconds (with kill)"
        echo "  pm m 30       # Monitor every 30 seconds (with kill)"
        echo "  pm kill 4001  # Kill process on port 4001"
        echo "  pm --start-port 8000 --end-port 8100  # Monitor ports 8000-8100"
        echo "  pm --start-port 5000 --end-port 6000 m  # Monitor ports 5000-6000 interactively"
        ;;
    *)
        python3 "$SCRIPT_DIR/port_monitor_enhanced.py" "$@" $PORT_OPTS
        ;;
esac