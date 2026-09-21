/* ==========================================================================
   ESP32-Lab - table de partitions Flash (lecture réelle sur la carte)
   ========================================================================== */

/** Recharge la table de partitions depuis la base, par MAC affichée. */
async function loadPartitionsFromDb() {
    const button = document.getElementById("partitions-db-button");
    const container = document.getElementById("partitions-content");

    button.disabled = true;
    button.textContent = "Chargement...";

    try {
        const reading = await loadStoredReading("partitions");
        if (reading && reading.payload && reading.payload.partitions) {
            renderPartitions(reading.payload.partitions, currentInventory);
            setStatus(
                "Table de partitions chargée depuis la base (lecture du " +
                formatDateTime(reading.recorded_at) + ")."
            );
        } else {
            container.innerHTML =
                '<div class="empty">Aucune table de partitions en base pour ' +
                'cette carte. Branche-la puis clique « Lire la table de ' +
                'partitions ».</div>';
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

/* Couleurs par sous-type de partition. */
const PARTITION_COLORS = {
    nvs: "#93c5fd",
    nvs_keys: "#bfdbfe",
    ota: "#c4b5fd",
    otadata: "#c4b5fd",
    phy: "#a5b4fc",
    factory: "#86efac",
    ota_0: "#86efac",
    ota_1: "#4ade80",
    coredump: "#fca5a5",
    spiffs: "#fcd34d",
    littlefs: "#fbbf24",
    fat: "#fdba74"
};

function partitionColor(subtype, index) {
    if (PARTITION_COLORS[subtype]) {
        return PARTITION_COLORS[subtype];
    }
    const fallback = ["#a3a3a3", "#d4d4d4", "#94a3b8", "#cbd5e1"];
    return fallback[index % fallback.length];
}

async function loadPartitions() {
    const button = document.getElementById("partitions-button");
    const container = document.getElementById("partitions-content");

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
    button.textContent = "Lecture en cours...";
    container.innerHTML =
        '<div class="empty">Lecture de la table de partitions ' +
        '(cela redémarre brièvement la carte)...</div>';

    try {
        let url = "/api/partitions?port=" + encodeURIComponent(selectedPort);
        if (chip) {
            url += "&chip=" + encodeURIComponent(chip);
        }
        const mac = currentInventory && currentInventory.identification
            && currentInventory.identification.mac;
        if (mac) {
            url += "&mac=" + encodeURIComponent(mac);
        }

        const result = await apiPost(url);
        renderPartitions(result.partitions, currentInventory);
        setStatus("Table de partitions lue sur la carte.");
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        setStatus("Lecture des partitions impossible : " + error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Lire la table de partitions";
    }
}

function renderPartitions(partitions, inventory) {
    const container = document.getElementById("partitions-content");

    if (!partitions || partitions.length === 0) {
        container.innerHTML =
            '<div class="empty">Aucune partition détectée.</div>';
        return;
    }

    /* Échelle : dernière fin de partition, ou taille Flash détectée. */
    const flashMb = inventory
        && inventory.identification
        && inventory.identification.flash_size_mb;
    const flashBytes = flashMb ? flashMb * 1024 * 1024 : null;
    const lastEnd = Math.max(...partitions.map(part => part.end));
    const scale = flashBytes && flashBytes >= lastEnd ? flashBytes : lastEnd;

    const chip = inventory && inventory.identification
        ? inventory.identification.chip : null;

    const segments = partitions.map((part, index) => {
        const width = (part.size / scale) * 100;
        const color = partitionColor(part.subtype, index);
        return `
            <div class="flash-partition-segment"
                 style="width:${width}%;background:${color}"
                 title="${escapeHtml(part.label)} - ${formatHex(part.offset)} - ${escapeHtml(formatBytes(part.size))}">
                <span>${escapeHtml(part.label)}</span>
            </div>
        `;
    }).join("");

    const rows = partitions.map((part, index) => {
        const color = partitionColor(part.subtype, index);
        return `
            <tr>
                <td>
                    <span class="flash-partition-color" style="background:${color}"></span>
                    ${escapeHtml(part.label)}
                </td>
                <td><code>${formatHex(part.offset)}</code></td>
                <td>${escapeHtml(formatBytes(part.size))}</td>
                <td>${escapeHtml(part.type)} (${escapeHtml(part.subtype)})</td>
                <td><code>${formatHex(part.end)}</code></td>
                <td>${part.encrypted ? "Oui" : "Non"}</td>
            </tr>
        `;
    }).join("");

    container.innerHTML = `
        <p>
            ${chip ? escapeHtml(chip) + " - " : ""}
            Flash détectée : <strong>${flashMb ? flashMb + " Mo" : "inconnue"}</strong>.
            Table réellement lue sur la carte à l'adresse <code>0x8000</code>.
        </p>

        <div class="flash-partition-bar">${segments}</div>

        <table class="flash-partition-legend">
            <thead>
                <tr>
                    <th>Partition</th>
                    <th>Adresse</th>
                    <th>Taille</th>
                    <th>Type</th>
                    <th>Fin</th>
                    <th>Chiffrée</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}
