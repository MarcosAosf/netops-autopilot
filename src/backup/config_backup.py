"""
Módulo: ConfigBackupEngine
Executa extração, arquivamento com checksum SHA256 e diff de configurações de equipamentos de rede.
"""

import os
import hashlib
import difflib
from datetime import datetime
from typing import Dict, Any, Tuple
from src.core.connection import DeviceSession

class ConfigBackupEngine:
    def __init__(self, backup_dir: str = "backups", mock_mode: bool = True):
        self.backup_dir = backup_dir
        self.mock_mode = mock_mode
        os.makedirs(self.backup_dir, exist_ok=True)

    def backup_device(self, device: Dict[str, Any]) -> Dict[str, Any]:
        hostname = device.get("hostname", "unknown-device")
        session = DeviceSession(device, mock_mode=self.mock_mode)
        session.connect()

        cmd = "show running-config"
        if "mikrotik" in device.get("device_type", ""):
            cmd = "/export"

        raw_config = session.send_command(cmd)
        session.disconnect()

        # Checksum SHA256 para integridade
        sha256 = hashlib.sha256(raw_config.encode("utf-8")).hexdigest()

        # Salvar arquivo de backup versionado
        data_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        device_folder = os.path.join(self.backup_dir, hostname)
        os.makedirs(device_folder, exist_ok=True)

        backup_file = os.path.join(device_folder, f"{hostname}_{data_str}.cfg")
        with open(backup_file, "w", encoding="utf-8") as f:
            f.write(raw_config)

        # Verificar diff com o backup anterior se existir
        diff_output = self._compare_with_previous(device_folder, backup_file)

        return {
            "hostname": hostname,
            "ip": device.get("ip"),
            "vendor": device.get("vendor"),
            "sha256": sha256,
            "backup_path": backup_file,
            "has_changes": bool(diff_output),
            "diff": diff_output
        }

    def _compare_with_previous(self, folder: str, current_file: str) -> str:
        files = sorted([os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".cfg")])
        if len(files) < 2:
            return ""

        previous_file = files[-2]
        with open(previous_file, "r", encoding="utf-8") as f1, open(current_file, "r", encoding="utf-8") as f2:
            diff = list(difflib.unified_diff(
                f1.readlines(),
                f2.readlines(),
                fromfile="backup_anterior",
                tofile="backup_atual"
            ))
            return "".join(diff)
