#!/usr/bin/env python3
"""
Python 3.14 Free-Threading 지원 포트 모니터링 시스템
GIL이 비활성화된 경우 진정한 병렬 처리로 성능 향상
"""

import subprocess
import re
import os
import sys
import psutil
import signal
import sysconfig
import time
import select
import termios
import tty
from typing import List, Dict, Optional
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint

console = Console()


class FreeThreadingPortMonitor:
    # 시스템 서비스 매핑 (프로세스명 -> 친숙한 이름)
    SYSTEM_SERVICES = {
        "nginx": "Nginx (웹서버)",
        "apache2": "Apache (웹서버)",
        "httpd": "Apache (웹서버)",
        "redis-server": "Redis (캐시)",
        "postgres": "PostgreSQL (DB)",
        "mysqld": "MySQL (DB)",
        "mongod": "MongoDB (DB)",
        "docker-proxy": "Docker Proxy",
        "sshd": "SSH Server",
        "code-server": "VS Code Server",
        "ttyd": "TTYD (웹터미널)",
        "grafana": "Grafana",
        "prometheus": "Prometheus",
        "ntopng": "ntopng (네트워크)",
    }

    def __init__(self, start_port=443, end_port=9000):
        self.port_range = (start_port, end_port)
        # sudo 비밀번호는 환경변수 SUDO_PASSWORD에서 가져오거나 직접 입력
        self.sudo_password = os.getenv("SUDO_PASSWORD", "")
        self.gil_disabled = self.check_gil_status()
        self.max_workers = os.cpu_count() or 4
        # 프로세스 정보 캐시 (PID -> 정보)
        self._process_cache = {}

    def check_gil_status(self) -> bool:
        """Python 3.14 Free-threading 지원 여부 확인"""
        gil_disabled = sysconfig.get_config_var("Py_GIL_DISABLED") == 1
        return gil_disabled

    def display_python_info(self):
        """Python 및 Free-threading 정보 표시"""
        info_lines = []
        info_lines.append(f"Python 버전: {sys.version.split()[0]}")
        info_lines.append(f"CPU 코어 수: {os.cpu_count()}")

        if self.gil_disabled:
            info_lines.append("✅ Free-threading 모드 (GIL 비활성화)")
            info_lines.append(f"   → 진정한 멀티코어 병렬 처리 가능!")
            info_lines.append(f"   → 최대 워커: {self.max_workers}개")
        else:
            info_lines.append("⚠️  일반 모드 (GIL 활성화)")
            info_lines.append("   → 스레드가 순차적으로 실행됨")

        return "\n".join(info_lines)

    # 너무 일반적인 앱 이름 (상위 폴더 포함 필요)
    GENERIC_APP_NAMES = {
        "frontend",
        "backend",
        "api",
        "src",
        "app",
        "server",
        "client",
        "web",
        "service",
    }

    def get_friendly_app_name(
        self,
        process_name: str,
        project_folder: str,
        app_name: Optional[str],
        description: Optional[str] = None,
    ) -> str:
        """친숙한 앱 이름 생성 (시스템 서비스, 설명, 폴더명 처리)"""
        # 1. 시스템 서비스 체크
        if process_name in self.SYSTEM_SERVICES:
            return self.SYSTEM_SERVICES[process_name]

        # 2. 프로젝트 설명이 있으면 우선 사용 (가장 명확한 정보)
        if description:
            return description

        folder_parts = (
            project_folder.split("/") if project_folder and project_folder != "Unknown" else []
        )

        # 3. package.json의 name이 있으면 사용 (단, 일반적인 이름이면 상위 폴더 추가)
        if app_name and app_name != "Unknown":
            # 일반적인 이름이고 상위 폴더가 있으면 "상위/앱명" 형태
            if app_name.lower() in self.GENERIC_APP_NAMES and len(folder_parts) >= 2:
                parent_folder = folder_parts[-2]
                return f"{parent_folder}/{app_name}"
            return app_name

        # 4. 프로젝트 폴더가 Unknown이면 프로세스명 반환
        if project_folder == "Unknown" or not project_folder:
            return process_name if process_name != "Unknown" else "Unknown"

        # 5. 폴더 경로에서 친숙한 이름 생성 (동적 감지)
        last_folder = folder_parts[-1] if folder_parts else ""

        # 폴더가 2개 이상이면 항상 "상위/마지막" 형태로 표시 (더 명확한 식별)
        # 예: "compose_email_system/frontend" -> "compose_email_system/frontend"
        # 예: "AI_EMAIL_MANAGER/backend" -> "AI_EMAIL_MANAGER/backend"
        if len(folder_parts) >= 2:
            parent_folder = folder_parts[-2]
            return f"{parent_folder}/{last_folder}"

        return last_folder if last_folder else "Unknown"

    def get_process_details_cached(self, pid: int) -> Dict:
        """캐시된 프로세스 정보 가져오기 (중복 조회 방지)"""
        if pid in self._process_cache:
            return self._process_cache[pid]

        details = self.get_process_details_single(pid)
        self._process_cache[pid] = details
        return details

    def clear_process_cache(self):
        """프로세스 캐시 초기화"""
        self._process_cache.clear()

    def get_app_name_from_package_json(self, cwd: str) -> Optional[str]:
        """package.json에서 앱 이름 추출"""
        if not cwd or cwd == "Unknown":
            return None

        # 현재 디렉토리부터 상위 디렉토리까지 package.json 검색
        current = Path(cwd)
        for _ in range(5):  # 최대 5단계 상위까지 검색
            package_json = current / "package.json"
            if package_json.exists():
                try:
                    import json

                    with open(package_json, "r") as f:
                        data = json.load(f)
                        return data.get("name")
                except:
                    pass
            if current.parent == current:
                break
            current = current.parent
        return None

    def get_project_description(self, cwd: str) -> Optional[str]:
        """프로젝트 설명 추출 (package.json, pyproject.toml, Python docstring, README)"""
        if not cwd or cwd == "Unknown":
            return None

        current = Path(cwd)

        # 1. package.json description
        for _ in range(3):
            package_json = current / "package.json"
            if package_json.exists():
                try:
                    import json

                    with open(package_json, "r") as f:
                        data = json.load(f)
                        desc = data.get("description")
                        if desc:
                            return desc[:25]  # 최대 25자
                except:
                    pass
            if current.parent == current:
                break
            current = current.parent

        current = Path(cwd)

        # 2. pyproject.toml description
        for _ in range(3):
            pyproject = current / "pyproject.toml"
            if pyproject.exists():
                try:
                    with open(pyproject, "r") as f:
                        content = f.read()
                        # [project] 섹션의 description 찾기
                        match = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
                        if match:
                            return match.group(1)[:25]
                except:
                    pass
            if current.parent == current:
                break
            current = current.parent

        # 3. Python main.py 또는 app.py docstring
        for py_name in ["main.py", "app.py", "__init__.py"]:
            py_file = Path(cwd) / py_name
            if py_file.exists():
                try:
                    with open(py_file, "r") as f:
                        content = f.read(1000)  # 첫 1000자
                        # 트리플 쿼트 docstring 찾기 (""" 또는 ''')
                        match = re.search(
                            r'^\s*(?:#[^\n]*\n)*\s*["\']["\']["\']([^"\']+)', content, re.MULTILINE
                        )
                        if match:
                            # 첫 줄만 추출하고 길이 제한
                            first_line = match.group(1).strip().split("\n")[0]
                            return first_line[:25]
                except:
                    pass

        # 4. README.md 첫 줄
        for readme_name in ["README.md", "readme.md", "README.txt"]:
            readme = Path(cwd) / readme_name
            if readme.exists():
                try:
                    with open(readme, "r") as f:
                        first_line = f.readline().strip()
                        # # 제목 제거
                        if first_line.startswith("#"):
                            first_line = first_line.lstrip("#").strip()
                        if first_line:
                            return first_line[:25]
                except:
                    pass

        return None

    def get_process_details_single(self, pid: int) -> Dict:
        """단일 프로세스의 상세 정보 가져오기"""
        try:
            process = psutil.Process(pid)
            cmdline = process.cmdline()
            if len(cmdline) > 3:
                cmdline_str = " ".join(cmdline[:3]) + "..."
            else:
                cmdline_str = " ".join(cmdline)

            cwd = process.cwd()
            app_name = self.get_app_name_from_package_json(cwd)
            description = self.get_project_description(cwd)

            return {
                "pid": pid,
                "cwd": cwd,
                "app_name": app_name,
                "description": description,
                "cmdline": cmdline_str,
                "memory": f"{process.memory_info().rss / 1024 / 1024:.1f}MB",
                "cpu": f"{process.cpu_percent():.1f}%",
                "user": process.username(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {
                "pid": pid,
                "cwd": "Unknown",
                "app_name": None,
                "description": None,
                "cmdline": "",
                "memory": "N/A",
                "cpu": "N/A",
                "user": "N/A",
            }

    def get_open_ports_sequential(self) -> List[Dict]:
        """순차적으로 포트 정보 수집 (기존 방식)"""
        try:
            cmd = f"echo '{self.sudo_password}' | sudo -S ss -tulnp '( sport >= :{self.port_range[0]} and sport <= :{self.port_range[1]} )'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                console.print("[red]Error running ss command[/red]")
                return []

            ports_info = []
            lines = result.stdout.strip().split("\n")[1:]

            for line in lines:
                if not line.strip() or "[sudo]" in line:
                    continue

                parts = line.split()
                if len(parts) < 6:
                    continue

                # 포트 정보 파싱
                local_addr = parts[4]
                port_match = re.search(r":(\d+)$", local_addr)
                if not port_match:
                    continue

                port = int(port_match.group(1))

                # PID 추출
                pid_match = re.search(r"pid=(\d+)", line)
                pid = int(pid_match.group(1)) if pid_match else None

                # 프로세스 이름 추출
                process_match = re.search(r'"([^"]+)"', line)
                process_name = process_match.group(1) if process_match else "Unknown"

                # 프로세스 상세 정보 (순차적)
                process_info = self.get_process_details_single(pid) if pid else {}

                # 프로젝트 폴더 추출
                project_folder = self.extract_project_folder(process_info.get("cwd", ""))

                ports_info.append(
                    {
                        "protocol": parts[0],
                        "state": parts[1],
                        "port": port,
                        "pid": pid,
                        "process_name": process_name,
                        "project_folder": project_folder,
                        "app_name": process_info.get("app_name"),
                        "description": process_info.get("description"),
                        "cwd": process_info.get("cwd", "Unknown"),
                        "cmdline": process_info.get("cmdline", ""),
                        "memory": process_info.get("memory", "N/A"),
                        "cpu": process_info.get("cpu", "N/A"),
                        "user": process_info.get("user", "N/A"),
                    }
                )

            return ports_info

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return []

    def get_open_ports_parallel(self) -> List[Dict]:
        """병렬로 포트 정보 수집 (Free-threading 최적화)"""
        try:
            cmd = f"echo '{self.sudo_password}' | sudo -S ss -tulnp '( sport >= :{self.port_range[0]} and sport <= :{self.port_range[1]} )'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                console.print("[red]Error running ss command[/red]")
                return []

            # 먼저 기본 포트 정보만 수집
            basic_ports_info = []
            lines = result.stdout.strip().split("\n")[1:]

            for line in lines:
                if not line.strip() or "[sudo]" in line:
                    continue

                parts = line.split()
                if len(parts) < 6:
                    continue

                # 포트 정보 파싱
                local_addr = parts[4]
                port_match = re.search(r":(\d+)$", local_addr)
                if not port_match:
                    continue

                port = int(port_match.group(1))

                # PID 추출
                pid_match = re.search(r"pid=(\d+)", line)
                pid = int(pid_match.group(1)) if pid_match else None

                # 프로세스 이름 추출
                process_match = re.search(r'"([^"]+)"', line)
                process_name = process_match.group(1) if process_match else "Unknown"

                basic_ports_info.append(
                    {
                        "protocol": parts[0],
                        "state": parts[1],
                        "port": port,
                        "pid": pid,
                        "process_name": process_name,
                    }
                )

            # PID 목록 추출 (중복 제거로 조회 최소화)
            unique_pids = list(set(info["pid"] for info in basic_ports_info if info["pid"]))

            # 병렬로 프로세스 상세 정보 수집 (중복 PID는 한 번만 조회)
            process_details_map = {}
            if unique_pids:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {
                        executor.submit(self.get_process_details_cached, pid): pid
                        for pid in unique_pids
                    }
                    for future in futures:
                        pid = futures[future]
                        try:
                            details = future.result()
                            process_details_map[pid] = details
                        except Exception as e:
                            process_details_map[pid] = {
                                "pid": pid,
                                "cwd": "Unknown",
                                "description": None,
                                "cmdline": "",
                                "memory": "N/A",
                                "cpu": "N/A",
                                "user": "N/A",
                            }

            # 최종 포트 정보 구성
            ports_info = []
            for basic_info in basic_ports_info:
                pid = basic_info["pid"]
                process_info = process_details_map.get(pid, {}) if pid else {}

                project_folder = self.extract_project_folder(process_info.get("cwd", ""))

                ports_info.append(
                    {
                        **basic_info,
                        "project_folder": project_folder,
                        "app_name": process_info.get("app_name"),
                        "description": process_info.get("description"),
                        "cwd": process_info.get("cwd", "Unknown"),
                        "cmdline": process_info.get("cmdline", ""),
                        "memory": process_info.get("memory", "N/A"),
                        "cpu": process_info.get("cpu", "N/A"),
                        "user": process_info.get("user", "N/A"),
                    }
                )

            return ports_info

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return []

    def get_open_ports(self, use_parallel=None) -> tuple[List[Dict], float]:
        """포트 정보 수집 (자동으로 최적 방식 선택)"""
        # 캐시 초기화 (매 조회 시 새로운 데이터)
        self.clear_process_cache()

        # use_parallel이 명시되지 않으면 GIL 상태에 따라 자동 결정
        if use_parallel is None:
            use_parallel = self.gil_disabled

        start_time = time.time()

        if use_parallel:
            ports_info = self.get_open_ports_parallel()
        else:
            ports_info = self.get_open_ports_sequential()

        elapsed = time.time() - start_time

        return ports_info, elapsed

    def extract_project_folder(self, cwd: str) -> str:
        """CWD에서 프로젝트 폴더 경로 추출 (DEVEL 이후 전체 경로)"""
        if cwd == "Unknown" or not cwd:
            return "Unknown"

        if "/DEVEL/" in cwd:
            parts = cwd.split("/DEVEL/")
            if len(parts) > 1 and parts[1]:
                return parts[1]  # DEVEL/ 이후 전체 경로 반환

        return Path(cwd).name if cwd else "Unknown"

    def display_ports_with_actions(self, ports_info: List[Dict]):
        """포트 정보를 테이블로 표시 (모바일 자동 감지)"""
        # ANSI escape: 화면 지우고 커서를 맨 위로 이동 (tmux 호환)
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

        # 터미널 폭 감지하여 모바일/PC 모드 결정
        try:
            term_width = os.get_terminal_size().columns
        except:
            term_width = 80  # 기본값

        is_mobile = term_width < 80  # 80컬럼 미만이면 모바일 모드

        # 헤더 정보
        header_text = f"🚀 Port Monitor ({self.port_range[0]}-{self.port_range[1]})"
        console.print(Panel(header_text, style="bold cyan"))

        # 타임스탬프
        timestamp = time.strftime("%H:%M:%S" if is_mobile else "%Y-%m-%d %H:%M:%S")
        console.print(f"[dim]{timestamp}[/dim]")
        if not is_mobile:
            console.print(f"[dim]Usage: Type process No. and press Enter to kill[/dim]")
        console.print("")

        # 테이블 (모바일: 간소화, PC: 전체 정보)
        table = Table(show_header=True, header_style="bold magenta")

        if is_mobile:
            # 모바일 모드: No., Port, App, Memory 표시
            table.add_column("No.", style="bold white", width=3)
            table.add_column("Port", style="cyan", width=5)
            table.add_column("App", style="bold green")
            table.add_column("Mem", style="red", width=6)
        else:
            # PC 모드: 전체 정보 표시
            table.add_column("No.", style="bold white", width=4)
            table.add_column("Port", style="cyan", width=6)
            table.add_column("App Name", style="bold cyan", width=28)
            table.add_column("Project Path", style="green", width=32)
            table.add_column("PID", style="yellow", width=8)
            table.add_column("Mem", style="red", width=8)
            table.add_column("User", style="magenta", width=10)

        for idx, port in enumerate(sorted(ports_info, key=lambda x: x["port"]), 1):
            # 친숙한 앱 이름 생성 (시스템 서비스, 설명, 폴더명 처리)
            app_name = self.get_friendly_app_name(
                port.get("process_name", "Unknown"),
                port.get("project_folder", "Unknown"),
                port.get("app_name"),
                port.get("description"),
            )

            app_display = (
                f"[bold cyan]{app_name}[/bold cyan]"
                if app_name != "Unknown"
                else "[dim]Unknown[/dim]"
            )

            if port["project_folder"] != "Unknown":
                folder_display = f"[green]{port['project_folder']}[/green]"
            else:
                folder_display = "[dim]Unknown[/dim]"

            if is_mobile:
                table.add_row(str(idx), str(port["port"]), app_display, str(port["memory"]))
            else:
                table.add_row(
                    str(idx),
                    str(port["port"]),
                    app_display,
                    folder_display,
                    str(port["pid"]) if port["pid"] else "N/A",
                    str(port["memory"]),
                    port["user"],
                )

        console.print(table)
        console.print(f"\n[bold]Total:[/bold] {len(ports_info)}")
        console.print("")  # 카운트다운과 구분용 빈 줄

        return ports_info

    def kill_process(self, pid: int, force: bool = False) -> bool:
        """프로세스 종료"""
        try:
            signal_type = signal.SIGKILL if force else signal.SIGTERM
            signal_name = "SIGKILL" if force else "SIGTERM"

            try:
                os.kill(pid, signal_type)
                console.print(f"[green]✓ Sent {signal_name} to process {pid}[/green]")
                return True
            except PermissionError:
                cmd = f"echo '{self.sudo_password}' | sudo -S kill -{signal_type} {pid}"
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                console.print(f"[green]✓ Killed process {pid} with sudo[/green]")
                return True

        except ProcessLookupError:
            console.print(f"[yellow]Process {pid} already terminated[/yellow]")
            return True
        except Exception as e:
            console.print(f"[red]✗ Error killing process {pid}: {e}[/red]")
            return False

    def benchmark_comparison(self, iterations=3):
        """순차 vs 병렬 처리 성능 비교"""
        console.print("\n" + "=" * 70)
        console.print(Panel("⚡ 성능 벤치마크: 순차 처리 vs 병렬 처리", style="bold yellow"))
        console.print("=" * 70)

        # 순차 처리 테스트
        console.print("\n[bold cyan]1. 순차 처리 (기존 방식)[/bold cyan]")
        sequential_times = []
        for i in range(iterations):
            console.print(f"  테스트 {i+1}/{iterations}...", end=" ")
            _, elapsed = self.get_open_ports(use_parallel=False)
            sequential_times.append(elapsed)
            console.print(f"{elapsed:.3f}초")

        avg_sequential = sum(sequential_times) / len(sequential_times)
        console.print(f"[bold]평균 시간:[/bold] {avg_sequential:.3f}초")

        # 병렬 처리 테스트
        console.print("\n[bold cyan]2. 병렬 처리 (Free-threading)[/bold cyan]")
        parallel_times = []
        for i in range(iterations):
            console.print(f"  테스트 {i+1}/{iterations}...", end=" ")
            _, elapsed = self.get_open_ports(use_parallel=True)
            parallel_times.append(elapsed)
            console.print(f"{elapsed:.3f}초")

        avg_parallel = sum(parallel_times) / len(parallel_times)
        console.print(f"[bold]평균 시간:[/bold] {avg_parallel:.3f}초")

        # 결과 분석
        console.print("\n" + "=" * 70)
        console.print("[bold cyan]📊 성능 분석 결과[/bold cyan]")
        console.print("=" * 70)

        speedup = avg_sequential / avg_parallel if avg_parallel > 0 else 0
        improvement = (
            ((avg_sequential - avg_parallel) / avg_sequential * 100) if avg_sequential > 0 else 0
        )

        console.print(f"순차 처리:    {avg_sequential:.3f}초")
        console.print(f"병렬 처리:    {avg_parallel:.3f}초")
        console.print(f"속도 향상:    {speedup:.2f}x")
        console.print(f"성능 개선:    {improvement:.1f}%")

        if self.gil_disabled:
            if speedup > 1.5:
                console.print(
                    "\n[bold green]✅ Free-threading이 효과적으로 작동합니다![/bold green]"
                )
                console.print(f"   → {self.max_workers}개 워커가 동시에 실행됨")
                console.print(f"   → CPU 코어를 완전히 활용")
            elif speedup > 1.1:
                console.print("\n[bold yellow]⚠️  약간의 성능 향상이 있습니다[/bold yellow]")
                console.print("   → 더 많은 작업이 있을 때 효과가 더 클 것입니다")
            else:
                console.print("\n[bold red]❌ 예상보다 성능 향상이 적습니다[/bold red]")
                console.print("   → 프로세스 수가 적거나 I/O 대기가 많을 수 있습니다")
        else:
            console.print("\n[bold yellow]ℹ️  GIL이 활성화된 일반 모드입니다[/bold yellow]")
            console.print("   → Python 3.14t (free-threading 빌드)를 사용하면 성능이 향상됩니다")
            console.print("   → pyenv install 3.14.0t 로 설치 가능")

        console.print("=" * 70 + "\n")

    def get_non_blocking_input(self, timeout=1):
        """비차단 입력 받기"""
        if sys.stdin in select.select([sys.stdin], [], [], timeout)[0]:
            return sys.stdin.read(1)
        return None

    def get_multi_char_input(self, prompt_text: str, timeout: int = 30) -> str:
        """멀티 문자 입력을 받는 함수 (개선됨 - ESC는 None 반환)"""
        sys.stdout.write("\r\033[K")
        sys.stdout.write(prompt_text)
        sys.stdout.flush()

        input_text = ""
        start_time = time.time()

        while True:
            if time.time() - start_time > timeout:
                break

            char = self.get_non_blocking_input(0.1)
            if char == "\n" or char == "\r":
                break
            elif char and char.isdigit():
                input_text += char
                sys.stdout.write(char)
                sys.stdout.flush()
            elif char == "\x7f" or char == "\b":  # backspace
                if input_text:
                    input_text = input_text[:-1]
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            elif char == "\x1b":  # ESC key
                return None  # None 반환으로 취소 (빈 문자열과 구분)
            elif char and char.isalpha():
                # 알파벳이 입력되면 즉시 종료 (q, r, h 등의 명령어)
                return char

        return input_text

    def quick_view(self, interval=60):
        """자동 갱신 모드 (카운트다운 포함)"""
        # 터미널 설정 저장
        old_settings = None
        is_terminal = sys.stdin.isatty()

        if is_terminal:
            try:
                old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except:
                is_terminal = False

        try:
            hidden_pids = set()
            last_update = 0
            countdown = interval

            # 초기 화면 표시
            ports_info, _ = self.get_open_ports()
            visible_ports = [p for p in ports_info if p["pid"] not in hidden_pids]
            if visible_ports or not hidden_pids:
                self.display_ports_with_actions(visible_ports)
                last_update = time.time()

            while True:
                current_time = time.time()

                # 갱신 시간 체크
                if current_time - last_update >= interval:
                    ports_info, _ = self.get_open_ports()
                    visible_ports = [p for p in ports_info if p["pid"] not in hidden_pids]

                    if not visible_ports and not hidden_pids:
                        console.print(
                            f"[yellow]No ports found in range {self.port_range[0]}-{self.port_range[1]}[/yellow]"
                        )
                        time.sleep(2)
                        continue

                    self.display_ports_with_actions(visible_ports)
                    last_update = current_time
                    countdown = interval

                # 카운트다운 표시 (화면 하단 고정 위치에 표시)
                if countdown > 0:
                    # 터미널 크기 가져오기
                    try:
                        term_height = os.get_terminal_size().lines
                    except:
                        term_height = 24  # 기본값
                    # 커서를 화면 맨 아래줄로 이동하고 줄 지우기
                    sys.stdout.write(f"\033[{term_height};1H")  # 마지막 줄로 이동
                    sys.stdout.write("\033[K")  # 줄 지우기
                    sys.stdout.write(f"[{countdown}s] No.=kill | h=hide | r=refresh | q=quit")
                    sys.stdout.flush()
                    countdown -= 1

                # 입력 체크 (터미널 환경에서만)
                user_input = None
                if is_terminal:
                    user_input = self.get_non_blocking_input(1)
                else:
                    time.sleep(1)

                if user_input:
                    if user_input.lower() == "q":
                        console.print("\n[yellow]Exiting...[/yellow]")
                        break
                    elif user_input.lower() == "r":
                        # 즉시 갱신
                        ports_info, _ = self.get_open_ports()
                        visible_ports = [p for p in ports_info if p["pid"] not in hidden_pids]
                        self.display_ports_with_actions(visible_ports)
                        last_update = time.time()
                        countdown = interval
                    elif user_input.lower() == "h":
                        # Hide 모드
                        sys.stdout.write("\r\033[K")
                        sys.stdout.flush()

                        if is_terminal:
                            hide_input = self.get_multi_char_input(
                                "Hide process No. (press Enter to confirm, ESC to cancel): "
                            )
                            if hide_input and hide_input.isdigit():
                                hide_idx = int(hide_input) - 1
                                if 0 <= hide_idx < len(visible_ports):
                                    sorted_ports = sorted(visible_ports, key=lambda x: x["port"])
                                    pid_to_hide = sorted_ports[hide_idx]["pid"]
                                    if pid_to_hide:
                                        hidden_pids.add(pid_to_hide)
                                        port_num = sorted_ports[hide_idx]["port"]
                                        proj = sorted_ports[hide_idx]["project_folder"]
                                        console.print(
                                            f"\n[yellow]✓ Hidden: No.{hide_idx+1} - {proj} (Port {port_num}, PID {pid_to_hide})[/yellow]"
                                        )
                                        time.sleep(1)
                                    else:
                                        console.print(f"\n[red]No PID found[/red]")
                                        time.sleep(1)
                                else:
                                    console.print(
                                        f"\n[red]Invalid: {hide_input} (range: 1-{len(visible_ports)})[/red]"
                                    )
                                    time.sleep(1)

                        # 갱신
                        ports_info, _ = self.get_open_ports()
                        visible_ports = [p for p in ports_info if p["pid"] not in hidden_pids]
                        self.display_ports_with_actions(visible_ports)
                        countdown = interval
                    elif user_input.isdigit():
                        # Kill 모드 - 숫자 입력 시작됨, 즉시 나머지 입력 받기
                        sys.stdout.write("\r\033[K")
                        sys.stdout.flush()

                        if is_terminal:
                            # 첫 숫자 표시하고 나머지 즉시 입력받기
                            full_input = self.get_multi_char_input(
                                f"Kill process No. (press Enter to confirm, ESC to cancel): {user_input}"
                            )

                            # ESC 취소 처리 (None 반환)
                            if full_input is None:
                                ports_info, _ = self.get_open_ports()
                                visible_ports = [
                                    p for p in ports_info if p["pid"] not in hidden_pids
                                ]
                                self.display_ports_with_actions(visible_ports)
                                countdown = interval
                                continue

                            # 명령어 문자 처리
                            if full_input and full_input.isalpha():
                                if full_input.lower() == "q":
                                    console.print("\n[yellow]Exiting...[/yellow]")
                                    break
                                elif full_input.lower() == "r":
                                    ports_info, _ = self.get_open_ports()
                                    visible_ports = [
                                        p for p in ports_info if p["pid"] not in hidden_pids
                                    ]
                                    self.display_ports_with_actions(visible_ports)
                                    last_update = time.time()
                                    countdown = interval
                                    continue

                            # 숫자 조합 (full_input이 빈 문자열이면 user_input만 사용)
                            if full_input and full_input.isdigit():
                                kill_input = user_input + full_input
                            else:
                                kill_input = user_input  # 한자리수 입력 + Enter 경우
                        else:
                            kill_input = user_input

                        # 프로세스 종료 처리
                        if kill_input and kill_input.isdigit():
                            idx = int(kill_input) - 1
                            if 0 <= idx < len(visible_ports):
                                sorted_ports = sorted(visible_ports, key=lambda x: x["port"])
                                selected = sorted_ports[idx]

                                if selected["pid"]:
                                    console.print(
                                        f"\n[yellow]Killing No.{idx+1}: {selected['project_folder']} (Port {selected['port']}, PID {selected['pid']})[/yellow]"
                                    )
                                    if self.kill_process(selected["pid"]):
                                        console.print(
                                            f"[green]✓ Process {selected['pid']} killed[/green]"
                                        )
                                    time.sleep(1)

                                    # 갱신
                                    ports_info, _ = self.get_open_ports()
                                    visible_ports = [
                                        p for p in ports_info if p["pid"] not in hidden_pids
                                    ]
                                    self.display_ports_with_actions(visible_ports)
                                    last_update = time.time()
                                    countdown = interval
                                else:
                                    console.print(
                                        f"\n[red]No PID for port {selected['port']}[/red]"
                                    )
                                    time.sleep(1)
                                    ports_info, _ = self.get_open_ports()
                                    visible_ports = [
                                        p for p in ports_info if p["pid"] not in hidden_pids
                                    ]
                                    self.display_ports_with_actions(visible_ports)
                                    countdown = interval
                            else:
                                console.print(
                                    f"\n[red]Invalid: {kill_input} (range: 1-{len(visible_ports)})[/red]"
                                )
                                time.sleep(1)
                                ports_info, _ = self.get_open_ports()
                                visible_ports = [
                                    p for p in ports_info if p["pid"] not in hidden_pids
                                ]
                                self.display_ports_with_actions(visible_ports)
                                countdown = interval

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted by user[/yellow]")
        finally:
            # 터미널 설정 복원
            if old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except:
                    pass
            console.print("\n")


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Python 3.14 Free-Threading Port Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  %(prog)s                    # 기본 포트 모니터링 (60초 자동 갱신)
  %(prog)s -t 30              # 30초마다 자동 갱신
  %(prog)s --benchmark        # 성능 벤치마크 실행
  %(prog)s --parallel         # 강제로 병렬 처리 사용
  %(prog)s --sequential       # 강제로 순차 처리 사용
        """,
    )
    parser.add_argument("-b", "--benchmark", action="store_true", help="성능 벤치마크 실행")
    parser.add_argument(
        "-t", "--interval", type=int, default=60, help="자동 갱신 주기(초) (기본: 60)"
    )
    parser.add_argument("--parallel", action="store_true", help="병렬 처리 강제 사용")
    parser.add_argument("--sequential", action="store_true", help="순차 처리 강제 사용")
    parser.add_argument("--start-port", type=int, default=443, help="시작 포트 (기본: 443 - HTTPS)")
    parser.add_argument("--end-port", type=int, default=9000, help="종료 포트 (기본: 9000)")

    args = parser.parse_args()

    monitor = FreeThreadingPortMonitor(args.start_port, args.end_port)

    try:
        if args.benchmark:
            # 먼저 한 번 표시
            ports_info, elapsed = monitor.get_open_ports()
            monitor.display_ports_with_actions(ports_info)
            console.print(f"\n[bold]포트 정보 수집 시간:[/bold] {elapsed:.3f}초\n")
            # 벤치마크 실행
            monitor.benchmark_comparison()
        else:
            # 처리 방식 결정
            use_parallel = None
            if args.parallel:
                use_parallel = True
            elif args.sequential:
                use_parallel = False

            # 자동 갱신 모니터링
            monitor.quick_view(interval=args.interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
