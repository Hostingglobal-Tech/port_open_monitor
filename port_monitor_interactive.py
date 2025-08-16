#!/usr/bin/env python3
"""
대화형 포트 모니터링 시스템
자동 갱신 중에도 프로세스 kill 가능
"""

import subprocess
import re
import os
import sys
import psutil
import signal
import select
import termios
import tty
from typing import List, Dict, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
import time
import threading

console = Console()

class InteractivePortMonitor:
    def __init__(self):
        self.port_range = (3000, 9000)
        self.sudo_password = "ak@5406454"
        self.running = True
        self.ports_info = []
        self.hidden_ports = set()  # 숨긴 포트 목록
        
    def get_open_ports(self) -> List[Dict]:
        """열려있는 포트 정보 수집"""
        try:
            cmd = f"echo '{self.sudo_password}' | sudo -S ss -tulnp '( sport >= :{self.port_range[0]} and sport <= :{self.port_range[1]} )'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
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
                
                # 프로세스 상세 정보
                process_info = self.get_process_details(pid) if pid else {}
                
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
            return []
    
    def get_process_details(self, pid: int) -> Dict:
        """PID로 프로세스 상세 정보 가져오기"""
        try:
            process = psutil.Process(pid)
            cmdline = process.cmdline()
            if len(cmdline) > 3:
                cmdline_str = ' '.join(cmdline[:3]) + '...'
            else:
                cmdline_str = ' '.join(cmdline)
            
            return {
                'cwd': process.cwd(),
                'cmdline': cmdline_str,
                'memory': f"{process.memory_info().rss / 1024 / 1024:.1f}MB",
                'cpu': f"{process.cpu_percent():.1f}%",
                'user': process.username()
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}
    
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
    
    def display_ports_with_actions(self, ports_info: List[Dict]):
        """포트 정보를 테이블로 표시"""
        console.clear()
        
        # 헤더
        console.print(Panel("🔄 Port Monitor (3000-9000)", style="bold cyan"))
        
        # 현재 시간
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"[dim]Last updated: {timestamp}[/dim]\n")
        
        # 숨긴 포트 제외하고 필터링
        visible_ports = [p for p in ports_info if p['port'] not in self.hidden_ports]
        
        # 숨긴 포트가 있으면 표시
        if self.hidden_ports:
            console.print(f"[yellow]Hidden ports: {', '.join(map(str, sorted(self.hidden_ports)))}[/yellow]")
            console.print(f"[dim]Press 'u' to unhide all, or 's' + number to show specific port[/dim]\n")
        
        # 테이블
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("No.", style="bold white", width=5)
        table.add_column("Port", style="cyan", width=8)
        table.add_column("Project Folder", style="bold green", width=35)
        table.add_column("PID", style="yellow", width=10)  # 8 -> 10으로 증가
        table.add_column("Process", style="blue", width=20)  # 25 -> 20으로 감소
        table.add_column("Memory", style="red", width=12)  # 10 -> 12로 증가
        table.add_column("User", style="magenta", width=12)
        
        for idx, port in enumerate(sorted(visible_ports, key=lambda x: x['port']), 1):
            if port['project_folder'] != 'Unknown':
                folder_display = f"[bold green]{port['project_folder']}[/bold green]"
            else:
                folder_display = "[dim]Unknown[/dim]"
            
            table.add_row(
                str(idx),
                str(port['port']),
                folder_display,
                str(port['pid']) if port['pid'] else "N/A",
                port['process_name'][:20],  # 25 -> 20으로 조정
                str(port['memory']),
                port['user']
            )
        
        console.print(table)
        console.print(f"\n[bold]Total ports:[/bold] {len(visible_ports)} visible, {len(self.hidden_ports)} hidden")
        console.print("")  # 카운트다운과 구분을 위한 빈 줄
        
        return visible_ports
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """프로세스 종료"""
        try:
            signal_type = signal.SIGKILL if force else signal.SIGTERM
            signal_name = "SIGKILL" if force else "SIGTERM"
            
            try:
                os.kill(pid, signal_type)
                console.print(f"\n[green]✓ Sent {signal_name} to process {pid}[/green]")
                return True
            except PermissionError:
                cmd = f"echo '{self.sudo_password}' | sudo -S kill -{signal_type} {pid}"
                subprocess.run(cmd, shell=True, check=True, capture_output=True)
                console.print(f"\n[green]✓ Killed process {pid} with sudo[/green]")
                return True
                
        except ProcessLookupError:
            console.print(f"\n[yellow]Process {pid} already terminated[/yellow]")
            return True
        except Exception as e:
            console.print(f"\n[red]✗ Error killing process {pid}: {e}[/red]")
            return False
    
    def get_non_blocking_input(self, timeout=1):
        """비차단 입력 받기"""
        if sys.stdin in select.select([sys.stdin], [], [], timeout)[0]:
            return sys.stdin.read(1)
        return None
    
    def interactive_monitor(self, interval=60):
        """대화형 자동 모니터링"""
        # 터미널 설정 저장 (터미널 환경에서만)
        old_settings = None
        is_terminal = sys.stdin.isatty()
        
        if is_terminal:
            try:
                old_settings = termios.tcgetattr(sys.stdin)
                # 터미널을 raw 모드로
                tty.setcbreak(sys.stdin.fileno())
            except:
                is_terminal = False
        
        try:
            
            last_update = 0
            countdown = interval
            
            while self.running:
                current_time = time.time()
                
                # 갱신 시간 체크
                if current_time - last_update >= interval:
                    self.ports_info = self.get_open_ports()
                    self.display_ports_with_actions(self.ports_info)
                    last_update = current_time
                    countdown = interval
                
                # 카운트다운 표시 (같은 줄에서 업데이트)
                if countdown > 0:
                    # 커서를 줄 처음으로 이동하고 줄 전체 지우기
                    sys.stdout.write('\r\033[K')
                    sys.stdout.write(f"[Auto refresh in {countdown}s] 1-9:kill, h:hide, u:unhide, s:show, r:refresh, q:quit")
                    sys.stdout.flush()
                    countdown -= 1
                
                # 입력 체크 (터미널 환경에서만)
                user_input = None
                if is_terminal:
                    user_input = self.get_non_blocking_input(1)
                else:
                    # 비터미널 환경에서는 그냥 1초 대기
                    time.sleep(1)
                
                if user_input:
                    if user_input.lower() == 'q':
                        console.print("\n[yellow]Exiting...[/yellow]")
                        break
                    elif user_input.lower() == 'r':
                        # 즉시 갱신
                        self.ports_info = self.get_open_ports()
                        self.display_ports_with_actions(self.ports_info)
                        last_update = time.time()
                        countdown = interval
                    elif user_input.lower() == 'h':
                        # Hide 모드 - 다음 입력을 기다림
                        sys.stdout.write('\r\033[K')
                        sys.stdout.write("Enter port number to hide (or 'c' to cancel): ")
                        sys.stdout.flush()
                        
                        hide_input = None
                        while not hide_input:
                            if is_terminal:
                                hide_input = self.get_non_blocking_input(5)
                            else:
                                break
                        
                        if hide_input and hide_input.isdigit():
                            hide_idx = int(hide_input) - 1
                            visible_ports = [p for p in self.ports_info if p['port'] not in self.hidden_ports]
                            if 0 <= hide_idx < len(visible_ports):
                                sorted_ports = sorted(visible_ports, key=lambda x: x['port'])
                                port_to_hide = sorted_ports[hide_idx]['port']
                                self.hidden_ports.add(port_to_hide)
                                console.print(f"\n[yellow]Hidden port {port_to_hide}[/yellow]")
                                time.sleep(1)
                        
                        # 갱신
                        self.display_ports_with_actions(self.ports_info)
                        countdown = interval
                    elif user_input.lower() == 'u':
                        # Unhide all
                        if self.hidden_ports:
                            console.print(f"\n[green]Unhiding all ports: {', '.join(map(str, sorted(self.hidden_ports)))}[/green]")
                            self.hidden_ports.clear()
                            time.sleep(1)
                            self.display_ports_with_actions(self.ports_info)
                        countdown = interval
                    elif user_input.lower() == 's':
                        # Show specific port
                        sys.stdout.write('\r\033[K')
                        sys.stdout.write("Enter port number to show: ")
                        sys.stdout.flush()
                        
                        show_input = None
                        while not show_input:
                            if is_terminal:
                                show_input = self.get_non_blocking_input(5)
                            else:
                                break
                        
                        if show_input and show_input.isdigit():
                            port_to_show = int(show_input)
                            if port_to_show in self.hidden_ports:
                                self.hidden_ports.remove(port_to_show)
                                console.print(f"\n[green]Showing port {port_to_show}[/green]")
                                time.sleep(1)
                                self.display_ports_with_actions(self.ports_info)
                        countdown = interval
                    elif user_input.isdigit():
                        idx = int(user_input) - 1
                        visible_ports = [p for p in self.ports_info if p['port'] not in self.hidden_ports]
                        if 0 <= idx < len(visible_ports):
                            sorted_ports = sorted(visible_ports, key=lambda x: x['port'])
                            selected = sorted_ports[idx]
                            
                            if selected['pid']:
                                console.print(f"\n\n[yellow]Killing {selected['project_folder']} on port {selected['port']} (PID: {selected['pid']})...[/yellow]")
                                self.kill_process(selected['pid'])
                                time.sleep(2)
                                
                                # 갱신
                                self.ports_info = self.get_open_ports()
                                self.display_ports_with_actions(self.ports_info)
                                last_update = time.time()
                                countdown = interval
                        else:
                            console.print(f"\n[red]Invalid selection: {user_input}[/red]")
                            time.sleep(1)
                            self.display_ports_with_actions(self.ports_info)
                            countdown = interval
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")
        finally:
            # 터미널 설정 복원 (터미널 환경에서만)
            if old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except:
                    pass
            console.print("\n")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Interactive Port Monitor with Kill Feature")
    parser.add_argument('-t', '--interval', type=int, default=60, help='Refresh interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    monitor = InteractivePortMonitor()
    
    # 초기 표시
    ports_info = monitor.get_open_ports()
    monitor.ports_info = ports_info
    monitor.display_ports_with_actions(ports_info)
    
    # 대화형 모니터링 시작
    monitor.interactive_monitor(args.interval)


if __name__ == "__main__":
    main()