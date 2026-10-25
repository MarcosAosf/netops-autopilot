"""
Módulo: ConnectionManager
Gerencia conexões SSH seguras via Netmiko com suporte a modo de simulação/offline.
"""

from typing import Dict, Any, Optional

class DeviceSession:
    def __init__(self, device_info: Dict[str, Any], mock_mode: bool = True):
        self.device = device_info
        self.mock_mode = mock_mode
        self.connection = None

    def connect(self):
        if self.mock_mode:
            return True

        from netmiko import ConnectHandler
        device_params = {
            "device_type": self.device.get("device_type", "cisco_ios"),
            "host": self.device["ip"],
            "username": self.device.get("username", "admin"),
            "password": self.device.get("secret", ""),
            "secret": self.device.get("secret", ""),
            "timeout": 10
        }
        self.connection = ConnectHandler(**device_params)
        self.connection.enable()
        return True

    def send_command(self, command: str) -> str:
        if self.mock_mode:
            return self._mock_output(command)

        if not self.connection:
            raise ConnectionError("Dispositivo não conectado.")
        return self.connection.send_command(command)

    def send_config(self, config_commands: list) -> str:
        if self.mock_mode:
            return f"[MOCK-OK] {len(config_commands)} comandos aplicados com sucesso em {self.device['hostname']}."

        if not self.connection:
            raise ConnectionError("Dispositivo não conectado.")
        return self.connection.send_config_set(config_commands)

    def disconnect(self):
        if self.connection:
            self.connection.disconnect()
            self.connection = None

    def _mock_output(self, command: str) -> str:
        cmd = command.strip().lower()
        hostname = self.device.get("hostname", "switch-01")

        if "show run" in cmd or "show running-config" in cmd:
            return f"""!
version 16.9
hostname {hostname}
!
vlan 10
 name FINANCEIRO
!
vlan 20
 name TI_INFRAESTRUTURA
!
interface GigabitEthernet1/0/1
 description UPLINK-CORE
 switchport mode trunk
!
interface GigabitEthernet1/0/2
 switchport mode access
 switchport access vlan 10
 switchport port-security
 switchport port-security maximum 2
 switchport port-security violation restrict
!
interface GigabitEthernet1/0/3
 switchport mode access
 switchport access vlan 20
 ! VIOLACAO: Port-security ausente
!
end"""

        if "show ip int br" in cmd or "show ip interface brief" in cmd:
            return f"""Interface              IP-Address      OK? Method Status                Protocol
GigabitEthernet1/0/1   10.0.0.1        YES NVRAM  up                    up      
GigabitEthernet1/0/2   unassigned      YES unset  up                    up      
GigabitEthernet1/0/3   unassigned      YES unset  up                    up      
Vlan10                 192.168.10.254  YES manual up                    up      
Vlan20                 192.168.20.254  YES manual up                    up      """

        if "show port-security" in cmd:
            return f"""Secure Port  MaxSecureAddr  CurrentAddr  SecurityViolation  Security Action
---------------------------------------------------------------------------
Gi1/0/2                 2            1                  0         Restrict
---------------------------------------------------------------------------"""

        return f"{hostname}# {command}\nOK"
