# 🚀 Port Open Monitor

포트 3000-9000 사이의 열린 TCP 포트를 모니터링하고 관리하는 도구입니다.

## ✨ 주요 기능

- **프로젝트 폴더명 표시**: 각 포트가 어떤 프로젝트에서 사용되는지 명확히 표시
- **즉시 프로세스 종료**: 화면에서 번호 선택으로 바로 kill 가능
- **상세 정보 제공**: PID, 메모리 사용량, 사용자, 전체 경로 표시
- **대화형 모드**: 메뉴 기반 인터페이스로 편리한 관리
- **🆕 Python 3.14 Free-Threading 지원**: GIL 없이 진정한 병렬 처리!

## 📊 현재 포트 사용 예시

```
┏━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
┃ No┃ Port ┃ PID  ┃ Process         ┃ Project Folder             ┃ Memory┃ User     ┃
┡━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
│ 1 │ 4001 │ 35403│ next-server     │ compose_email_system       │ 338MB │ nmsglobal│
│ 2 │ 4300 │ 14367│ node            │ customer_management_system │ 1.7GB │ nmsglobal│
│ 3 │ 8000 │ 87897│ node            │ compose_email_system       │ 148MB │ nmsglobal│
└───┴──────┴──────┴─────────────────┴────────────────────────────┴───────┴──────────┘
```

## 🛠️ 사용 방법

### 빠른 명령 (pm)

```bash
# 현재 포트 상태 확인
./pm

# 대화형 모드 (번호로 선택하여 kill)
./pm i

# 자동 모니터링 모드 (1분 간격)
./pm m

# 자동 모니터링 모드 (30초 간격)
./pm m 30

# 특정 포트 프로세스 종료
./pm kill 4001

# 도움말
./pm help
```

### Python 스크립트 직접 실행

```bash
# 기본 보기
python3 port_monitor_enhanced.py

# 대화형 모드
python3 port_monitor_enhanced.py -i

# 빠른 보기 모드
python3 port_monitor_enhanced.py -q

# 자동 모니터링 모드 (기본 60초)
python3 port_monitor_enhanced.py -m

# 자동 모니터링 모드 (커스텀 간격)
python3 port_monitor_enhanced.py -m -t 30
```

### 원본 스크립트 (port_monitor.py)

```bash
# 포트 현황 확인
python3 port_monitor.py

# 대화형 모드
python3 port_monitor.py -i

# 특정 포트 프로세스 종료
python3 port_monitor.py -p 4001

# PID로 프로세스 종료
python3 port_monitor.py -k 35403
```

### 🆕 Python 3.14 Free-Threading 버전

Python 3.14의 free-threading (GIL 비활성화) 기능을 활용한 고성능 버전입니다.

```bash
# 기본 실행 (자동으로 최적 방식 선택)
python3.14t port_monitor_freethreading.py

# 성능 벤치마크 (순차 vs 병렬 비교)
python3.14t port_monitor_freethreading.py --benchmark

# 병렬 처리 강제 사용
python3.14t port_monitor_freethreading.py --parallel

# 순차 처리 강제 사용 (비교용)
python3.14t port_monitor_freethreading.py --sequential

# 테스트 스크립트 실행
./test_freethreading.sh
```

**주요 특징:**
- ✅ GIL 자동 감지 및 최적화
- ⚡ ThreadPoolExecutor로 프로세스 정보 병렬 수집
- 📊 실시간 성능 벤치마크 기능
- 🎯 CPU 코어 수에 따른 자동 워커 조정

**설치 방법:**
```bash
# Python 3.14 free-threading 빌드 설치
pyenv install 3.14.0t

# 프로젝트에 적용
cd ~/DEVEL/port_open_monitor  # 또는 프로젝트 디렉토리
pyenv local 3.14.0t
```

**상세 가이드:** [FREETHREADING_GUIDE.md](./FREETHREADING_GUIDE.md)

## 📁 파일 구조

```
port_open_monitor/
├── pm                              # 간편 실행 스크립트
├── port_monitor.py                 # 기본 모니터링 스크립트
├── port_monitor_enhanced.py        # 향상된 버전 (폴더명 표시)
├── port_monitor_interactive.py     # 대화형 자동 갱신 버전
├── port_monitor_freethreading.py   # 🆕 Python 3.14 Free-Threading 버전
├── FREETHREADING_GUIDE.md          # Free-Threading 상세 가이드
├── test_freethreading.sh           # Free-Threading 테스트 스크립트
└── README.md                       # 이 파일
```

## 🔍 모드별 기능

### 📊 자동 모니터링 모드 (New!)
- **기본 간격**: 60초마다 자동 갱신
- **커스텀 간격**: 원하는 초 단위로 설정 가능
- **실시간 업데이트**: 포트 변경 사항 자동 감지
- **Ctrl+C로 중지**: 언제든지 모니터링 중단 가능

### 🎯 대화형 모드
1. **번호로 프로세스 관리**: 1-N 번호 입력으로 프로세스 선택
2. **Graceful/Force Kill**: SIGTERM 또는 SIGKILL 선택 가능
3. **일괄 종료**: 모든 프로세스 한번에 종료
4. **리포트 내보내기**: 텍스트 파일로 저장
5. **자동 새로고침**: 프로세스 종료 후 자동 갱신

## 💡 특징

- **프로젝트 자동 감지**: /home/nmsglobal/DEVEL/ 하위 폴더명 자동 추출
- **색상 하이라이트**: 프로젝트별 색상으로 구분
- **메모리 모니터링**: 각 프로세스의 메모리 사용량 실시간 표시
- **권한 자동 처리**: sudo 권한 필요시 자동 처리

## 📝 주의사항

- 포트 범위: 3000-9000
- sudo 권한 필요 (자동 처리됨)
- Python 3.x 및 psutil, rich 패키지 필요

## 🚨 프로세스 종료 옵션

- **SIGTERM (15)**: 정상 종료 요청 (기본)
- **SIGKILL (9)**: 강제 종료 (Force kill)

## 📊 알려진 프로젝트 매핑

- Port 4001: newsletter_email_system
- Port 4300: system-scan-report-remix
- Port 4400: customer_management_system (frontend)
- Port 8000: compose_email_system (backend)
- Port 8888: Jupyter Lab