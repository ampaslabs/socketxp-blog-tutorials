"""Raspberry Pi health collectors. Each returns nothing on other hardware."""
import subprocess


def pi_throttled():
    """Decode `vcgencmd get_throttled` into flags (1 = set)."""
    try:
        out = subprocess.run(
            ["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2
        ).stdout                                   # e.g. "throttled=0x50005"
        value = int(out.strip().split("=")[1], 16)
    except (OSError, IndexError, ValueError, subprocess.TimeoutExpired):
        return {}
    return {
        "undervolt_now":   int(bool(value & 0x1)),
        "throttled_now":   int(bool(value & 0x4)),
        "undervolt_boot":  int(bool(value & 0x10000)),   # occurred since boot
        "throttled_boot":  int(bool(value & 0x40000)),
    }


def wifi_rssi(iface="wlan0"):
    """Signal level in dBm, or None when not on Wi-Fi."""
    try:
        with open("/proc/net/wireless") as f:
            for line in f:
                if line.strip().startswith(iface + ":"):
                    return float(line.split()[3].rstrip("."))
    except OSError:
        pass
    return None


def root_readonly():
    """1 if / is mounted read-only (often a failing SD card)."""
    readonly = 0
    with open("/proc/mounts") as f:
        for line in f:
            _dev, mountpoint, _fstype, opts = line.split()[:4]
            if mountpoint == "/":
                readonly = int("ro" in opts.split(","))
    return readonly


def collect():
    metrics = pi_throttled()
    metrics["root_ro"] = root_readonly()
    rssi = wifi_rssi()
    if rssi is not None:
        metrics["rssi"] = rssi
    return metrics
