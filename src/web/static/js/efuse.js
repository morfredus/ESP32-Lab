/* ==========================================================================
   ESP32-Lab — eFuses : identité du silicium et état de sécurité
   ========================================================================== */

const MAC_LABELS = {
    wifi_sta: "Wi-Fi station",
    wifi_ap: "Wi-Fi point d'accès",
    bluetooth: "Bluetooth",
    ethernet: "Ethernet"
};

async function loadEfuses() {
    const button = document.getElementById("efuse-button");
    const container = document.getElementById("efuse-content");

    const selectedPort = portSelect.value;
    if (!selectedPort) {
        container.innerHTML =
            '<div class="empty">Sélectionne un port série (onglet Général).</div>';
        return;
    }

    const chip = currentInventory
        && currentInventory.identification
        && currentInventory.identification.chip_family;

    button.disabled = true;
    button.textContent = "Lecture des eFuses...";
    container.innerHTML =
        '<div class="empty">Lecture des eFuses en cours ' +
        '(lecture seule, une dizaine de secondes)...</div>';

    try {
        let url = "/api/efuse?port=" + encodeURIComponent(selectedPort);
        if (chip) {
            url += "&chip=" + encodeURIComponent(chip);
        }
        const mac = currentInventory && currentInventory.identification
            && currentInventory.identification.mac;
        if (mac) {
            url += "&mac=" + encodeURIComponent(mac);
        }

        const report = await apiPost(url);
        renderEfuses(report);
        setStatus("eFuses lues sur la carte.");
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        setStatus("Lecture des eFuses impossible : " + error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Lire les eFuses";
    }
}

function securityBadge(active, labelOn = "Activé", labelOff = "Désactivé") {
    const cls = active ? "badge-on" : "badge-off";
    const text = active ? labelOn : labelOff;
    return `<span class="badge ${cls}">${text}</span>`;
}

function renderEfuseSecurity(security) {
    const tiles = [
        ["Secure Boot", securityBadge(security.secure_boot),
            "Vérifie la signature du firmware au démarrage."],
        ["Chiffrement Flash",
            securityBadge(security.flash_encryption) +
            ` <small>(${escapeHtml(security.flash_encryption_state)})</small>`,
            "Chiffre le contenu de la Flash."],
        ["USB-JTAG désactivé", securityBadge(security.usb_jtag_disabled),
            "Blocage du débogage matériel via USB-JTAG."],
        ["Mode téléchargement désactivé",
            securityBadge(security.download_mode_disabled),
            "Empêche le reflashage par mode download."],
        ["Téléchargement sécurisé", securityBadge(security.secure_download),
            "UART download chiffré uniquement."],
        ["Version sécurisée",
            `<strong>${escapeHtml(security.secure_version)}</strong>`,
            "Compteur anti-rollback (ESP-IDF)."],
        ["Clés provisionnées",
            `<strong>${security.keys_used.length}</strong> / 6`,
            "Emplacements de clés utilisés (hors USER)."]
    ];

    const cards = tiles.map(([label, value, hint]) => `
        <div class="efuse-tile">
            <div class="efuse-tile-label">${escapeHtml(label)}</div>
            <div class="efuse-tile-value">${value}</div>
            <div class="efuse-tile-hint">${escapeHtml(hint)}</div>
        </div>
    `).join("");

    return `
        <h3>Sécurité</h3>
        <div class="efuse-tiles">${cards}</div>
    `;
}

function renderEfuseIdentity(identity) {
    const rows = [
        ["Révision du silicium", identity.revision],
        ["Version package", identity.pkg_version],
        ["Version bloc calibration", identity.blk_version_major],
        ["Capacité PSRAM (eFuse)", identity.psram_cap],
        ["Capacité Flash (eFuse)", identity.flash_cap],
        ["Calibration température",
            identity.temp_calib != null ? identity.temp_calib + " °C" : null]
    ];

    const cards = rows.map(([label, value]) => `
        <div class="efuse-tile">
            <div class="efuse-tile-label">${escapeHtml(label)}</div>
            <div class="efuse-tile-value">
                <strong>${escapeHtml(orPlaceholder(value))}</strong>
            </div>
        </div>
    `).join("");

    const uniqueId = identity.optional_unique_id
        ? `<div class="efuse-unique">
               <div class="efuse-tile-label">Identifiant unique 128 bits</div>
               <code>${escapeHtml(identity.optional_unique_id)}</code>
           </div>`
        : "";

    return `
        <h3>Identité du silicium</h3>
        <div class="efuse-tiles">${cards}</div>
        ${uniqueId}
    `;
}

function renderEfuseMacs(identity) {
    const derived = identity.derived_macs || {};

    const rows = Object.entries(derived).map(([key, mac]) => `
        <tr>
            <td>${escapeHtml(MAC_LABELS[key] || key)}</td>
            <td><code>${escapeHtml(mac)}</code></td>
        </tr>
    `).join("");

    if (!rows) {
        return "";
    }

    return `
        <h3>Adresses MAC universelles</h3>
        <p class="note">
            Dérivées de la MAC de base gravée en eFuse
            (${escapeHtml(orPlaceholder(identity.mac))}).
        </p>
        <table class="efuse-mac-table">
            <thead><tr><th>Interface</th><th>Adresse</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

function renderEfuseCategories(report) {
    const labels = report.category_labels || {};
    const categories = report.categories || {};

    return Object.entries(categories).map(([category, fields]) => {
        const rows = fields.map(field => {
            const value = field.readable === false
                ? "<em>protégé (non lisible)</em>"
                : `<strong>${escapeHtml(orPlaceholder(field.value))}</strong>`;

            return `
                <tr>
                    <td><code>${escapeHtml(field.name)}</code></td>
                    <td>${value}</td>
                    <td>${escapeHtml(field.description || "")}</td>
                    <td><code>${escapeHtml(orPlaceholder(field.raw_value))}</code></td>
                </tr>
            `;
        }).join("");

        const label = labels[category] || category;

        return `
            <details class="efuse-category">
                <summary>${escapeHtml(label)} — ${fields.length} champs</summary>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>eFuse</th>
                                <th>Valeur</th>
                                <th>Description</th>
                                <th>Brut</th>
                            </tr>
                        </thead>
                        <tbody>${rows}</tbody>
                    </table>
                </div>
            </details>
        `;
    }).join("");
}

function renderEfuses(report) {
    const container = document.getElementById("efuse-content");

    container.innerHTML = `
        <div class="panel">
            ${renderEfuseSecurity(report.security || {})}
        </div>
        <div class="panel">
            ${renderEfuseIdentity(report.identity || {})}
            ${renderEfuseMacs(report.identity || {})}
        </div>
        <div class="panel">
            <h3>Toutes les eFuses (${report.count})</h3>
            <p class="note">
                Lecture seule. Aucune eFuse n'a été ni ne sera modifiée.
            </p>
            ${renderEfuseCategories(report)}
        </div>
    `;

    container.querySelectorAll("details").forEach(detail => {
        detail.open = false;
    });
}
