import os
import subprocess
import getpass
from pathlib import Path

def install_systemd_service():
    username = getpass.getuser()
    service_name = "clipthread-tkinter-ui"
    
    # Get package directory
    pkg_dir = Path(__file__).parent
    service_src = pkg_dir / f"{service_name}.service"
    
    # Copy service file
    subprocess.run(['sudo', 'cp', str(service_src), f'/etc/systemd/system/{service_name}@{username}.service'])
    
    # Reload systemd
    subprocess.run(['sudo', 'systemctl', 'daemon-reload'])
    
    # Enable and start for current user
    subprocess.run(['sudo', 'systemctl', 'enable', f'{service_name}@{username}'])
    subprocess.run(['sudo', 'systemctl', 'start', f'{service_name}@{username}'])

if __name__ == "__main__":
    install_systemd_service()