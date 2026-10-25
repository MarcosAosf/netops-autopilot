"""
Módulo: BatchProvisioningEngine
Renderiza templates Jinja2 e aplica blocos de configuração em massa em switches e roteadores.
"""

import os
from jinja2 import Template
from typing import Dict, Any, List
from src.core.connection import DeviceSession

class BatchProvisioningEngine:
    def __init__(self, templates_dir: str = "templates", mock_mode: bool = True):
        self.templates_dir = templates_dir
        self.mock_mode = mock_mode

    def render_template(self, template_name: str, variables: Dict[str, Any]) -> str:
        tpl_path = os.path.join(self.templates_dir, template_name)
        if not os.path.exists(tpl_path):
            raise FileNotFoundError(f"Template não encontrado: {tpl_path}")

        with open(tpl_path, "r", encoding="utf-8") as f:
            template = Template(f.read())
        return template.render(**variables)

    def deploy_config(self, device: Dict[str, Any], config_text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in config_text.splitlines() if line.strip() and not line.strip().startswith("!")]
        session = DeviceSession(device, mock_mode=self.mock_mode)
        session.connect()
        result = session.send_config(lines)
        session.disconnect()

        return {
            "hostname": device.get("hostname"),
            "ip": device.get("ip"),
            "comandos_enviados": len(lines),
            "status": "APLICADO",
            "detalhes": result
        }
