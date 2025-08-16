#!/usr/bin/env python3
"""
향상된 포트 모니터링 시스템
3000-9000 사이의 TCP 포트를 모니터링하고 프로세스를 관리합니다.
폴더명을 정확히 표시하고 즉시 kill 가능한 인터페이스 제공
"""

import subprocess
import re
import os
import sys
import psutil
import signal
from typing import List, Dict, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint
from rich.layout import Layout
from rich.live import Live
import time

console = Console()

class EnhancedPortMonitor:
    def __init__(self):
        self.port_range = (3000, 9000)
        self.sudo_password = "ak@5406454"
        
    def get_open_ports(self) -> List[Dict]:
        """열려있는 포트 정보 수집"""
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
            console.print(f"[red]Error: {e}[/red]")
            return []
    
    def get_process_details(self, pid: int) -> Dict:
        """PID로 프로세스 상세 정보 가져오기"""
        try:
            process = psutil.Process(pid)
            
            # 명령줄 인자 가져오기
            cmdline = process.cmdline()
            # 너무 긴 경우 처음 몇 개만
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
        
        # /home/nmsglobal/DEVEL/ 다음의 폴더명 추출
        if '/DEVEL/' in cwd:
            parts = cwd.split('/DEVEL/')
            if len(parts) > 1:
                project_parts = parts[1].split('/')
                if project_parts[0]:
                    return project_parts[0]
        
        # 마지막 폴더명 반환
        return Path(cwd).name if cwd else 'Unknown'
    
    def display_ports_with_actions(self, ports_info: List[Dict]):
        """포트 정보를 테이블로 표시 (액션 번호 포함)"""
        table = Table(title="🔍 Enhanced Port Monitor (3000-9000)", show_header=True, header_style="bold magenta")
        table.add_column("No.", style="bold white", width=5)
        table.add_column("Port", style="cyan", width=8)
        table.add_column("Project Folder", style="bold green", width=35)
        table.add_column("PID", style="yellow", width=8)
        table.add_column("Process", style="blue", width=25)
        table.add_column("Memory", style="red", width=10)
        table.add_column("User", style="magenta", width=12)
        
        for idx, port in enumerate(sorted(ports_info, key=lambda x: x['port']), 1):
            # 프로젝트 폴더 하이라이트
            if port['project_folder'] != 'Unknown':
                folder_display = f"[bold green]{port['project_folder']}[/bold green]"
            else:
                folder_display = "[dim]Unknown[/dim]"
            
            table.add_row(
                str(idx),
                str(port['port']),
                folder_display,
                str(port['pid']) if port['pid'] else "N/A",
                port['process_name'][:25],
                str(port['memory']),
                port['user']
            )
        
        console.print(table)
        console.print(f"\n[bold]Total ports in use:[/bold] {len(ports_info)}")
        return ports_info
    
    def kill_process(self, pid: int, force: bool = False) -> bool:
        """프로세스 종료"""
        try:
            if force:
                signal_type = signal.SIGKILL
                signal_name = "SIGKILL"
            else:
                signal_type = signal.SIGTERM
                signal_name = "SIGTERM"
            
            try:
                os.kill(pid, signal_type)
                console.print(f"[green]✓ Sent {signal_name} to process {pid}[/green]")
                return True
            except PermissionError:
                # sudo로 재시도
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
    
    def interactive_session(self):
        """향상된 대화형 세션"""
        while True:
            console.clear()
            console.print(Panel("🚀 Enhanced Port Monitor - Interactive Mode", style="bold blue"))
            
            # 포트 정보 수집 및 표시
            ports_info = self.get_open_ports()
            
            if not ports_info:
                console.print("[yellow]No ports found in range 3000-9000[/yellow]")
                if Confirm.ask("\nRefresh?", default=True):
                    continue
                else:
                    break
            
            # 번호와 함께 표시
            indexed_ports = self.display_ports_with_actions(ports_info)
            
            # 옵션 메뉴
            console.print("\n[bold cyan]Actions:[/bold cyan]")
            console.print("[bold]Enter number (1-{}) to manage process[/bold]".format(len(indexed_ports)))
            console.print("[bold]R[/bold] - Refresh list")
            console.print("[bold]A[/bold] - Kill all processes")
            console.print("[bold]E[/bold] - Export to file")
            console.print("[bold]Q[/bold] - Quit")
            
            choice = Prompt.ask("\n[bold yellow]Select action[/bold yellow]").strip().upper()
            
            if choice == 'R':
                continue
            elif choice == 'Q':
                console.print("[green]Goodbye! 👋[/green]")
                break
            elif choice == 'E':
                self.export_to_file(indexed_ports)
                Prompt.ask("\nPress Enter to continue")
            elif choice == 'A':
                if Confirm.ask("[bold red]Kill ALL processes?[/bold red]", default=False):
                    for port in indexed_ports:
                        if port['pid']:
                            self.kill_process(port['pid'])
                    time.sleep(2)
                    console.print("[green]All processes terminated[/green]")
                    Prompt.ask("\nPress Enter to continue")
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(indexed_ports):
                    sorted_ports = sorted(indexed_ports, key=lambda x: x['port'])
                    selected = sorted_ports[idx]
                    
                    # 프로세스 상세 정보 표시
                    console.print(f"\n[bold]Process Details:[/bold]")
                    console.print(f"  Port: {selected['port']}")
                    console.print(f"  PID: {selected['pid']}")
                    console.print(f"  Process: {selected['process_name']}")
                    console.print(f"  Project: [bold green]{selected['project_folder']}[/bold green]")
                    console.print(f"  Path: {selected['cwd']}")
                    console.print(f"  Memory: {selected['memory']}")
                    console.print(f"  User: {selected['user']}")
                    
                    # 액션 선택
                    console.print("\n[bold]Actions:[/bold]")
                    console.print("1. Kill gracefully (SIGTERM)")
                    console.print("2. Force kill (SIGKILL)")
                    console.print("3. Cancel")
                    
                    action = Prompt.ask("Select", choices=["1", "2", "3"], default="3")
                    
                    if action == "1":
                        if selected['pid']:
                            self.kill_process(selected['pid'], force=False)
                            time.sleep(2)
                    elif action == "2":
                        if selected['pid']:
                            self.kill_process(selected['pid'], force=True)
                            time.sleep(1)
                    
                    if action in ["1", "2"]:
                        console.print("\n[green]Process terminated. Refreshing...[/green]")
                        time.sleep(1)
                else:
                    console.print("[red]Invalid selection[/red]")
                    Prompt.ask("\nPress Enter to continue")
    
    def export_to_file(self, ports_info: List[Dict]):
        """포트 정보를 파일로 내보내기"""
        timestamp = subprocess.check_output('date +%Y%m%d_%H%M%S', shell=True).decode().strip()
        filename = f"port_monitor_report_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("Enhanced Port Monitor Report\n")
            f.write("=" * 80 + "\n")
            f.write(f"Date: {subprocess.check_output('date', shell=True).decode().strip()}\n")
            f.write(f"Port Range: {self.port_range[0]}-{self.port_range[1]}\n")
            f.write("=" * 80 + "\n\n")
            
            for port in sorted(ports_info, key=lambda x: x['port']):
                f.write(f"Port: {port['port']}\n")
                f.write(f"  Protocol: {port['protocol']}\n")
                f.write(f"  PID: {port['pid']}\n")
                f.write(f"  Process: {port['process_name']}\n")
                f.write(f"  Project Folder: {port['project_folder']}\n")
                f.write(f"  Full Path: {port['cwd']}\n")
                f.write(f"  Command: {port['cmdline']}\n")
                f.write(f"  Memory: {port['memory']}\n")
                f.write(f"  User: {port['user']}\n")
                f.write("-" * 40 + "\n")
        
        console.print(f"[green]✓ Report saved to {filename}[/green]")
    
    def quick_view(self, interactive=True):
        """빠른 보기 모드 (번호와 함께)"""
        ports_info = self.get_open_ports()
        
        if not ports_info:
            console.print("[yellow]No ports found in range 3000-9000[/yellow]")
            return
        
        self.display_ports_with_actions(ports_info)
        
        # 터미널 모드에서만 대화형 액션 제공
        if not interactive or not sys.stdin.isatty():
            return
            
        # 빠른 액션
        console.print("\n[bold cyan]Quick Actions:[/bold cyan]")
        console.print("Enter port number or process number (1-{}) to kill, or 'q' to quit".format(len(ports_info)))
        
        choice = Prompt.ask("\n[bold yellow]Action[/bold yellow]", default="q").strip().lower()
        
        if choice == 'q':
            return
        elif choice.isdigit():
            value = int(choice)
            
            # 번호로 선택 (1-N)
            if 1 <= value <= len(ports_info):
                sorted_ports = sorted(ports_info, key=lambda x: x['port'])
                selected = sorted_ports[value - 1]
                if selected['pid']:
                    project = selected['project_folder']
                    if Confirm.ask(f"Kill [{project}] on port {selected['port']} (PID: {selected['pid']})?"):
                        self.kill_process(selected['pid'])
                        console.print("[green]Process terminated[/green]")
            # 포트 번호로 선택
            elif 3000 <= value <= 9000:
                port_info = next((p for p in ports_info if p['port'] == value), None)
                if port_info and port_info['pid']:
                    project = port_info['project_folder']
                    if Confirm.ask(f"Kill [{project}] on port {value} (PID: {port_info['pid']})?"):
                        self.kill_process(port_info['pid'])
                        console.print("[green]Process terminated[/green]")
                else:
                    console.print(f"[red]No process found on port {value}[/red]")
    
    def auto_monitor(self, interval=60):
        """자동 모니터링 모드 (기본 60초 간격)"""
        console.print(Panel(f"🔄 Auto Monitor Mode - Refreshing every {interval} seconds", style="bold cyan"))
        console.print("Press Ctrl+C to stop monitoring\n")
        
        try:
            while True:
                # 현재 시간 표시
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                console.print(f"\n[dim]Last updated: {timestamp}[/dim]")
                
                # 포트 정보 수집 및 표시
                ports_info = self.get_open_ports()
                
                if not ports_info:
                    console.print("[yellow]No ports found in range 3000-9000[/yellow]")
                else:
                    self.display_ports_with_actions(ports_info)
                
                # 다음 업데이트까지 대기
                console.print(f"\n[dim]Next update in {interval} seconds... (Press Ctrl+C to stop)[/dim]")
                time.sleep(interval)
                
                # 화면 클리어 (선택적)
                console.clear()
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped[/yellow]")
            return


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Port Monitor (3000-9000)")
    parser.add_argument('-i', '--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('-q', '--quick', action='store_true', help='Quick view with kill option')
    parser.add_argument('-m', '--monitor', action='store_true', help='Auto monitor mode (1 minute interval)')
    parser.add_argument('-t', '--interval', type=int, default=60, help='Monitor interval in seconds (default: 60)')
    
    args = parser.parse_args()
    
    monitor = EnhancedPortMonitor()
    
    try:
        if args.monitor:
            monitor.auto_monitor(args.interval)
        elif args.interactive:
            monitor.interactive_session()
        elif args.quick:
            monitor.quick_view()
        else:
            # 기본: quick view 모드
            monitor.quick_view()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()