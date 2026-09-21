/* ==========================================================================
   ESP32-Lab - Firmware & OTA : identite des applications et etat OTA
   ========================================================================== */

/** Lit le firmware et l'etat OTA sur la carte (lecture seule). */
async function loadFirmware() {
    const button = document.getElementById("firmware-button");
    const container = document.getElementById("firmware-content");

    const selectedPort = portSelect.value;
    if (!selectedPort) {
        container.innerHTML =
            '<div class="empty">Sélectionne un port série (onglet Général).</div>';
        return;
    }

    const chip = currentInventory && currentInventory.identification
        && currentInventory.identification.chip_family;
    const mac = currentInventory && currentInventory.identification
        && currentInventory.identification.mac;

    button.disabled = true;
    button.textContent = "Lecture du firmware...";
    container.innerHTML =
        '<div class="empty">Lecture du firmware en cours (lecture seule, ' +
        'plusieurs zones Flash)...</div>';

    try {
        let url = "/api/firmware?port=" + encodeURIComponent(selectedPort);
        if (chip) {
            url += "&chip=" + encodeURIComponent(chip);
        }
        if (mac) {
            url += "&mac=" + encodeURIComponent(mac);
        }

        const report = await apiPost(url);
        renderFirmware(report);
        setStatus("Firmware lu sur la carte.");
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        setStatus("Lecture du firmware impossible : " + error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Lire le firmware";
    }
}

/** Recharge la derniere lecture firmware depuis la base (sans la carte). */
async function loadFirmwareFromDb() {
    const button = document.getElementById("firmware-db-button");
    const container = document.getElementById("firmware-content");

    button.disabled = true;
    button.textContent = "Chargement...";

    try {
        const reading = await loadStoredReading("firmware");
        if (reading && reading.payload) {
            renderFirmware(reading.payload);
            setStatus(
                "Firmware chargé depuis la base (lecture du " +
                formatDateTime(reading.recorded_at) + ")."
            );
        } else {
            container.innerHTML =
                '<div class="empty">Aucune lecture firmware en base pour cette ' +
                'carte. Branche-la puis clique « Lire le firmware ».</div>';
        }
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        setStatus(error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Charger depuis la base";
    }
}

function firmwareOtaBlock(ota) {
    if (!ota || !ota.present) {
        return `
            <div class="panel">
                <h3>OTA</h3>
                <p class="note">Pas de partition <code>otadata</code> : cette
                carte n'utilise pas l'OTA (démarrage sur <code>factory</code>).</p>
            </div>`;
    }

    const rows = (ota.entries || []).map((entry, index) => {
        if (!entry) {
            return "";
        }
        const seq = entry.blank ? "(vierge)" : entry.ota_seq;
        const crc = entry.blank
            ? PLACEHOLDER
            : (entry.crc_ok
                ? '<span class="badge badge-on">OK</span>'
                : '<span class="badge badge-off">invalide</span>');
        return `
            <tr>
                <td>#${index}</td>
                <td>${escapeHtml(String(seq))}</td>
                <td>${escapeHtml(entry.ota_state_name)}</td>
                <td>${crc}</td>
            </tr>`;
    }).join("");

    return `
        <div class="panel">
            <h3>OTA</h3>
            <div class="detail">
                Slot sélectionné au démarrage :
                <strong>${escapeHtml(ota.boot_label)}</strong>
            </div>
            <p class="note">
                Il s'agit du slot que le bootloader choisira au prochain
                démarrage, pas forcément le firmware en cours d'exécution.
            </p>
            <table class="efuse-mac-table">
                <thead><tr>
                    <th>Entrée</th><th>Séquence</th><th>État</th><th>CRC</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>`;
}

function firmwareAppCard(app) {
    const desc = app.app_desc;
    const bootMark = "";

    let body;
    if (app.encrypted && !desc) {
        body = '<div class="gpio-note">Partition chiffrée : identité illisible.' +
            '</div>';
    } else if (!desc) {
        body = '<div class="gpio-note">Slot vide (aucune application ' +
            'programmée).</div>';
    } else {
        const rows = [
            ["Projet", desc.project_name],
            ["Version", desc.version],
            ["Version ESP-IDF", desc.idf_ver],
            ["Compilé le", (desc.date || "") + " " + (desc.time || "")],
            ["Anti-rollback (secure_version)", desc.secure_version]
        ].map(([label, value]) => `
            <tr>
                <td>${escapeHtml(label)}</td>
                <td><strong>${escapeHtml(orPlaceholder(value))}</strong></td>
            </tr>`).join("");

        body = `
            <table class="efuse-mac-table">
                <tbody>${rows}</tbody>
            </table>
            <div class="firmware-sha">
                <span class="efuse-tile-label">sha256 de l'ELF</span>
                <code>${escapeHtml(desc.elf_sha256)}</code>
            </div>`;
    }

    return `
        <details class="efuse-category firmware-app">
            <summary>
                ${escapeHtml(app.label || app.subtype)}
                <small>(${escapeHtml(app.subtype)},
                ${(app.size / 1024).toFixed(0)} Kio)</small>${bootMark}
            </summary>
            <div style="padding:10px;">${body}</div>
        </details>`;
}

function renderFirmware(report) {
    const container = document.getElementById("firmware-content");
    const apps = report.apps || [];

    const appCards = apps.map(firmwareAppCard).join("");

    container.innerHTML = `
        ${firmwareOtaBlock(report.ota)}
        <div class="panel">
            <h3>Applications (${apps.length})</h3>
            <p class="note">
                Identité lue dans chaque partition applicative
                (<code>esp_app_desc</code>). Lecture seule.
            </p>
            ${appCards || '<div class="empty">Aucune application.</div>'}
        </div>
    `;

    container.querySelectorAll("details").forEach(detail => {
        detail.open = true;
    });
}
