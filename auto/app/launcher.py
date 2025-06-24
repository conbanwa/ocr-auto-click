import os
import subprocess
import time
from logging import info, error, debug, basicConfig, DEBUG
from typing import Union, Optional, List, Tuple

import psutil

# Configure logging
basicConfig(
    level=DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        # logging.FileHandler('launcher.log'),
        # logging.StreamHandler()
    ]
)


def launch_application(
        app_path: Union[str, os.PathLike],
        args: Optional[List[str]] = None,
        working_dir: Optional[Union[str, os.PathLike]] = None,
        show_console: bool = False,
        admin: bool = False
) -> Tuple[bool, Optional[List[psutil.Process]]]:
    """
    Launch an application and return all related process objects.

    Args:
        app_path: Full path to the executable file.
        args: List of command-line arguments.
        working_dir: Working directory for the process.
        show_console: Whether to show the console window.
        admin: Whether to run as administrator (Windows only).

    Returns:
        Tuple[bool, Optional[List[psutil.Process]]]: Success status and list of process objects.
    """
    debug(f"Launching: {app_path} with args: {args}")

    if not os.path.exists(app_path):
        error(f"Path does not exist: {app_path}")
        return False, None

    args = args or []
    working_dir = working_dir or os.path.dirname(app_path)
    cmd = [app_path] + args

    process = subprocess.Popen(
        cmd,
        cwd=working_dir,
        shell=admin if os.name == 'nt' else False,
        creationflags=0 if show_console else subprocess.CREATE_NO_WINDOW
    )
    if not psutil.pid_exists(process.pid):
        error(f"Failed to start process: {app_path} (PID {process.pid} not found)")
        return False, None

    # Wait longer to allow child processes to spawn
    time.sleep(1.0)
    if not psutil.pid_exists(process.pid):
        error(f"Initial process terminated prematurely: PID {process.pid}")
        # Attempt to find related processes by name
        process_name = os.path.basename(app_path).lower()
        processes = []
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.name().lower() == process_name:
                processes.append(proc)
        if not processes:
            error(f"No related processes found for {app_path}")
            return False, None
        for proc in processes:
            info(f"Started PID {proc.pid}: {proc.name()}")
        return True, processes

    ps_proc = psutil.Process(process.pid)
    # Collect main process and all child processes
    processes = [ps_proc] + ps_proc.children(recursive=True)
    for proc in processes:
        info(f"Started PID {proc.pid}: {proc.name()}")
    return True, processes


def terminate_application(
        target: Union[List[psutil.Process], psutil.Process, int, str],
        force: bool = False,
        timeout: int = 3,
        check_interval: float = 0.1
) -> bool:
    """
    Terminate an application and verify if all related processes exited.

    Args:
        target: List of process objects, single process, PID, or process name.
        force: Whether to attempt forceful termination if safe termination fails.
        timeout: Total timeout for termination (seconds).
        check_interval: Interval to check process status (seconds).

    Returns:
        bool: True if all terminations were successful, False otherwise.
    """

    def verify_terminated(pid: int) -> bool:
        """Verify if a process has terminated."""
        if psutil.pid_exists(pid):
            return False
        return True

    def log_terminate(pid: int, name: str, method: str):
        """Log termination attempt."""
        info(f"Terminating PID {pid} ({name}) with {method}")

    def log_failure(proc: psutil.Process):
        """Log detailed failure reasons."""
        pid = proc.pid
        name = proc.name()
        status = proc.status()
        parent_pid = proc.ppid()
        parent = psutil.Process(parent_pid) if psutil.pid_exists(parent_pid) else None
        parent_name = parent.name() if parent else "Unknown"
        error(f"Failed to terminate PID {pid} ({name})")
        error(f"Process status: {status}")
        error(f"Parent process: {parent_name} (PID: {parent_pid})")
        error(f"Memory usage: {proc.memory_info().rss / 1024 / 1024:.2f} MB")
        error(f"CPU usage: {proc.cpu_percent(interval=0.1):.2f}%")
        if status in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]:
            error("Process is in zombie or dead state")
        elif status == psutil.STATUS_RUNNING:
            error("Process is still running, possibly hung or locked")

    # Handle list of processes first
    if isinstance(target, list):
        # Check if all elements have required Process attributes (pid, name)
        if all(hasattr(p, 'pid') and hasattr(p, 'name') for p in target):
            debug(f"Terminating {len(target)} processes")
            success = True
            for proc in target:
                if not _safe_terminate(
                        proc,
                        force,
                        timeout,
                        check_interval,
                        verify_terminated,
                        log_terminate,
                        log_failure
                ):
                    success = False
            return success

    # Handle process name input
    if isinstance(target, str):
        debug(f"Terminating by name: {target}")
        success = True
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.name().lower() == target.lower():
                if not _safe_terminate(
                        proc,
                        force,
                        timeout,
                        check_interval,
                        verify_terminated,
                        log_terminate,
                        log_failure
                ):
                    success = False
        return success

    # Handle single PID or process object
    if isinstance(target, int) or (hasattr(target, 'pid') and hasattr(target, 'name')):
        pid = target.pid if hasattr(target, 'pid') else target
        if not psutil.pid_exists(pid):
            error(f"Process does not exist: {pid}")
            return False
        proc = psutil.Process(pid) if isinstance(target, int) else target
        return _safe_terminate(
            proc,
            force,
            timeout,
            check_interval,
            verify_terminated,
            log_terminate,
            log_failure
        )

    error(f"Invalid target type: {type(target)}")
    return False


def _safe_terminate(
        proc: psutil.Process,
        force: bool,
        timeout: float,
        check_interval: float,
        verify_func: callable,
        log_func: callable,
        failure_func: callable
) -> bool:
    """
    Safely terminate a process, always attempting safe termination first.

    Args:
        proc: Process object to terminate.
        force: Whether to attempt forceful termination if safe termination fails.
        timeout: Total timeout for termination.
        check_interval: Interval to check process status.
        verify_func: Function to verify termination.
        log_func: Function to log termination attempts.
        failure_func: Function to log failure reasons.

    Returns:
        bool: True if terminated, False otherwise.
    """
    pid = proc.pid
    name = proc.name()

    if not psutil.pid_exists(pid):
        debug(f"Already terminated: PID {pid}")
        return True

    # Always attempt safe termination first
    log_func(pid, name, "terminate()")
    proc.terminate()

    start_time = time.time()
    while time.time() - start_time < timeout:
        if verify_func(pid):
            debug(f"Verify terminated: PID {pid}")
            return True
        time.sleep(check_interval)

    # If safe termination failed and force is True, attempt forceful termination
    if force:
        log_func(pid, name, "kill()")
        proc.kill()
        time.sleep(0.5)
        if verify_func(pid):
            debug(f"Verify killed: PID {pid}")
            return True

    # Log failure if termination (safe or forced) didn't work
    failure_func(proc)
    return False


if __name__ == "__main__":
    def chrome():
        """Main function to demonstrate program launch and termination."""
        executable_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        info(f"Starting launcher for: {executable_path}")

        success, incognito = launch_application(
            executable_path,
            args=["--incognito"],
            show_console=False
        )
        if not success:
            error("Failed to launch program, exiting")
            return

        success, processes = launch_application(
            executable_path,
            show_console=True,
        )
        if not success:
            error("Failed to launch program, exiting")
            return

        debug("Waiting 3 seconds before attempting to close")
        time.sleep(1)

        success = terminate_application(incognito, force=True)
        if not success:
            error("Program termination failed, see logs for details")
            terminate_application("chrome.exe", force=True)
        else:
            info("Program terminated successfully")
        time.sleep(3)
        success = terminate_application(processes, force=True)
        if not success:
            error("Program termination failed, see logs for details")
            terminate_application("chrome.exe", force=True)
        else:
            info("Program terminated successfully")


    def notepad():
        app_path = r"C:\Windows\System32\notepad.exe"
        args = [r"C:\temp\notes.txt"]
        success, processes = launch_application(app_path, args=args)
        time.sleep(1)

        success = terminate_application(processes, force=True)
        if not success:
            error("Program termination failed, see logs for details")
            terminate_application("notepad.exe", force=True)
        else:
            info("Program terminated successfully")

    def powershell():
        debug("Testing PowerShell launch with admin")
        app_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

        if not os.path.exists(app_path):
            error(f"PowerShell executable not found: {app_path}")

        success, processes = launch_application(app_path, admin=True, show_console=True)
    notepad()
    powershell()
