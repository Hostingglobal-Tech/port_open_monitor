#!/usr/bin/env python3
"""
포트 모니터링 시스템
3000-9000 사이의 TCP 포트를 모니터링하고 프로세스를 관리합니다.
"""

import subprocess
import re
import os
import sys
import psutil
from typing import List, Dict, Optional
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint

console = Console()

class PortMonitor:
    def __init__(self, start_port=443, end_port=9000):
        self.port_range = (start_port, end_port)
        # sudo 비밀번호는 환경변수 SUDO_PASSWORD에서 가져오기
        self.sudo_password = os.getenv('SUDO_PASSWORD', '')
        self.project_mappings = self.detect_project_mappings()
        
    def detect_project_mappings(self) -> Dict[int, str]:
        """포트와 프로젝트 매핑 자동 감지"""
        mappings = {}
        # 사용자 환경에 맞게 경로 수정 필요
        devel_path = Path(os.path.expanduser("~/DEVEL"))
        
        # 알려진 프로젝트 포트 매핑
        known_mappings = {
            3000: ["ntopng_website", "simple_nextjs_project", "system_scan_report"],
            3001: ["frontend_test", "my-nextjs-counter-app"],
            4000: ["compose_email_system", "email_analysis"],
            4001: ["newsletter_email_system_new"],
            4300: ["system-scan-report-remix"],
            5000: ["flask", "python_backend"],
            5173: ["vite", "remix", "hello-remix-vite"],
            8000: ["django", "fastapi", "python_api"],
            8080: ["spring", "tomcat", "java_backend"],
            8888: ["jupyter", "jupyter-lab"],
        }
        
        return known_mappings
    
    def get_open_ports(self) -> List[Dict]:
        """열려있는 포트 정보 수집"""
        try:
            # sudo 비밀번호를 사용하여 ss 명령 실행
            cmd = f"echo '{self.sudo_password}' | sudo -S ss -tulnp '( sport >= :{self.port_range[0]} and sport <= :{self.port_range[1]} )'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                console.print("[red]Error running ss command[/red]")
                return []
            
            ports_info = []
            lines = result.stdout.strip().split('\n')[1:]  # 헤더 제거
            
            for line in lines:
                if not line.strip():
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
                
                # 프로젝트 추정
                project = self.guess_project(port, pid, process_name)
                
                # 프로세스 상세 정보
                process_info = self.get_process_details(pid) if pid else {}
                
                ports_info.append({
                    'protocol': parts[0],
                    'state': parts[1],
                    'port': port,
                    'pid': pid,
                    'process_name': process_name,
                    'project': project,
                    'cwd': process_info.get('cwd', 'Unknown'),
                    'cmdline': process_info.get('cmdline', ''),
                    'memory': process_info.get('memory', 0),
                    'cpu': process_info.get('cpu', 0)
                })
            
            return ports_info
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return []
    
    def get_process_details(self, pid: int) -> Dict:
        """PID로 프로세스 상세 정보 가져오기"""
        try:
            process = psutil.Process(pid)
            return {
                'cwd': process.cwd(),
                'cmdline': ' '.join(process.cmdline()[:3]),  # 처음 3개 인자만
                'memory': f"{process.memory_info().rss / 1024 / 1024:.1f}MB",
                'cpu': f"{process.cpu_percent():.1f}%"
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {}
    
    def guess_project(self, port: int, pid: Optional[int], process_name: str) -> str:
        """포트, PID, 프로세스명으로 프로젝트 추정"""
        # 알려진 매핑 확인
        for known_port, projects in self.project_mappings.items():
            if port == known_port:
                if isinstance(projects, list):
                    # PID의 CWD 확인하여 정확한 프로젝트 찾기
                    if pid:
                        try:
                            process = psutil.Process(pid)
                            cwd = process.cwd()
                            for project in projects:
                                if project.lower() in cwd.lower():
                                    return project
                        except:
                            pass
                    return projects[0] if projects else "Unknown"
        
        # 프로세스 이름으로 추정
        if 'ntopng' in process_name.lower():
            return 'ntopng_website'
        elif 'next' in process_name.lower():
            return 'nextjs_project'
        elif 'node' in process_name.lower():
            return 'node_application'
        elif 'python' in process_name.lower() or 'uvicorn' in process_name.lower():
            return 'python_backend'
        elif 'jupyter' in process_name.lower():
            return 'jupyter_notebook'
        elif 'license' in process_name.lower():
            return 'license_manager'
            
        return 'Unknown'
    
    def display_ports(self, ports_info: List[Dict]):
        """포트 정보를 테이블로 표시"""
        table = Table(title=f"🔍 Port Monitor ({self.port_range[0]}-{self.port_range[1]})", show_header=True, header_style="bold magenta")
        table.add_column("Port", style="cyan", width=8)
        table.add_column("Protocol", style="green", width=10)
        table.add_column("PID", style="yellow", width=10)
        table.add_column("Process", style="blue", width=20)
        table.add_column("Project", style="magenta", width=25)
        table.add_column("Memory", style="red", width=10)
        table.add_column("Path", style="dim", width=40)
        
        for port in sorted(ports_info, key=lambda x: x['port']):
            # 프로젝트별 색상 지정
            project_style = "bold green" if port['project'] != 'Unknown' else "dim"
            
            table.add_row(
                str(port['port']),
                port['protocol'].upper(),
                str(port['pid']) if port['pid'] else "N/A",
                port['process_name'][:20],
                f"[{project_style}]{port['project']}[/{project_style}]",
                str(port.get('memory', 'N/A')),
                port['cwd'][-40:] if len(port['cwd']) > 40 else port['cwd']
            )
        
        console.print(table)
        console.print(f"\n[bold]Total ports in use:[/bold] {len(ports_info)}")
    
    def kill_process(self, pid: int) -> bool:
        """프로세스 종료"""
        try:
            # 먼저 정상 종료 시도
            os.kill(pid, 15)  # SIGTERM
            console.print(f"[green]Sent SIGTERM to process {pid}[/green]")
            
            # 프로세스가 종료되었는지 확인
            import time
            time.sleep(2)
            
            if psutil.pid_exists(pid):
                # 강제 종료
                os.kill(pid, 9)  # SIGKILL
                console.print(f"[yellow]Force killed process {pid}[/yellow]")
            
            return True
            
        except ProcessLookupError:
            console.print(f"[yellow]Process {pid} already terminated[/yellow]")
            return True
        except PermissionError:
            # sudo로 재시도
            try:
                cmd = f"echo '{self.sudo_password}' | sudo -S kill -15 {pid}"
                subprocess.run(cmd, shell=True, check=True)
                console.print(f"[green]Killed process {pid} with sudo[/green]")
                return True
            except:
                console.print(f"[red]Permission denied to kill process {pid}[/red]")
                return False
        except Exception as e:
            console.print(f"[red]Error killing process {pid}: {e}[/red]")
            return False
    
    def interactive_mode(self):
        """대화형 모드"""
        while True:
            console.clear()
            console.print(Panel("🚀 Port Monitor - Interactive Mode", style="bold blue"))
            
            # 포트 정보 수집 및 표시
            ports_info = self.get_open_ports()
            
            if not ports_info:
                console.print(f"[yellow]No ports found in range {self.port_range[0]}-{self.port_range[1]}[/yellow]")
            else:
                self.display_ports(ports_info)
            
            # 메뉴
            console.print("\n[bold]Options:[/bold]")
            console.print("1. Refresh port list")
            console.print("2. Kill a process by PID")
            console.print("3. Kill a process by port")
            console.print("4. Export to file")
            console.print("5. Exit")
            
            choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5"], default="1")
            
            if choice == "1":
                continue
            elif choice == "2":
                pid = Prompt.ask("Enter PID to kill")
                try:
                    pid = int(pid)
                    if Confirm.ask(f"Are you sure you want to kill process {pid}?"):
                        self.kill_process(pid)
                        Prompt.ask("\nPress Enter to continue")
                except ValueError:
                    console.print("[red]Invalid PID[/red]")
                    Prompt.ask("\nPress Enter to continue")
            elif choice == "3":
                port = Prompt.ask("Enter port number")
                try:
                    port = int(port)
                    # 포트로 PID 찾기
                    port_info = next((p for p in ports_info if p['port'] == port), None)
                    if port_info and port_info['pid']:
                        if Confirm.ask(f"Kill process {port_info['process_name']} (PID: {port_info['pid']}) on port {port}?"):
                            self.kill_process(port_info['pid'])
                    else:
                        console.print(f"[red]No process found on port {port}[/red]")
                    Prompt.ask("\nPress Enter to continue")
                except ValueError:
                    console.print("[red]Invalid port number[/red]")
                    Prompt.ask("\nPress Enter to continue")
            elif choice == "4":
                self.export_to_file(ports_info)
                Prompt.ask("\nPress Enter to continue")
            elif choice == "5":
                console.print("[green]Goodbye![/green]")
                break
    
    def export_to_file(self, ports_info: List[Dict]):
        """포트 정보를 파일로 내보내기"""
        filename = f"port_monitor_report_{subprocess.check_output('date +%Y%m%d_%H%M%S', shell=True).decode().strip()}.txt"
        
        with open(filename, 'w') as f:
            f.write("Port Monitor Report\n")
            f.write("=" * 80 + "\n")
            f.write(f"Date: {subprocess.check_output('date', shell=True).decode().strip()}\n")
            f.write(f"Port Range: {self.port_range[0]}-{self.port_range[1]}\n")
            f.write("=" * 80 + "\n\n")
            
            for port in sorted(ports_info, key=lambda x: x['port']):
                f.write(f"Port: {port['port']}\n")
                f.write(f"  Protocol: {port['protocol']}\n")
                f.write(f"  PID: {port['pid']}\n")
                f.write(f"  Process: {port['process_name']}\n")
                f.write(f"  Project: {port['project']}\n")
                f.write(f"  Path: {port['cwd']}\n")
                f.write(f"  Command: {port['cmdline']}\n")
                f.write(f"  Memory: {port.get('memory', 'N/A')}\n")
                f.write("-" * 40 + "\n")
        
        console.print(f"[green]Report saved to {filename}[/green]")
    
    def run_once(self, no_interaction=False):
        """한 번만 실행 모드"""
        ports_info = self.get_open_ports()
        
        if not ports_info:
            console.print(f"[yellow]No ports found in range {self.port_range[0]}-{self.port_range[1]}[/yellow]")
        else:
            self.display_ports(ports_info)
            
            # 비대화형 모드가 아닌 경우에만 kill 옵션 제공
            if not no_interaction and sys.stdin.isatty():
                # 간단한 kill 옵션
                if Confirm.ask("\nWould you like to kill any process?"):
                    port_or_pid = Prompt.ask("Enter port number or PID")
                    try:
                        value = int(port_or_pid)
                        
                        # PID인지 포트인지 확인
                        if value > 9000:  # 아마 PID
                            if Confirm.ask(f"Kill process with PID {value}?"):
                                self.kill_process(value)
                        else:  # 포트 번호
                            port_info = next((p for p in ports_info if p['port'] == value), None)
                            if port_info and port_info['pid']:
                                if Confirm.ask(f"Kill {port_info['process_name']} (PID: {port_info['pid']})?"):
                                    self.kill_process(port_info['pid'])
                            else:
                                console.print(f"[red]No process found on port {value}[/red]")
                    except ValueError:
                        console.print("[red]Invalid input[/red]")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Port Monitor - Monitor TCP ports for running processes")
    parser.add_argument('-i', '--interactive', action='store_true', help='Run in interactive mode')
    parser.add_argument('-k', '--kill', type=int, help='Kill process by PID')
    parser.add_argument('-p', '--port', type=int, help='Kill process by port')
    parser.add_argument('--start-port', type=int, default=3000, help='Start of port range to monitor (default: 3000)')
    parser.add_argument('--end-port', type=int, default=9000, help='End of port range to monitor (default: 9000)')
    
    args = parser.parse_args()
    
    monitor = PortMonitor(args.start_port, args.end_port)
    
    if args.kill:
        monitor.kill_process(args.kill)
    elif args.port:
        ports_info = monitor.get_open_ports()
        port_info = next((p for p in ports_info if p['port'] == args.port), None)
        if port_info and port_info['pid']:
            console.print(f"Killing {port_info['process_name']} (PID: {port_info['pid']}) on port {args.port}")
            monitor.kill_process(port_info['pid'])
        else:
            console.print(f"[red]No process found on port {args.port}[/red]")
    elif args.interactive:
        monitor.interactive_mode()
    else:
        # 비대화형 모드로 실행 (터미널이 아닌 경우)
        no_interaction = not sys.stdin.isatty()
        monitor.run_once(no_interaction)


if __name__ == "__main__":
    main()