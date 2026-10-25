"""
Testes Unitários para o NetOps-AutoPilot.
"""

from src.backup.config_backup import ConfigBackupEngine
from src.audit.port_security import PortSecurityAuditor
from src.provisioning.batch_deploy import BatchProvisioningEngine

def test_backup_engine_checksum():
    engine = ConfigBackupEngine(backup_dir="tests/test_backups", mock_mode=True)
    dev = {"hostname": "sw-test-01", "ip": "10.0.0.1", "device_type": "cisco_ios", "vendor": "Cisco"}
    res = engine.backup_device(dev)

    assert res["hostname"] == "sw-test-01"
    assert len(res["sha256"]) == 64 # SHA256 hex length
    assert "sw-test-01" in res["backup_path"]

def test_port_security_auditor_detects_violations():
    auditor = PortSecurityAuditor(mock_mode=True)
    dev = {"hostname": "sw-core", "ip": "10.0.0.1", "device_type": "cisco_ios", "vendor": "Cisco"}
    violations = auditor.audit_device(dev)

    # O mock contém Gi1/0/3 sem port-security e Gi1/0/1 trunk sem native vlan
    rules = [v["regra"] for v in violations]
    assert "SEC-NET-01" in rules # Port-security ausente
    assert "SEC-NET-03" in rules # Native VLAN 1 trunk

def test_batch_provisioning_jinja2():
    deployer = BatchProvisioningEngine(templates_dir="templates", mock_mode=True)
    rendered = deployer.render_template("cisco_vlan_provision.j2", {
        "hostname": "sw-dist",
        "vlan_id": 99,
        "vlan_name": "GERENCIA_OOB",
        "interface_range": "GigabitEthernet1/0/20 - 24",
        "department": "NOC"
    })

    assert "vlan 99" in rendered
    assert "name GERENCIA_OOB" in rendered
    assert "switchport port-security" in rendered
