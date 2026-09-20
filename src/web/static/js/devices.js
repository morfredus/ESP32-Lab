/* ==========================================================================
   ESP32-Lab — cartes enregistrées (registre)
   ========================================================================== */

async function loadDevices() {
    const button = document.getElementById("devices-button");
    const container = document.getElementById("devices-content");

    button.disabled = true;
    button.textContent = "Chargement...";

    try {
        const result = await apiGet("/api/devices");
        devicesData = Object.values(result.devices || {});

        if (devicesData.length === 0) {
            container.innerHTML =
                '<div class="empty">Aucune carte enregistrée.</div>';
            return;
        }

        devicesData.sort((first, second) =>
            (first.name || first.mac).localeCompare(second.name || second.mac)
        );

        const rows = devicesData.map(device => {
            const scanCount = (historyByMac[(device.mac || "").toLowerCase()] || []).length;
            return `
            <tr>
                <td><strong>${escapeHtml(device.name || "Sans nom")}</strong></td>
                <td>${escapeHtml(device.mac)}</td>
                <td>${escapeHtml(device.chip || PLACEHOLDER)}</td>
                <td>${escapeHtml(device.location || PLACEHOLDER)}</td>
                <td>${escapeHtml(formatDateTime(device.last_seen))}</td>
                <td>${scanCount || 0}</td>
                <td>
                    <button class="history-details-button"
                            onclick="editDeviceProfile('${escapeHtml(device.mac)}')">
                        Modifier
                    </button>
                    <button class="history-details-button"
                            onclick="showDeviceDetails('${escapeHtml(device.mac)}')">
                        Détails
                    </button>
                    <button class="history-details-button"
                            onclick="compareDeviceScans('${escapeHtml(device.mac)}')"
                            ${scanCount < 2 ? "disabled title='Au moins 2 scans nécessaires'" : ""}>
                        Comparer les scans
                    </button>
                </td>
            </tr>
        `;
        }).join("");

        container.innerHTML = `
            <table>
                <thead>
                    <tr>
                        <th>Nom</th>
                        <th>MAC</th>
                        <th>ESP32</th>
                        <th>Emplacement</th>
                        <th>Dernière détection</th>
                        <th>Scans</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        `;
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    } finally {
        button.disabled = false;
        button.textContent = "Actualiser les cartes";
    }
}

/* Ouvre la modale de comparaison des scans d'une même carte. Réutilise la
   modale d'historique (liste des scans d'une MAC + sélection de deux entrées
   à comparer). */
function compareDeviceScans(mac) {
    const entries = historyByMac[(mac || "").toLowerCase()] || [];

    if (entries.length < 2) {
        setStatus(
            "Cette carte n'a qu'un seul scan : impossible de comparer.",
            true
        );
        return;
    }

    historyModalSelectedIndexes = new Set();
    showDeviceHistory(mac);
}

function filterDevices() {
    const search = document.getElementById("device-search-input")
        .value.trim().toLowerCase();

    document.querySelectorAll("#devices-content tbody tr").forEach(row => {
        row.style.display =
            row.textContent.toLowerCase().includes(search) ? "" : "none";
    });
}

function showDeviceDetails(mac) {
    const device = devicesData.find(
        item => (item.mac || "").toLowerCase() === mac.toLowerCase()
    ) || {};

    const entries = historyByMac[mac.toLowerCase()] || [];
    const latest = entries.length > 0 ? entries[0] : null;
    const info = latest ? (latest.inventory || {}).identification || {} : {};

    const modal = document.getElementById("history-modal");
    const title = document.getElementById("history-modal-title");
    const content = document.getElementById("history-modal-content");

    function value(deviceKey, infoKey = deviceKey) {
        return orPlaceholder(device[deviceKey] ?? info[infoKey]);
    }

    function unitValue(key, unit) {
        const raw = device[key] ?? info[key];
        return (raw === null || raw === undefined || raw === "")
            ? PLACEHOLDER
            : formatUnit(raw, unit);
    }

    title.textContent = "Détails - " + (device.name || mac);

    content.innerHTML = `
        <div class="device-details-grid">
            <div class="device-detail-card"><strong>Nom</strong>${escapeHtml(device.name || "Sans nom")}</div>
            <div class="device-detail-card"><strong>Adresse MAC</strong>${escapeHtml(mac)}</div>
            <div class="device-detail-card"><strong>Modèle</strong>${escapeHtml(value("chip"))}</div>
            <div class="device-detail-card"><strong>Emplacement</strong>${escapeHtml(device.location || PLACEHOLDER)}</div>
            <div class="device-detail-card"><strong>Dernière détection</strong>${escapeHtml(formatDateTime(device.last_seen))}</div>
            <div class="device-detail-card"><strong>Port série</strong>${escapeHtml(value("port"))}</div>
            <div class="device-detail-card"><strong>Révision</strong>${escapeHtml(value("revision"))}</div>
            <div class="device-detail-card"><strong>Fonctionnalités</strong>${escapeHtml(value("features"))}</div>
            <div class="device-detail-card"><strong>Fréquence CPU</strong>${escapeHtml(unitValue("cpu_frequency_mhz", "MHz"))}</div>
            <div class="device-detail-card"><strong>Fréquence quartz</strong>${escapeHtml(unitValue("crystal_frequency_mhz", "MHz"))}</div>
            <div class="device-detail-card"><strong>Flash</strong>${escapeHtml(unitValue("flash_size_mb", "Mo"))}</div>
            <div class="device-detail-card"><strong>Fabricant Flash</strong>${escapeHtml(flashManufacturerLabel(device.flash_manufacturer ?? info.flash_manufacturer))}</div>
            <div class="device-detail-card"><strong>Référence Flash</strong>${escapeHtml(flashDeviceLabel(device.flash_device ?? info.flash_device))}</div>
            <div class="device-detail-card"><strong>Type Flash</strong>${escapeHtml(value("flash_type"))}</div>
            <div class="device-detail-card"><strong>Tension Flash</strong>${escapeHtml(value("flash_voltage"))}</div>
            <div class="device-detail-card"><strong>PSRAM</strong>${escapeHtml(unitValue("psram_size_mb", "Mo"))}</div>
            <div class="device-detail-card"><strong>PSRAM disponible</strong>${escapeHtml(value("psram"))}</div>
            <div class="device-detail-card"><strong>Nombre de détections</strong>${entries.length}</div>
        </div>

        <div class="device-detail-card">
            <strong>Note</strong>${escapeHtml(device.note || PLACEHOLDER)}
        </div>

        <p>
            <button class="history-details-button"
                    onclick="editDeviceProfile('${escapeHtml(mac)}'); closeDeviceHistory();">
                Modifier la fiche
            </button>
            <button class="history-details-button"
                    onclick="compareDeviceScans('${escapeHtml(mac)}')"
                    ${entries.length < 2 ? "disabled title='Au moins 2 scans nécessaires'" : ""}>
                Comparer les scans
            </button>
        </p>
    `;

    modal.style.display = "block";
}
