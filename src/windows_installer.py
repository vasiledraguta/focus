"""Windows Task Scheduler installer for Focus Blocker."""

import ctypes
import subprocess
import sys
from pathlib import Path

TASK_NAME = "FocusBlocker"


def is_admin() -> bool:
    """Check if running with Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_python_path() -> str:
    """Get the full path to the current Python interpreter."""
    return sys.executable


def get_project_path() -> Path:
    """Get the project root directory (where main.py lives)."""
    return Path(__file__).parent.resolve()


def create_task_xml() -> str:
    """Generate the Task Scheduler XML content."""
    python_path = get_python_path()
    project_path = get_project_path()
    main_script = project_path / "main.py"

    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Focus Blocker DNS Server - Blocks distracting websites</Description>
  </RegistrationInfo>
  <Triggers>
    <BootTrigger>
      <Enabled>true</Enabled>
    </BootTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>S-1-5-18</UserId>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{python_path}"</Command>
      <Arguments>"{main_script}" start</Arguments>
      <WorkingDirectory>{project_path}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""


def disable_ipv6() -> None:
    """Disable IPv6 to prevent DNS bypass."""
    print("Disabling IPv6 to prevent DNS bypass...")
    subprocess.run(
        ["powershell", "-Command", "Disable-NetAdapterBinding -Name 'Ethernet' -ComponentID ms_tcpip6"],
        capture_output=True
    )
    subprocess.run(
        ["powershell", "-Command", "Disable-NetAdapterBinding -Name 'Wi-Fi' -ComponentID ms_tcpip6"],
        capture_output=True
    )


def enable_ipv6() -> None:
    """Re-enable IPv6."""
    print("Re-enabling IPv6...")
    subprocess.run(
        ["powershell", "-Command", "Enable-NetAdapterBinding -Name 'Ethernet' -ComponentID ms_tcpip6"],
        capture_output=True
    )
    subprocess.run(
        ["powershell", "-Command", "Enable-NetAdapterBinding -Name 'Wi-Fi' -ComponentID ms_tcpip6"],
        capture_output=True
    )


def install() -> bool:
    """Install the Windows Task Scheduler task."""
    if not is_admin():
        print("Error: Installation requires Administrator privileges.")
        return False

    # Remove existing task if present
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True
    )

    # Disable IPv6 to prevent DNS bypass
    disable_ipv6()

    # Create temporary XML file
    project_path = get_project_path()
    xml_path = project_path / "focus_task.xml"
    
    try:
        xml_path.write_text(create_task_xml(), encoding="utf-16")
        
        # Create the task
        result = subprocess.run(
            ["schtasks", "/Create", "/TN", TASK_NAME, "/XML", str(xml_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"Error creating task: {result.stderr}")
            return False
        
        # Start the task immediately
        subprocess.run(
            ["schtasks", "/Run", "/TN", TASK_NAME],
            capture_output=True
        )
        
        print("Focus Blocker installed successfully!")
        print("\nThe DNS server will start automatically on boot.")
        return True
        
    finally:
        # Clean up XML file
        if xml_path.exists():
            xml_path.unlink()


def uninstall() -> bool:
    """Uninstall the Windows Task Scheduler task."""
    if not is_admin():
        print("Error: Uninstallation requires Administrator privileges.")
        return False

    # Stop the task
    subprocess.run(
        ["schtasks", "/End", "/TN", TASK_NAME],
        capture_output=True
    )

    # Delete the task
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0 and "cannot find" not in result.stderr.lower():
        print(f"Error removing task: {result.stderr}")
        return False

    # Reset DNS settings
    print("Resetting DNS settings to automatic...")
    subprocess.run(
        ["netsh", "interface", "ip", "set", "dns", "Wi-Fi", "dhcp"],
        capture_output=True
    )
    subprocess.run(
        ["netsh", "interface", "ip", "set", "dns", "Ethernet", "dhcp"],
        capture_output=True
    )

    # Re-enable IPv6
    enable_ipv6()

    print("Focus Blocker uninstalled successfully.")
    return True


def is_installed() -> bool:
    """Check if Focus Blocker is installed as a scheduled task."""
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME],
        capture_output=True
    )
    return result.returncode == 0


def is_running() -> bool:
    """Check if the Focus Blocker task is running."""
    result = subprocess.run(
        ["schtasks", "/Query", "/TN", TASK_NAME, "/V", "/FO", "LIST"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        return False
    return "Running" in result.stdout


def get_status() -> dict:
    """Get the current status of Focus Blocker."""
    return {
        "installed": is_installed(),
        "running": is_running(),
        "task_name": TASK_NAME,
    }
