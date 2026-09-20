/* ==========================================================================
   ESP32-Lab — inventaire matériel et fiche de la carte
   ========================================================================== */

async function loadInventory() {
    try {
        const response = await fetch("/api/inventory");

        if (response.status === 404) {
            contentElement.innerHTML =
                '<div class="empty">Aucun inventaire. ' +
                'Sélectionne un port puis « Scanner la carte ».</div>';
            return;
        }

        if (!response.ok) {
            throw new Error("Impossible de charger l'inventaire.");
        }

        const inventory = await response.json();
        currentInventory = inventory;
        const info = inventory.identification || {};

        await loadDeviceProfile(info.mac);

        const flashManufacturer = info.flash_manufacturer_name
            || info.flash_manufacturer || PLACEHOLDER;
        const flashDevice = info.flash_device_name
            || info.flash_device || PLACEHOLDER;

        contentElement.innerHTML = `
            <div class="card">
                <h2>Microcontrôleur</h2>
                <div class="value">${escapeHtml(orPlaceholder(info.chip))}</div>
                <div class="detail">Révision : ${escapeHtml(orPlaceholder(info.revision))}</div>
                <div class="detail">CPU : ${escapeHtml(formatUnit(info.cpu_frequency_mhz, "MHz"))}</div>
                <div class="detail">Quartz : ${escapeHtml(formatUnit(info.crystal_frequency_mhz, "MHz"))}</div>
            </div>

            <div class="card">
                <h2>Mémoire Flash</h2>
                <div class="value">${escapeHtml(formatUnit(info.flash_size_mb, "Mo"))}</div>
                <div class="detail">Fabricant : ${escapeHtml(flashManufacturer)}</div>
                <div class="detail">Référence : ${escapeHtml(flashDevice)}</div>
                <div class="detail">Type : ${escapeHtml(orPlaceholder(info.flash_type))}</div>
                <div class="detail">Tension : ${escapeHtml(orPlaceholder(info.flash_voltage))}</div>
            </div>

            <div class="card">
                <h2>PSRAM</h2>
                <div class="value">${escapeHtml(formatUnit(info.psram_size_mb, "Mo"))}</div>
                <div class="detail">${escapeHtml(orPlaceholder(info.psram))}</div>
            </div>

            <div class="card">
                <h2>Connectivité</h2>
                <div class="value">Wi-Fi / Bluetooth</div>
                <div class="detail">MAC : ${escapeHtml(orPlaceholder(info.mac))}</div>
                <div class="detail">${escapeHtml(orPlaceholder(info.features))}</div>
            </div>

            <div class="card">
                <h2>Connexion</h2>
                <div class="value">${escapeHtml(orPlaceholder(inventory.port))}</div>
                <div class="detail">Dernier inventaire : ${escapeHtml(formatDateTime(inventory.timestamp))}</div>
            </div>
        `;
    } catch (error) {
        setStatus(error.message, true);
    }
}

async function refreshInventory() {
    const selectedPort = portSelect.value;

    if (!selectedPort) {
        setStatus("Sélectionne un port série.", true);
        return;
    }

    refreshButton.disabled = true;
    refreshButton.textContent = "Actualisation...";
    setStatus(`Interrogation de ${selectedPort}...`);

    try {
        await apiPost(
            "/api/inventory/refresh?port=" + encodeURIComponent(selectedPort)
        );

        setStatus("Inventaire actualisé avec succès.");

        await loadInventory();
        await loadHistory();
        await loadDevices();
    } catch (error) {
        setStatus(error.message, true);
    } finally {
        refreshButton.disabled = false;
        refreshButton.textContent = "Scanner la carte";
    }
}

/* --- Fiche de la carte ---------------------------------------------------- */

async function loadDeviceProfile(mac) {
    const macElement = document.getElementById("device-mac");
    const nameElement = document.getElementById("device-name");
    const locationElement = document.getElementById("device-location");
    const noteElement = document.getElementById("device-note");

    macElement.textContent = mac || PLACEHOLDER;
    nameElement.value = "";
    locationElement.value = "";
    noteElement.value = "";

    if (!mac) {
        return;
    }

    try {
        const result = await apiGet(
            "/api/device?mac=" + encodeURIComponent(mac)
        );
        const device = result.device;

        if (device) {
            nameElement.value = device.name || "";
            locationElement.value = device.location || "";
            noteElement.value = device.note || "";
        }
    } catch (error) {
        console.error("Erreur lors du chargement de la fiche :", error);
    }
}

async function editDeviceProfile(mac) {
    await loadDeviceProfile(mac);
    showTab("general");

    const macElement = document.getElementById("device-mac");
    macElement.scrollIntoView({ behavior: "smooth", block: "center" });
    document.getElementById("device-name").focus();

    setStatus("Modification de la fiche : " + mac);
}

async function saveDeviceProfile() {
    const mac = document.getElementById("device-mac").textContent;
    const name = document.getElementById("device-name").value;
    const location = document.getElementById("device-location").value;
    const note = document.getElementById("device-note").value;

    if (!mac || mac === PLACEHOLDER) {
        setStatus("Aucune adresse MAC disponible.", true);
        return;
    }

    const button = document.getElementById("save-device-button");
    button.disabled = true;
    button.textContent = "Enregistrement...";

    try {
        await apiPost("/api/device/update", { mac, name, location, note });
        setStatus("Fiche de la carte enregistrée.");
        await loadDevices();
    } catch (error) {
        setStatus(error.message, true);
    } finally {
        button.disabled = false;
        button.textContent = "Enregistrer la fiche";
    }
}
