"""
NetOps-AutoPilot // CLI de Automação de Redes Multi-Vendor
Uso:
  python main.py backup
  python main.py audit
  python main.py provision-vlan --vlan-id 50 --vlan-name WIFI_CONVIDADOS
  python main.py health
"""

import os
import yaml
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.backup.config_backup import ConfigBackupEngine
from src.audit.port_security import PortSecurityAuditor
from src.audit.health_check import NetworkHealthCheck
from src.provisioning.batch_deploy import BatchProvisioningEngine

console = Console()

def load_inventory(inventory_path: str = "inventory/hosts.yaml") -> list:
    if not os.path.exists(inventory_path):
        console.print(f"[red]Erro:[/red] Arquivo de inventário '{inventory_path}' não encontrado.")
        return []
    with open(inventory_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    devices = []
    if "switches" in data:
        devices.extend(data["switches"])
    if "routers" in data:
        devices.extend(data["routers"])
    return devices

@click.group()
def cli():
    """NetOps-AutoPilot: Automação de Redes Multi-Vendor com Python e Netmiko."""
    pass

@cli.command()
@click.option("--live", is_flag=True, default=False, help="Executar conexões SSH reais via Netmiko (padrão: modo simulação)")
@click.option("--inventory", "-i", default="inventory/hosts.yaml", help="Caminho do arquivo de inventário YAML")
def backup(live: bool, inventory: str):
    """Executa backup automatizado de running-config com cálculo de hash SHA256."""
    devices = load_inventory(inventory)
    engine = ConfigBackupEngine(mock_mode=not live)

    console.print()
    console.rule("[bold cyan]🔄 NetOps-AutoPilot // Backup de Configurações de Rede[/bold cyan]")
    console.print(f"[dim]Modo: {'SSH REAL (Netmiko)' if live else 'SIMULAÇÃO TESTE'} | Equipamentos: {len(devices)}[/dim]\n")

    table = Table(title="Status dos Backups de Rede", border_style="cyan")
    table.add_column("Hostname", style="bold white")
    table.add_column("IP", style="cyan")
    table.add_column("Fabricante", style="yellow")
    table.add_column("SHA256 (Hash)", style="dim")
    table.add_column("Status", justify="center")

    for dev in devices:
        res = engine.backup_device(dev)
        status_txt = "[bold green]SALVO ✔[/bold green]"
        if res["has_changes"]:
            status_txt = "[bold yellow]ALTERADO ⚠[/bold yellow]"
        table.add_row(res["hostname"], res["ip"], res["vendor"], res["sha256"][:12] + "...", status_txt)

    console.print(table)
    console.print("\n[green]✔ Backups arquivados com sucesso na pasta 'backups/'.[/green]\n")

@cli.command()
@click.option("--live", is_flag=True, default=False, help="Executar conexões SSH reais")
@click.option("--inventory", "-i", default="inventory/hosts.yaml", help="Inventário de equipamentos")
def audit(live: bool, inventory: str):
    """Audita switches em busca de falhas de Port-Security, BPDU Guard e VLANs."""
    devices = load_inventory(inventory)
    auditor = PortSecurityAuditor(mock_mode=not live)

    console.print()
    console.rule("[bold cyan]🛡️ NetOps-AutoPilot // Auditoria de Segurança de Portas e VLANs[/bold cyan]\n")

    todas_violacoes = []
    for dev in devices:
        if "switch" in dev.get("role", "").lower() or "cat" in dev.get("model", "").lower():
            v = auditor.audit_device(dev)
            todas_violacoes.extend(v)

    if not todas_violacoes:
        console.print("[bold green]✔ Nenhuma violação encontrada nas interfaces analisadas![/bold green]\n")
        return

    table = Table(title="Violações de Segurança de Rede Detectadas", border_style="red")
    table.add_column("Severidade", justify="center")
    table.add_column("Switch", style="bold white")
    table.add_column("Interface", style="cyan")
    table.add_column("Vulnerabilidade", style="yellow")
    table.add_column("Risco / Ação Corretiva", style="white")

    for v in todas_violacoes:
        sev = v["severidade"]
        sev_color = "red" if sev == "CRITICA" else ("yellow" if sev == "ALTA" else "cyan")
        table.add_row(f"[{sev_color}]{sev}[/{sev_color}]", v["hostname"], v["interface"], v["problema"], v["recomendacao"])

    console.print(table)
    console.print()

@cli.command()
@click.option("--vlan-id", "-v", required=True, type=int, help="ID numérico da VLAN (ex: 30)")
@click.option("--vlan-name", "-n", required=True, type=str, help="Nome da VLAN (ex: SERVIDORES_DMZ)")
@click.option("--range", "-r", default="GigabitEthernet1/0/10 - 15", help="Faixa de interfaces (ex: Gi1/0/10 - 15)")
@click.option("--dept", "-d", default="TI Corporativa", help="Departamento associado")
@click.option("--live", is_flag=True, default=False, help="Aplicar via SSH Netmiko real")
def provision_vlan(vlan_id: int, vlan_name: str, range: str, dept: str, live: bool):
    """Provisiona VLANs e Port-Security em lote usando templates Jinja2."""
    devices = load_inventory()
    deployer = BatchProvisioningEngine(mock_mode=not live)

    console.print()
    console.rule(f"[bold cyan]⚡ Provisionamento em Lote: VLAN {vlan_id} ({vlan_name})[/bold cyan]\n")

    for dev in devices:
        if "switch" in dev.get("role", "").lower():
            config_text = deployer.render_template("cisco_vlan_provision.j2", {
                "hostname": dev["hostname"],
                "vlan_id": vlan_id,
                "vlan_name": vlan_name,
                "interface_range": range,
                "department": dept
            })
            res = deployer.deploy_config(dev, config_text)
            console.print(f"[green]✔[/green] {dev['hostname']} ({dev['ip']}): {res['comandos_enviados']} comandos de configuração gerados e aplicados.")

    console.print("\n[bold green]Provisionamento em massa concluído com sucesso![/bold green]\n")

@cli.command()
@click.option("--inventory", "-i", default="inventory/hosts.yaml")
def health(inventory: str):
    """Executa sweep de conectividade ICMP e diagnóstico de latência nos hosts."""
    devices = load_inventory(inventory)
    checker = NetworkHealthCheck()

    console.print()
    console.rule("[bold cyan]📡 Diagnóstico de Saúde e Conectividade de Rede[/bold cyan]\n")

    results = checker.sweep_inventory(devices)
    table = Table(title="Diagnóstico de Conectividade Multi-Vendor", border_style="cyan")
    table.add_column("Hostname", style="bold white")
    table.add_column("IP", style="cyan")
    table.add_column("Fabricante", style="yellow")
    table.add_column("Status", justify="center")
    table.add_column("Latência RTT", justify="right")

    for r in results:
        status_txt = "[green]ONLINE ✔[/green]" if r["status"] == "ONLINE" else "[red]OFFLINE ✖[/red]"
        lat_txt = f"{r['rtt_ms']} ms" if r["rtt_ms"] is not None else "--"
        table.add_row(r["hostname"], r["host"], r["vendor"], status_txt, lat_txt)

    console.print(table)
    console.print()

if __name__ == "__main__":
    cli()
