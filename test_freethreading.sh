#!/bin/bash
# Python 3.14 Free-Threading 테스트 스크립트

echo "======================================================================"
echo "Python 3.14 Free-Threading Port Monitor 테스트"
echo "======================================================================"
echo ""

# 1. Python 버전 확인
echo "1. Python 환경 확인"
echo "----------------------------------------------------------------------"
python3 --version
python3 -c "import sys, sysconfig; print(f'GIL Disabled: {sysconfig.get_config_var(\"Py_GIL_DISABLED\")}')"
echo ""

# 2. 필수 패키지 확인
echo "2. 필수 패키지 확인"
echo "----------------------------------------------------------------------"
python3 -c "import psutil; print('psutil:', psutil.__version__)"
python3 -c "import rich; print('rich:', rich.__version__)"
echo ""

# 3. 기본 실행 테스트
echo "3. 기본 실행 테스트"
echo "----------------------------------------------------------------------"
python3 port_monitor_freethreading.py
echo ""

# 4. 성능 벤치마크 (옵션)
read -p "성능 벤치마크를 실행하시겠습니까? (y/n): " run_benchmark
if [ "$run_benchmark" = "y" ] || [ "$run_benchmark" = "Y" ]; then
    echo ""
    echo "4. 성능 벤치마크"
    echo "----------------------------------------------------------------------"
    python3 port_monitor_freethreading.py --benchmark
fi

echo ""
echo "======================================================================"
echo "테스트 완료!"
echo "======================================================================"
