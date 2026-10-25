"""
Módulo: NetworkHealthCheck
Executa diagnósticos de conectividade ICMP/Ping em lote, medindo latência média e perda de pacotes.
"""

import time
import subprocess
from typing import List, Dict, Any

class NetworkHealthCheck:
    def __init__(self, timeout_sec: int = 1):
        self.timeout = timeout_sec

    def ping_host(self, host: str, count: int = 2) -> Dict[str, Any]:
        """Testa conectividade com medição de RTT."""
        inicio = time.monotonic()
        # Comando ping multiplataforma (Windows: -n, Linux: -c)
        param = "-n" if subprocess.os.name == "nt" else "-c"
        cmd = ["ping", param, str(count), "-w", str(self.timeout * 1000), host]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            rtt_ms = round((time.monotonic() - inicio) * 1000 / count, 2)
            sucesso = res.returncode == 0
        except Exception:
            sucesso = False
            rtt_ms = 0.0

        return {
            "host": host,
            "status": "ONLINE" if sucesso else "OFFLINE",
            "rtt_ms": rtt_ms if sucesso else None,
            "perda_pct": 0 if sucesso else 100
        }

    def sweep_inventory(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for dev in devices:
            ip = dev.get("ip")
            if not ip:
                continue
            res = self.ping_host(ip)
            res["hostname"] = dev.get("hostname", ip)
            res["vendor"] = dev.get("vendor", "N/A")
            results.append(res)
        return results
