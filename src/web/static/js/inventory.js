/* ==========================================================================
   ESP32-Lab — inventaire matériel et fiche de la carte
   ========================================================================== */

/** Vide la vue d'inventaire et la fiche (aucune carte affichée). */
function showEmptyInventory(message) {
    currentInventory = null;
    contentElement.innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
    loadDeviceProfile(null);   // réinitialise la fiche (chemin synchrone)
}

/** Déduit la MAC d'un port depuis son numéro de série (USB natif ESP32 = MAC). */
function macFromPort(port) {
    const serial = (port && port.serial_number || "").trim().toLowerCase();
    return /^([0-9a-f]{2}:){5}[0-9a-f]{2}$/.test(serial) ? serial : null;
}

/**
 * Affiche l'inventaire correspondant au port sélectionné, si cette carte a
 * déjà été scannée (base). Sinon, laisse la vue vide.
 */
async function showInventoryForSelectedPort() {
    const port = detectedPorts.find(item => item.device === portSelect.value);
    const mac = port ? macFromPort(port) : null;
    await loadInventory(mac);
}

/**
 * Charge l'inventaire d'une carte depuis la base (par MAC). Sans MAC connue,
 * ou si la carte n'a jamais été scannée, la vue reste vide.
 */
async function loadInventory(mac) {
    if (!mac) {
        showEmptyInventory(
            "Aucune carte affichée. Clique « Actualiser les ports » " +
            "(la dernière analyse s'affiche si la carte a déjà été scannée) " +
            "ou « Scanner la carte »."
        );
        return;
    }

    try {
        const result = await apiGet(
            "/api/db/reading?mac=" + encodeURIComponent(mac) + "&section=inventory"
        );
        const reading = result.reading;

        if (!reading || !reading.payload) {
            showEmptyInventory(
                "Cette carte n'a pas encore été scannée. Clique « Scanner la carte »."
            );
            return;
        }

        renderInventoryCards(reading.payload);
    } catch (error) {
        setStatus(error.message, true);
    }
}

/** Rend les 8 cartes matériel à partir d'un inventaire. */
async function renderInventoryCards(inventory) {
    currentInventory = inventory;
    const info = inventory.identification || {};

    await loadDeviceProfile(info.mac);

    const flashManufacturer = info.flash_manufacturer_name
        || info.flash_manufacturer || PLACEHOLDER;
    const flashDevice = info.flash_device_name
        || info.flash_device || PLACEHOLDER;

    const device = registeredDevice(info.mac) || {};

    // 8 cartes, ordre de lecture : identité -> silicium -> calcul ->
    // stockage // mémoire vive -> radios -> identifiant réseau -> lien.
    contentElement.innerHTML = `
            <div class="card">
                <h2>Carte</h2>
                <div class="value">${escapeHtml(device.name || "Sans nom")}</div>
                <div class="detail">Emplacement : ${escapeHtml(device.location || PLACEHOLDER)}</div>
                <div class="detail">Note : ${escapeHtml(device.note || PLACEHOLDER)}</div>
            </div>

            <div class="card">
                <h2>Microcontrôleur</h2>
                <div class="value">${escapeHtml(orPlaceholder(info.chip))}</div>
                <div class="detail">Révision : ${escapeHtml(orPlaceholder(info.revision))}</div>
                <div class="detail">Famille : ${escapeHtml(orPlaceholder(info.chip_family))}</div>
            </div>

            <div class="card">
                <h2>Processeur</h2>
                <div class="value">${escapeHtml(formatUnit(info.cpu_frequency_mhz, "MHz"))}</div>
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
                <div class="detail">${escapeHtml(orPlaceholder(info.features))}</div>
            </div>

            <div class="card">
                <h2>Adresse MAC</h2>
                <div class="value" style="font-size:19px;word-break:break-all">${escapeHtml(orPlaceholder(info.mac))}</div>
                <div class="detail">Identifiant matériel de base</div>
            </div>

            <div class="card">
                <h2>Connexion</h2>
                <div class="value">${escapeHtml(orPlaceholder(inventory.port))}</div>
                <div class="detail">Dernier inventaire : ${escapeHtml(formatDateTime(inventory.timestamp))}</div>
            </div>
        `;
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
        const result = await apiPost(
            "/api/inventory/refresh?port=" + encodeURIComponent(selectedPort)
        );

        setStatus("Inventaire actualisé avec succès.");

        const scannedMac = result.inventory
            && result.inventory.identification
            && result.inventory.identification.mac;

        // Registre d'abord (noms à jour), puis affichage de la carte scannée
        // et historique, puis registre à nouveau pour le compte de scans.
        await loadDevices();
        if (result.inventory) {
            await renderInventoryCards(result.inventory);
        } else if (scannedMac) {
            await loadInventory(scannedMac);
        }
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
