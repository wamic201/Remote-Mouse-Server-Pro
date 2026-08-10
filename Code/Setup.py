import subprocess
import sys
import importlib.util

def install_package(package_name, import_name=None):
    """
    Checks if a package is installed. If not, installs it.
    """
    if import_name is None:
        import_name = package_name.replace('-', '_')

    print(f"Checking for {package_name}...")
    
    if importlib.util.find_spec(import_name) is None:
        print(f"{package_name} not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"Successfully installed {package_name}.\n")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {package_name}. Error: {e}")
            sys.exit(1)
    else:
        print(f"{package_name} is already installed.\n")

def main():
    print("="*50)
    print("Remote Trackpad Dependency Installer")
    print("="*50)
    
    # List of required packages
    # (Package Name, Import Name if different)
    dependencies = [
        ("Flask", "flask"),
        ("flask-socketio", "flask_socketio"),
        ("eventlet", "eventlet")
    ]