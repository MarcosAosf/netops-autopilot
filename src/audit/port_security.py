"""
Módulo: PortSecurityAuditor
Audita interfaces de switches para conformidade com normas de segurança de rede (Port-Security, VLANs, Trunks).
"""

import re
from typing import Dict, Any, List
from src.core.connection import DeviceSession

class PortSecurityAuditor:
    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode

    def audit_device(self, device: Dict[str, Any]) -> List[Dict[str, Any]]:
        hostname = device.get("hostname", "switch")
        session = DeviceSession(device, mock_mode=self.mock_mode)
        session.connect()

        running_config = session.send_command("show running-config")
        session.disconnect()

        violations = []

        # Expressão para capturar blocos de interface
        interfaces = re.findall(r"interface\s+([^\n]+)\n(.*?)(?=\ninterface|\nend|\Z)", running_config, re.DOTALL)

        for intf_name, intf_body in interfaces:
            intf_name = intf_name.strip()

            # Apenas interfaces de acesso ethernet
            if "Ethernet" not in intf_name:
                continue

            # Se for porta de acesso
            if "switchport mode access" in intf_body:
                # Regra 1: Falta de port-security
                if "switchport port-security" not in intf_body:
                    violations.append({
                        "hostname": hostname,
                        "interface": intf_name,
                        "regra": "SEC-NET-01",
                        "severidade": "ALTA",
                        "problema": "Porta de acesso sem Port-Security habilitado.",
                        "risco": "Vulnerável a ataques de MAC Flooding e rogue DHCP servers.",
                        "recomendacao": "Habilite 'switchport port-security' com limite de MACs e violação restrict."
                    })

                # Regra 2: Falta de BPDU Guard
                if "spanning-tree bpduguard" not in intf_body:
                    violations.append({
                        "hostname": hostname,
                        "interface": intf_name,
                        "regra": "SEC-NET-02",
                        "severidade": "MEDIA",
                        "problema": "Ausência de Spanning-Tree BPDU Guard.",
                        "risco": "Risco de loop de rede caso um switch não autorizado seja plugado.",
                        "recomendacao": "Adicione 'spanning-tree bpduguard enable'."
                    })

            # Se for porta Trunk
            if "switchport mode trunk" in intf_body:
                # Regra 3: VLAN Nativa 1 (VLAN Hopping)
                if "switchport trunk native vlan" not in intf_body:
                    violations.append({
                        "hostname": hostname,
                        "interface": intf_name,
                        "regra": "SEC-NET-03",
                        "severidade": "CRITICA",
                        "problema": "Porta Trunk utilizando VLAN nativa padrão (VLAN 1).",
                        "risco": "Vulnerável a ataques de Double Tagging / VLAN Hopping.",
                        "recomendacao": "Altere a VLAN nativa para uma VLAN nula não utilizada (ex: vlan 999)."
                    })

        return violations
