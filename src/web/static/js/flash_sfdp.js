/* ==========================================================================
   ESP32-Lab - Puce Flash : SFDP et identifiant unique
   ========================================================================== */

/** Recharge les détails SFDP depuis la base (sans la carte), par MAC affichée. */
async function loadFlashDetailsFromDb() {
    const button = document.getElementById("flash-sfdp-db-button");
    const container = document.getElementById("flash-sfdp-content");

    button.disabled = true;
    button.textContent = "Chargement...";

    try {
        const reading = await loadStoredReading("sfdp");
        if (reading && reading.payload) {
            renderFlashDetails(reading.payload);
            setStatus(
                "Détails SFDP chargés depuis la base (lecture du " +
                formatDateTime(reading.recorded_at) + ")."
            );
        } else {
            container.innerHTML =
                '<div class="empty">Aucune lecture SFDP en base pour cette ' +
                'carte. Branchez-la puis cliquez « Lire les détails de la ' +
                'Flash (SFDP) ».</div>';
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

async function loadFlashDetails() {
    const button = document.getElementById("flash-sfdp-button");
    const container = document.getElementById("flash-sfdp-content");

    const selectedPort = portSelect.value;
    if (!selectedPort) {
        container.innerHTML =
            '<div class="empty">Sélectionnez un port série (onglet Général).</div>';
        return;
    }

    const chip = currentInventory
        && currentInventory.identification
        && currentInventory.identification.chip_family;

    button.disabled = true;
    button.textContent = "Lecture SFDP...";
    container.innerHTML =
        '<div class="empty">Lecture des paramètres de la puce Flash ' +
        '(lecture seule)...</div>';

    try {
        let url = "/api/flash?port=" + encodeURIComponent(selectedPort);
        if (chip) {
            url += "&chip=" + encodeURIComponent(chip);
        }
        const mac = currentInventory && currentInventory.identification
            && currentInventory.identification.mac;
        if (mac) {
            url += "&mac=" + encodeURIComponent(mac);
        }

        const report = await apiPost(url);
        renderFlashDetails(report);
        setStatus("Détails de la puce Flash lus (SFDP).");
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        setStatus("Lecture SFDP impossible : " + error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Lire les détails de la Flash (SFDP)";
    }
}

function renderFlashDetails(report) {
    const container = document.getElementById("flash-sfdp-content");
    const jedec = report.jedec || {};
    const unique = report.unique_id || {};
    const sfdp = report.sfdp || {};
    const flash = report.flash || {};
    const fastRead = flash.fast_read || {};

    const tiles = [
        ["Fabricant", jedec.manufacturer_name],
        ["Référence", jedec.device_name],
        ["Densité (SFDP)", flash.capacity_label],
        ["Adressage", flash.address_bytes],
        ["Révision SFDP", sfdp.revision],
        ["Identifiant JEDEC", jedec.raw]
    ].map(([label, value]) => `
        <div class="efuse-tile">
            <div class="efuse-tile-label">${escapeHtml(label)}</div>
            <div class="efuse-tile-value">
                <strong>${escapeHtml(orPlaceholder(value))}</strong>
            </div>
        </div>
    `).join("");

    const uniqueBlock = unique.hex ? `
        <div class="efuse-unique">
            <div class="efuse-tile-label">
                Identifiant unique de la puce Flash (64 bits)
            </div>
            <code>${escapeHtml(unique.hex)}</code>
        </div>
    ` : "";

    const eraseRows = (flash.erase_types || []).map(erase => `
        <tr>
            <td>${escapeHtml(erase.size_label)}</td>
            <td><code>${escapeHtml(erase.opcode)}</code></td>
        </tr>
    `).join("");

    const eraseTable = eraseRows ? `
        <h3>Granularités d'effacement</h3>
        <table class="efuse-mac-table">
            <thead><tr><th>Taille</th><th>Opcode</th></tr></thead>
            <tbody>${eraseRows}</tbody>
        </table>
    ` : "";

    const fastReadBadges = [
        ["Dual 1-1-2", fastRead["1-1-2"]],
        ["Dual 1-2-2", fastRead["1-2-2"]],
        ["Quad 1-1-4", fastRead["1-1-4"]],
        ["Quad 1-4-4", fastRead["1-4-4"]],
        ["DTR", fastRead.dtr]
    ].map(([label, active]) => `
        <span class="badge ${active ? "badge-on" : "badge-off"}">
            ${escapeHtml(label)}
        </span>
    `).join(" ");

    const paramRows = (sfdp.param_headers || []).map(header => `
        <tr>
            <td><code>${escapeHtml(header.id)}</code></td>
            <td>${escapeHtml(header.major)}.${escapeHtml(header.minor)}</td>
            <td>${escapeHtml(header.length_dwords)} dwords</td>
            <td><code>0x${Number(header.pointer).toString(16).toUpperCase()}</code></td>
        </tr>
    `).join("");

    container.innerHTML = `
        <div class="panel">
            <h3>Puce Flash</h3>
            <div class="efuse-tiles">${tiles}</div>
            ${uniqueBlock}
        </div>
        <div class="panel">
            ${eraseTable}
            <h3>Modes de lecture rapide</h3>
            <div class="badge-row">${fastReadBadges}</div>
        </div>
        <div class="panel">
            <h3>Tables de paramètres SFDP</h3>
            <p class="note">
                Signature ${sfdp.signature_valid ? "valide" : "invalide"} ·
                ${escapeHtml(sfdp.num_param_headers)} table(s).
            </p>
            <table class="efuse-mac-table">
                <thead>
                    <tr><th>ID</th><th>Révision</th><th>Longueur</th><th>Offset</th></tr>
                </thead>
                <tbody>${paramRows}</tbody>
            </table>
        </div>
    `;
}
