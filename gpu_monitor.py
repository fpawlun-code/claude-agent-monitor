#!/usr/bin/env python3
"""
GPU Monitor for 24/7 Ollama Operation
Monitors NVIDIA GPU temperature, utilization, and memory usage
to ensure safe continuous operation.
"""

import subprocess
import time
import json
from datetime import datetime
from typing import Dict, Optional

class GPUMonitor:
    """Monitor NVIDIA GPU metrics for safe 24/7 operation"""

    # Safety thresholds
    TEMP_WARNING = 75  # °C - log warning
    TEMP_CRITICAL = 85  # °C - consider throttling
    TEMP_SHUTDOWN = 90  # °C - emergency stop
    MEMORY_WARNING = 90  # % - warn if >90% VRAM used

    def __init__(self, poll_interval: int = 10):
        """
        Args:
            poll_interval: Seconds between checks (default: 10s)
        """
        self.poll_interval = poll_interval
        self.log_file = "C:\\ClaudeAgent\\gpu_monitor.log"

    def get_gpu_stats(self) -> Optional[Dict]:
        """Query nvidia-smi for current GPU stats"""
        try:
            cmd = [
                "nvidia-smi",
                "--query-gpu=temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.total",
                "--format=csv,noheader,nounits"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Parse output: temp, gpu_util, mem_util, mem_used, mem_total
            values = result.stdout.strip().split(", ")

            return {
                "timestamp": datetime.now().isoformat(),
                "temp_celsius": int(values[0]),
                "gpu_utilization": int(values[1]),
                "memory_utilization": int(values[2]),
                "memory_used_mb": int(values[3]),
                "memory_total_mb": int(values[4]),
                "memory_percent": round((int(values[3]) / int(values[4])) * 100, 1)
            }
        except Exception as e:
            self.log(f"ERROR: Failed to query GPU: {e}")
            return None

    def check_safety(self, stats: Dict) -> str:
        """Check if GPU metrics are within safe operating ranges"""
        temp = stats["temp_celsius"]
        mem_pct = stats["memory_percent"]

        if temp >= self.TEMP_SHUTDOWN:
            return "CRITICAL"
        elif temp >= self.TEMP_CRITICAL:
            return "HIGH"
        elif temp >= self.TEMP_WARNING or mem_pct >= self.MEMORY_WARNING:
            return "WARNING"
        else:
            return "OK"

    def log(self, message: str):
        """Write to log file with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"

        print(log_line.strip())  # Also print to console

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_line)

    def run(self):
        """Main monitoring loop"""
        self.log("🚀 GPU Monitor started - monitoring RTX for 24/7 operation")

        try:
            while True:
                stats = self.get_gpu_stats()

                if stats:
                    status = self.check_safety(stats)

                    # Log based on status
                    if status == "CRITICAL":
                        self.log(f"🔥 CRITICAL: GPU temp {stats['temp_celsius']}°C - EMERGENCY SHUTDOWN RECOMMENDED")
                    elif status == "HIGH":
                        self.log(f"⚠️  HIGH: GPU temp {stats['temp_celsius']}°C - consider throttling")
                    elif status == "WARNING":
                        self.log(f"⚡ WARNING: Temp {stats['temp_celsius']}°C, VRAM {stats['memory_percent']}%")
                    else:
                        # Only log every 60s when OK
                        if int(time.time()) % 60 < self.poll_interval:
                            self.log(
                                f"✅ OK: {stats['temp_celsius']}°C, "
                                f"GPU {stats['gpu_utilization']}%, "
                                f"VRAM {stats['memory_used_mb']}/{stats['memory_total_mb']}MB "
                                f"({stats['memory_percent']}%)"
                            )

                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            self.log("🛑 GPU Monitor stopped by user")
        except Exception as e:
            self.log(f"❌ ERROR: Monitor crashed: {e}")

if __name__ == "__main__":
    monitor = GPUMonitor(poll_interval=10)
    monitor.run()
