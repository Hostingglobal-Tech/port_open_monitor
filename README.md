# 🚀 Port Open Monitor

포트 443-9000 범위의 열린 TCP 포트를 모니터링하고 관리하는 도구입니다.
(포트 443은 HTTPS, 기타 일반적으로 사용되는 서비스 포트들을 포함)

## ✨ 주요 기능

- **프로젝트 폴더명 표시**: 각 포트가 어떤 프로젝트에서 사용되는지 명확히 표시
- **즉시 프로세스 종료**: 화면에서 번호 선택으로 바로 kill 가능
- **상세 정보 제공**: PID, 메모리 사용량, 사용자, 전체 경로 표시
- **대화형 모드**: 메뉴 기반 인터페이스로 편리한 관리
- **🆕 Python 3.14 Free-Threading 지원**: GIL 없이 진정한 병렬 처리!

## 📊 화면 예시

```
┏━━━┳━━━━━━┳━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
┃ No┃ Port ┃ PID  ┃ Process         ┃ Project Folder             ┃ Memory┃ User     ┃
┡━━━╇━━━━━━╇━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
│ 1 │ 30XX │ XXXXX│ next-server     │ my_project                 │ 338MB │ user1    │
│ 2 │ 43XX │ XXXXX│ node            │ another_project            │ 1.7GB │ user1    │
│ 3 │ 80XX │ XXXXX│ node            │ my_project                 │ 148MB │ user1    │
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
./pm kill <PORT>

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
python3 port_monitor.py -p <PORT>

# PID로 프로세스 종료
python3 port_monitor.py -k <PID>
```

### 🆕 Python 3.14 Free-Threading 버전

Python 3.14의 free-threading (GIL 비활성화) 기능을 활용한 고성능 버전입니다.

**간편 명령어 (bashrc alias):**
```bash
# ~/.bashrc에 설정된 alias 사용 (python3 = 3.14t)
pmft          # Free-threading 포트 모니터 실행 (60초 자동 갱신)
pmft -t 30    # 30초마다 자동 갱신
pmft-bench    # 성능 벤치마크 (순차 vs 병렬 비교)
```

**직접 실행:**
```bash
# 기본 실행 (60초 자동 갱신 + 카운트다운)
python3 port_monitor_freethreading.py

# 빠른 갱신 (30초 간격)
python3 port_monitor_freethreading.py -t 30

# 성능 벤치마크 (순차 vs 병렬 비교)
python3 port_monitor_freethreading.py --benchmark

# 병렬 처리 강제 사용
python3 port_monitor_freethreading.py --parallel

# 순차 처리 강제 사용 (비교용)
python3 port_monitor_freethreading.py --sequential

# 테스트 스크립트 실행
./test_freethreading.sh
```

**⏱️ 실시간 카운트다운 기능:**
```
[Auto refresh in 59s] Enter number to kill, h:hide, r:refresh, q:quit
```

**키보드 명령어 (실행 중 입력):**
- **숫자 입력**: 해당 번호 프로세스 즉시 종료
- **h**: 프로세스 숨기기 (화면에서 제외)
- **r**: 즉시 갱신 (카운트다운 리셋)
- **q**: 프로그램 종료

**주요 특징:**
- ✅ GIL 자동 감지 및 최적화
- ⚡ ThreadPoolExecutor로 프로세스 정보 병렬 수집
- ⏱️ 실시간 카운트다운 + 자동 갱신
- 🎯 CPU 코어 수에 따른 자동 워커 조정
- 📊 실시간 성능 벤치마크 기능
- 👁️ 프로세스 숨기기 기능

**설치 방법:**
```bash
# Python 3.14 free-threading 빌드 설치
pyenv install 3.14.0t

# 프로젝트에 적용
cd ~/DEVEL/port_open_monitor  # 또는 프로젝트 디렉토리
pyenv local 3.14.0t

# ~/.bashrc에 alias 추가 (이미 설정됨)
# python3가 이미 3.14t로 설정되어 있음
alias pmft="python3 /path/to/port_monitor_freethreading.py"
alias pmft-bench="python3 /path/to/port_monitor_freethreading.py --benchmark"

# bashrc 리로드
source ~/.bashrc
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

- **프로젝트 자동 감지**: DEVEL 디렉토리 하위 폴더명 자동 추출
- **색상 하이라이트**: 프로젝트별 색상으로 구분
- **메모리 모니터링**: 각 프로세스의 메모리 사용량 실시간 표시
- **권한 자동 처리**: sudo 권한 필요시 자동 처리

## 📝 주의사항

- 포트 범위: 443-9000 (기본값, 커스터마이징 가능)
  - 포트 443: HTTPS 표준 포트
  - 포트 80: HTTP (필요시 --start-port 80으로 포함 가능)
- sudo 권한 필요 (자동 처리됨)
- Python 3.x 및 psutil, rich 패키지 필요

## 🚨 프로세스 종료 옵션

- **SIGTERM (15)**: 정상 종료 요청 (기본)
- **SIGKILL (9)**: 강제 종료 (Force kill)

## 📊 사용 팁

- **프로세스 숨기기**: 불필요한 프로세스를 화면에서 숨길 수 있습니다
- **즉시 갱신**: 'r' 키로 카운트다운 없이 즉시 갱신
- **빠른 종료**: 숫자 입력으로 프로세스 즉시 종료
- **자동 갱신**: 기본 60초, -t 옵션으로 조정 가능