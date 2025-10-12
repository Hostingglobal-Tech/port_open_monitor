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
    def __init__(self, start_port=3000, end_port=9000):
        self.port_range = (start_port, end_port)
        # sudo 비밀번호는 환경변수 SUDO_PASSWORD에서 가져오거나 직접 입력
        self.sudo_password = os.getenv('SUDO_PASSWORD', '')
        self.gil_disabled = self.check_gil_status()
        self.max_workers = os.cpu_count() or 4

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

    def get_process_details_single(self, pid: int) -> Dict:
        """단일 프로세스의 상세 정보 가져오기"""
        try:
            process = psutil.Process(pid)
            cmdline = process.cmdline()
            if len(cmdline) > 3:
                cmdline_str = ' '.join(cmdline[:3]) + '...'
            else:
                cmdline_str = ' '.join(cmdline)

            return {
                'pid': pid,
                'cwd': process.cwd(),
                'cmdline': cmdline_str,
                'memory': f"{process.memory_info().rss / 1024 / 1024:.1f}MB",
                'cpu': f"{process.cpu_percent():.1f}%",
                'user': process.username()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {'pid': pid, 'cwd': 'Unknown', 'cmdline': '', 'memory': 'N/A', 'cpu': 'N/A', 'user': 'N/A'}

    def get_open_ports_sequential(self) -> List[Dict]:
        """순차적으로 포트 정보 수집 (기존 방식)"""
        try:
            cmd = f"echo '{self.sudo_password}' | sudo -S ss -tulnp '( sport >= :{self.port_range[0]} and sport <= :{self.port_range[1]} )'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            if result.returncode != 0:
                console.print("[red]Error running ss command[/red]")
                return []

            ports_info = []
            lines = result.stdout.strip().split('\n')[1:]

            for line in lines:
                if not line.strip() or '[sudo]' in line:
                    continue

                parts = line.split()
                if len(parts) < 6:
                    continue

                # 포트 정보 파싱
                local_addr = parts[4]
                port_match = re.search(r':(\d+)$', local_addr)
                if not port_match:
                    continue

                port = int(port_match.group(1))

                # PID 추출
                pid_match = re.search(r'pid=(\d+)', line)
                pid = int(pid_match.group(1)) if pid_match else None

                # 프로세스 이름 추출
                process_match = re.search(r'"([^"]+)"', line)
                process_name = process_match.group(1) if process_match else "Unknown"

                # 프로세스 상세 정보 (순차적)
                process_info = self.get_process_details_single(pid) if pid else {}

                # 프로젝트 폴더 추출
                project_folder = self.extract_project_folder(process_info.get('cwd', ''))

                ports_info.append({
                    'protocol': parts[0],
                    'state': parts[1],
                    'port': port,
                    'pid': pid,
                    'process_name': process_name,
                    'project_folder': project_folder,
                    'cwd': process_info.get('cwd', 'Unknown'),
                    'cmdline': process_info.get('cmdline', ''),
                    'memory': process_info.get('memory', 'N/A'),
                    'cpu': process_info.get('cpu', 'N/A'),
                    'user': process_info.get('user', 'N/A')
                })

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
            lines = result.stdout.strip().split('\n')[1:]

            for line in lines:
                if not line.strip() or '[sudo]' in line:
                    continue

                parts = line.split()
                if len(parts) < 6:
                    continue

                # 포트 정보 파싱
                local_addr = parts[4]
                port_match = re.search(r':(\d+)$', local_addr)
                if not port_match:
                    continue

                port = int(port_match.group(1))

                # PID 추출
                pid_match = re.search(r'pid=(\d+)', line)
                pid = int(pid_match.group(1)) if pid_match else None

                # 프로세스 이름 추출
                process_match = re.search(r'"([^"]+)"', line)
                process_name = process_match.group(1) if process_match else "Unknown"

                basic_ports_info.append({
                    'protocol': parts[0],
                    'state': parts[1],
                    'port': port,
                    'pid': pid,
                    'process_name': process_name,
                })

            # PID 목록 추출
            pids = [info['pid'] for info in basic_ports_info if info['pid']]

            # 병렬로 프로세스 상세 정보 수집
            process_details_map = {}
            if pids:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {executor.submit(self.get_process_details_single, pid): pid for pid in pids}
                    for future in futures:
                        pid = futures[future]
                        try:
                            details = future.result()
                            process_details_map[pid] = details
                        except Exception as e:
                            process_details_map[pid] = {
                                'pid': pid,
                                'cwd': 'Unknown',
                                'cmdline': '',
                                'memory': 'N/A',
                                'cpu': 'N/A',
                                'user': 'N/A'
                            }

            # 최종 포트 정보 구성
            ports_info = []
            for basic_info in basic_ports_info:
                pid = basic_info['pid']
                process_info = process_details_map.get(pid, {}) if pid else {}

                project_folder = self.extract_project_folder(process_info.get('cwd', ''))

                ports_info.append({
                    **basic_info,
                    'project_folder': project_folder,
                    'cwd': process_info.get('cwd', 'Unknown'),
                    'cmdline': process_info.get('cmdline', ''),
                    'memory': process_info.get('memory', 'N/A'),
                    'cpu': process_info.get('cpu', 'N/A'),
                    'user': process_info.get('user', 'N/A')
                })

            return ports_info

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return []

    def get_open_ports(self, use_parallel=None) -> tuple[List[Dict], float]:
        """포트 정보 수집 (자동으로 최적 방식 선택)"""
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
        """CWD에서 프로젝트 폴더명 추출"""
        if cwd == 'Unknown' or not cwd:
            return 'Unknown'

        if '/DEVEL/' in cwd:
            parts = cwd.split('/DEVEL/')
            if len(parts) > 1:
                project_parts = parts[1].split('/')
                if project_parts[0]:
                    return project_parts[0]

        return Path(cwd).name if cwd else 'Unknown'

    def display_ports_with_actions(self, ports_info: List[Dict], elapsed_time: float):
        """포트 정보를 테이블로 표시"""
        # 헤더 정보
        header_text = f"🚀 Port Monitor ({self.port_range[0]}-{self.port_range[1]})"
        console.print(Panel(header_text, style="bold cyan"))

        # 테이블
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("No.", style="bold white", width=5)
        table.add_column("Port", style="cyan", width=8)
        table.add_column("Project Folder", style="bold green", width=30)
        table.add_column("PID", style="yellow", width=8)
        table.add_column("Process", style="blue", width=20)
        table.add_column("Memory", style="red", width=10)
        table.add_column("User", style="magenta", width=12)

        for idx, port in enumerate(sorted(ports_info, key=lambda x: x['port']), 1):
            if port['project_folder'] != 'Unknown':
                folder_display = f"[bold green]{port['project_folder']}[/bold green]"
            else:
                folder_display = "[dim]Unknown[/dim]"

            table.add_row(
                str(idx),
                str(port['port']),
                folder_display,
                str(port['pid']) if port['pid'] else "N/A",
                port['process_name'][:20],
                str(port['memory']),
                port['user']
            )

        console.print(table)
        console.print(f"\n[bold]Total ports in use:[/bold] {len(ports_info)}")
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
        console.print("\n" + "="*70)
        console.print(Panel("⚡ 성능 벤치마크: 순차 처리 vs 병렬 처리", style="bold yellow"))
        console.print("="*70)

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
        console.print("\n" + "="*70)
        console.print("[bold cyan]📊 성능 분석 결과[/bold cyan]")
        console.print("="*70)

        speedup = avg_sequential / avg_parallel if avg_parallel > 0 else 0
        improvement = ((avg_sequential - avg_parallel) / avg_sequential * 100) if avg_sequential > 0 else 0

        console.print(f"순차 처리:    {avg_sequential:.3f}초")
        console.print(f"병렬 처리:    {avg_parallel:.3f}초")
        console.print(f"속도 향상:    {speedup:.2f}x")
        console.print(f"성능 개선:    {improvement:.1f}%")

        if self.gil_disabled:
            if speedup > 1.5:
                console.print("\n[bold green]✅ Free-threading이 효과적으로 작동합니다![/bold green]")
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

        console.print("="*70 + "\n")

    def quick_view(self):
        """빠른 보기 모드"""
        hidden_pids = set()

        while True:
            ports_info, elapsed = self.get_open_ports()

            if not ports_info:
                console.print(f"[yellow]No ports found in range {self.port_range[0]}-{self.port_range[1]}[/yellow]")
                return

            # 숨긴 프로세스 제외
            visible_ports = [p for p in ports_info if p['pid'] not in hidden_pids]

            if not visible_ports:
                console.print("[yellow]모든 프로세스가 숨겨졌습니다.[/yellow]")
                if Confirm.ask("숨김 목록을 초기화하시겠습니까?"):
                    hidden_pids.clear()
                    continue
                return

            self.display_ports_with_actions(visible_ports, elapsed)

            if not sys.stdin.isatty():
                return

            # 메뉴
            console.print("\n[bold cyan]옵션:[/bold cyan]")
            console.print("1. 프로세스 숨기기")
            console.print("2. 프로세스 종료")
            console.print("3. 프로그램 종료")

            choice = Prompt.ask("[bold yellow]선택[/bold yellow]", choices=["1", "2", "3"], default="3")

            if choice == "1":
                idx = Prompt.ask("숨길 프로세스 번호")
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(visible_ports):
                        sorted_ports = sorted(visible_ports, key=lambda x: x['port'])
                        selected = sorted_ports[idx]
                        if selected['pid']:
                            hidden_pids.add(selected['pid'])
                            console.print(f"[green]✓ PID {selected['pid']} ({selected['project_folder']}) 숨김 처리됨[/green]")
                except ValueError:
                    console.print("[red]잘못된 입력[/red]")
            elif choice == "2":
                idx = Prompt.ask("종료할 프로세스 번호")
                try:
                    idx = int(idx) - 1
                    if 0 <= idx < len(visible_ports):
                        sorted_ports = sorted(visible_ports, key=lambda x: x['port'])
                        selected = sorted_ports[idx]
                        if selected['pid']:
                            if Confirm.ask(f"[{selected['project_folder']}] 프로세스 종료 (PID: {selected['pid']})?"):
                                self.kill_process(selected['pid'])
                except ValueError:
                    console.print("[red]잘못된 입력[/red]")
            elif choice == "3":
                break


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Python 3.14 Free-Threading Port Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  %(prog)s                    # 기본 포트 모니터링
  %(prog)s --benchmark        # 성능 벤치마크 실행
  %(prog)s --parallel         # 강제로 병렬 처리 사용
  %(prog)s --sequential       # 강제로 순차 처리 사용
        """
    )
    parser.add_argument('-b', '--benchmark', action='store_true', help='성능 벤치마크 실행')
    parser.add_argument('--parallel', action='store_true', help='병렬 처리 강제 사용')
    parser.add_argument('--sequential', action='store_true', help='순차 처리 강제 사용')
    parser.add_argument('--start-port', type=int, default=3000, help='시작 포트 (기본: 3000)')
    parser.add_argument('--end-port', type=int, default=9000, help='종료 포트 (기본: 9000)')

    args = parser.parse_args()

    monitor = FreeThreadingPortMonitor(args.start_port, args.end_port)

    try:
        if args.benchmark:
            # 먼저 한 번 표시
            ports_info, elapsed = monitor.get_open_ports()
            monitor.display_ports_with_actions(ports_info, elapsed)
            # 벤치마크 실행
            monitor.benchmark_comparison()
        else:
            # 처리 방식 결정
            use_parallel = None
            if args.parallel:
                use_parallel = True
            elif args.sequential:
                use_parallel = False

            # 일회성 모니터링
            monitor.quick_view()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
