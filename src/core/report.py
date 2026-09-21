"""
Rapport exportable par carte : une page HTML autonome, hors ligne, sans secret.

Assemble le dossier deja enregistre (`database.get_device_dossier`) : identite,
bilan de securite, Flash/SFDP, partitions, structure NVS, cartographie GPIO et
firmware. Les charges utiles stockees sont deja assainies (aucun secret) ; le
rapport n'en revele donc aucun. Les sections non capturees sont signalees comme
telles.
"""

import html
from datetime import datetime, timezone

from core import database
from core.esp32_gpio import compute_gpio_map
from core.security_posture import assess_security


SECTION_LABELS = {
    "inventory": "Inventaire",
    "efuse": "Identite & Securite (eFuses)",
    "sfdp": "Puce Flash (SFDP)",
    "partitions": "Partitions",
    "nvs": "Structure NVS",
    "firmware": "Firmware & OTA",
}


def build_report(mac):
    """Assemble les donnees du rapport d'une carte, ou ``None`` si absente."""

    dossier = database.get_device_dossier(mac)
    if not dossier:
        return None

    device = dossier.get("device", {})
    sections = dossier.get("sections", {})
    captured = dossier.get("captured", {})

    efuse = sections.get("efuse") or {}
    assessment = None
    if efuse.get("security"):
        assessment = assess_security(efuse["security"])

    gpio = None
    chip_family = device.get("chip_family")
    if chip_family:
        gpio = compute_gpio_map(chip_family, board=device.get("board_profile"))
        if gpio.get("status") != "ok" or not gpio.get("family_supported"):
            gpio = None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "captured": captured,
        "assessment": assessment,
        "efuse_identity": efuse.get("identity"),
        "sfdp": sections.get("sfdp"),
        "partitions": sections.get("partitions"),
        "nvs": sections.get("nvs"),
        "firmware": sections.get("firmware"),
        "gpio": gpio,
    }


def _esc(value):
    if value is None:
        return "-"
    return html.escape(str(value))


def _rows(pairs):
    body = "".join(
        f"<tr><th>{_esc(label)}</th><td>{_esc(value)}</td></tr>"
        for label, value in pairs
    )
    return f"<table class='kv'>{body}</table>"


def _scalar_rows(payload, skip=()):
    """
    Lignes cle/valeur d'une section : champs scalaires de premier niveau, et
    scalaires d'un niveau imbrique (prefixes) pour surfacer les details utiles
    (SFDP, NVS...) sans connaitre le schema exact.
    """

    pairs = []
    for key, value in (payload or {}).items():
        if key in skip or key in {"status", "source"}:
            continue
        if isinstance(value, (str, int, float, bool)):
            pairs.append((key, value))
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (str, int, float, bool)):
                    pairs.append((f"{key}.{sub_key}", sub_value))

    return _rows(pairs) if pairs else "<p class='muted'>Capture disponible dans l'application (pas de resume ici).</p>"


def _section_identity(device):
    return _rows([
        ("Nom", device.get("name") or "-"),
        ("Adresse MAC", device.get("mac")),
        ("Emplacement", device.get("location") or "-"),
        ("Puce", device.get("chip")),
        ("Famille", device.get("chip_family")),
        ("Revision", device.get("revision")),
        ("Frequence CPU", device.get("cpu_frequency_mhz")),
        ("Flash (Mo)", device.get("flash_size_mb")),
        ("PSRAM", device.get("psram")),
        ("Profil de carte", device.get("board_profile") or "-"),
    ])


def _section_assessment(assessment):
    if not assessment:
        return "<p class='muted'>Section eFuse non capturee.</p>"

    items = "".join(
        f"<tr><td>{_esc(it['label'])}</td>"
        f"<td><span class='badge {('on' if it['status'] else 'off')}'>"
        f"{'Active' if it['status'] else 'Non active'}</span></td>"
        f"<td>{_esc(it['summary'])}</td>"
        f"<td class='muted'>{_esc(it['advice'])}</td></tr>"
        for it in assessment["items"]
    )
    return (
        f"<p class='posture posture-{_esc(assessment['posture'])}'>"
        f"Posture : <strong>{_esc(assessment['posture_label'])}</strong> "
        f"({assessment['activated']}/{assessment['total']} protections actives)"
        "</p>"
        "<table class='grid'><thead><tr><th>Protection</th><th>Etat</th>"
        "<th>Description</th><th>Conseil</th></tr></thead>"
        f"<tbody>{items}</tbody></table>"
    )


def _section_partitions(payload):
    if not payload:
        return "<p class='muted'>Non capturee.</p>"

    rows = "".join(
        f"<tr><td>{_esc(p.get('label'))}</td><td>{_esc(p.get('type'))}</td>"
        f"<td>{_esc(p.get('subtype'))}</td>"
        f"<td>{_esc(hex(p['offset']) if isinstance(p.get('offset'), int) else p.get('offset'))}</td>"
        f"<td>{_esc(p.get('size'))}</td>"
        f"<td>{'oui' if p.get('encrypted') else 'non'}</td></tr>"
        for p in payload.get("partitions", [])
    )
    return (
        "<table class='grid'><thead><tr><th>Label</th><th>Type</th>"
        "<th>Sous-type</th><th>Offset</th><th>Taille</th><th>Chiffree</th>"
        f"</tr></thead><tbody>{rows}</tbody></table>"
    )


def _section_gpio(gpio):
    if not gpio:
        return "<p class='muted'>Famille non couverte ou carte non scannee.</p>"

    summary = gpio.get("summary", {})
    strapping = ", ".join(
        f"GPIO{p['gpio']}" for p in gpio.get("pins", []) if p.get("strapping"))
    onboard = ", ".join(
        f"GPIO{p['gpio']} ({p['board'].get('label') or p['board'].get('role')})"
        for p in gpio.get("pins", [])
        if p.get("board") and p["board"].get("exposure") == "onboard")

    pairs = [
        ("Famille", gpio.get("label")),
        ("GPIO", gpio.get("gpio_count")),
        ("Disponibles", summary.get("available")),
        ("Avec restrictions", summary.get("restricted")),
        ("A eviter", summary.get("avoid")),
        ("Strapping", strapping or "-"),
    ]
    if onboard:
        pairs.append(("Fonctions carte", onboard))
    return _rows(pairs)


def _section_firmware(payload):
    if not payload:
        return "<p class='muted'>Non capturee.</p>"

    ota = payload.get("ota", {})
    ota_line = (
        f"<p>Slot de boot : <strong>{_esc(ota.get('boot_label'))}</strong></p>"
        if ota.get("present") else "<p class='muted'>Pas d'OTA (factory).</p>"
    )

    apps = ""
    for app in payload.get("apps", []):
        desc = app.get("app_desc")
        if desc:
            detail = (
                f"projet {_esc(desc.get('project_name'))}, "
                f"version {_esc(desc.get('version'))}, "
                f"IDF {_esc(desc.get('idf_ver'))}, "
                f"compile {_esc(desc.get('date'))} {_esc(desc.get('time'))}"
            )
        elif app.get("encrypted"):
            detail = "chiffree (illisible)"
        else:
            detail = "vide"
        apps += (
            f"<tr><td>{_esc(app.get('label'))}</td>"
            f"<td>{_esc(app.get('subtype'))}</td><td>{detail}</td></tr>"
        )

    return (
        ota_line
        + "<table class='grid'><thead><tr><th>Partition</th><th>Sous-type</th>"
        f"<th>Application</th></tr></thead><tbody>{apps}</tbody></table>"
    )


def _block(title, body):
    return f"<section><h2>{_esc(title)}</h2>{body}</section>"


CSS = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0;
    color: #1e293b; background: #f1f5f9; }
.page { max-width: 860px; margin: 0 auto; padding: 24px 20px 40px; }
.report-header { display: flex; justify-content: space-between; align-items: flex-start;
    gap: 16px; background: #fff; border-left: 6px solid #2563eb; border-radius: 10px;
    padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.report-header h1 { margin: 0 0 4px; font-size: 22px; }
.sub { color: #64748b; margin: 0; font-size: 13px; }
.print-btn { border: 0; background: #2563eb; color: #fff; padding: 10px 16px;
    border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer;
    white-space: nowrap; }
.print-btn:hover { background: #1d4ed8; }
section { margin: 18px 0; background: #fff; border-radius: 10px; padding: 6px 20px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,.05); }
h2 { border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; font-size: 17px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
table.kv th { text-align: left; width: 210px; color: #475569; font-weight: 600;
    vertical-align: top; }
table.kv th, table.kv td { padding: 5px 8px; border-bottom: 1px solid #f1f5f9; }
table.grid th, table.grid td { padding: 6px 8px; border-bottom: 1px solid #e2e8f0;
    text-align: left; vertical-align: top; }
table.grid thead th { background: #f1f5f9; }
thead { display: table-header-group; }
.badge { padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge.on { background: #d1fadf; color: #027a48; }
.badge.off { background: #e5e7eb; color: #475569; }
.muted { color: #64748b; }
.posture { padding: 8px 12px; border-radius: 8px; background: #eef2f7;
    display: inline-block; font-size: 15px; }
.posture-hardened { background: #d1fadf; color: #027a48; }
.posture-partial { background: #fef0c7; color: #b54708; }
footer { margin-top: 24px; color: #94a3b8; font-size: 12px; text-align: center; }

@media print {
  body { background: #fff; }
  .page { max-width: none; padding: 0; }
  .no-print { display: none !important; }
  .report-header, section { box-shadow: none; }
  section { break-inside: avoid; page-break-inside: avoid; margin: 12px 0; }
  h2 { break-after: avoid; }
  tr { break-inside: avoid; }
  .badge, .posture, .report-header, table.grid thead th {
    -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  @page { margin: 14mm; }
}
"""


def _format_dt(value):
    """Formate une date ISO en '22/09/2026 01:23 UTC' (best effort)."""

    if not value:
        return "-"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(value))
        return dt.strftime("%d/%m/%Y %H:%M UTC")
    except (TypeError, ValueError):
        return str(value)


def render_report_html(report):
    """Rendu du rapport en page HTML autonome (CSS inline, aucun secret)."""

    if report is None:
        return "<!doctype html><meta charset='utf-8'><p>Carte introuvable.</p>"

    device = report.get("device", {})
    name = device.get("name") or device.get("mac") or "Carte ESP32"
    generated = report.get("generated_at", "")

    sfdp = report.get("sfdp")
    nvs = report.get("nvs")

    body = "".join([
        _block("Identite", _section_identity(device)),
        _block("Bilan de securite", _section_assessment(report.get("assessment"))),
        _block(
            "Puce Flash (SFDP)",
            _scalar_rows(sfdp, skip={"tables", "parameters"})
            if sfdp else "<p class='muted'>Non capturee.</p>"),
        _block("Partitions", _section_partitions(report.get("partitions"))),
        _block(
            "Structure NVS",
            _scalar_rows(nvs, skip={"entries", "pages", "report"})
            if nvs else "<p class='muted'>Non capturee.</p>"),
        _block("Cartographie GPIO", _section_gpio(report.get("gpio"))),
        _block("Firmware & OTA", _section_firmware(report.get("firmware"))),
    ])

    return (
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Rapport ESP32-Lab - {_esc(name)}</title>"
        f"<style>{CSS}</style></head><body><div class='page'>"
        "<header class='report-header'><div>"
        f"<h1>{_esc(name)}</h1>"
        f"<p class='sub'>Rapport ESP32-Lab &middot; MAC {_esc(device.get('mac'))}"
        f" &middot; genere le {_esc(_format_dt(generated))}</p></div>"
        "<button class='print-btn no-print' onclick='window.print()'>"
        "Telecharger en PDF</button></header>"
        f"{body}"
        "<footer>Rapport genere en lecture seule. Aucun secret (mot de passe, "
        "cle) n'est stocke ni inclus : seules des empreintes servent au suivi."
        "</footer></div></body></html>"
    )
