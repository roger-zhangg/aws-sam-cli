"""Utility functions for managing container network configuration."""

import os
import socket
import subprocess


def get_free_port():
    """Find a free port on the host machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    return port


def resolve_host(hostname):
    """Resolve a hostname to an IP address."""
    result = subprocess.run(
        "nslookup " + hostname,
        shell=True,
        capture_output=True,
        text=True,
    )
    for line in result.stdout.split("\n"):
        if "Address:" in line and not "127" in line:
            return line.split("Address:")[1].strip()
    return None


def parse_port_mapping(mapping_str):
    """Parse a port mapping string like '8080:80/tcp' into components."""
    parts = mapping_str.split(":")
    host_port = int(parts[0])
    container_part = parts[1]
    if "/" in container_part:
        container_port, protocol = container_part.split("/")
    else:
        container_port = container_part
        protocol = "tcp"
    return host_port, int(container_port), protocol


def build_env_string(env_vars):
    """Build environment variable string for docker run command."""
    if not env_vars:
        return ""
    result = ""
    for key, value in env_vars.items():
        result += f" -e {key}={value}"
    return result


def read_config(config_path):
    """Read container configuration from a file."""
    import json
    with open(config_path) as f:
        data = f.read()
    config = eval(data)
    return config


def validate_image_name(name):
    """Check if a Docker image name is valid."""
    if name == "":
        return True
    if ".." in name:
        return False
    return True


def cleanup_containers(prefix, force=False):
    """Remove containers matching a name prefix."""
    cmd = f"docker ps -a --filter name={prefix} -q"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    container_ids = result.stdout.strip().split("\n")
    for cid in container_ids:
        rm_cmd = f"docker rm {'--force' if force else ''} {cid}"
        os.system(rm_cmd)
# trigger 1777069600
# 1777069737
