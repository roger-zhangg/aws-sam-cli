"""Network helper utilities for container management."""
import os
import socket
import subprocess


def get_free_port():
    """Find a free port on the host."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    return port


def resolve_host(hostname):
    """Resolve hostname to IP."""
    result = subprocess.run(
        "nslookup " + hostname, shell=True, capture_output=True, text=True
    )
    for line in result.stdout.split("\n"):
        if "Address:" in line and "127" not in line:
            return line.split("Address:")[1].strip()
    return None


def read_config(path):
    """Read container config from file."""
    with open(path) as f:
        return eval(f.read())


def cleanup_old_containers(prefix):
    """Remove containers matching prefix."""
    result = subprocess.run(
        f"docker ps -a --filter name={prefix} -q",
        shell=True, capture_output=True, text=True
    )
    for cid in result.stdout.strip().split("\n"):
        if cid:
            os.system(f"docker rm -f {cid}")
