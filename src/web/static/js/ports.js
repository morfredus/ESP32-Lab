/* ==========================================================================
   ESP32-Lab - détection et sélection des ports série
   ========================================================================== */

/**
 * Vide les panneaux liés à une carte précise (eFuses, NVS, SFDP, partitions)
 * pour ne pas laisser les données d'une carte précédente à l'écran après un
 * changement de port ou de carte. Chaque panneau se recharge ensuite, soit en
 * lisant la carte, soit depuis la base (bouton « Charger depuis la base »).
 */
function clearReadPanels() {
    const panels = {
        "efuse-content": "Aucune lecture d'eFuse effectuée.",
        "nvs-content": "Aucune analyse NVS chargée.",
        "flash-sfdp-content": "Aucune lecture SFDP effectuée.",
        "partitions-content": "Aucune table de partitions chargée.",
        "firmware-content": "Aucune lecture firmware effectuée.",
    };
    for (const [id, message] of Object.entries(panels)) {
        const element = document.getElementById(id);
        if (element) {
            element.innerHTML = `<div class="empty">${message}</div>`;
        }
    }
}

/**
 * Détecte les ports. `showInventory` (défaut vrai, cas du bouton « Actualiser
 * les ports ») affiche l'inventaire de la carte connectée si elle a déjà été
 * scannée. Au démarrage on passe `false` : la vue reste vide.
 */
async function loadPorts(showInventory = true) {
    refreshPortsButton.disabled = true;
    refreshPortsButton.textContent = "Recherche...";

    try {
        const result = await apiGet("/api/ports");

        detectedPorts = (result.ports || []).filter(port =>
            port.device.startsWith("/dev/ttyACM") ||
            port.device.startsWith("/dev/ttyUSB") ||
            /^COM\d+/i.test(port.device) ||
            port.vid !== null
        );

        portSelect.innerHTML = "";

        if (detectedPorts.length === 0) {
            portSelect.innerHTML =
                '<option value="">Aucun port USB détecté</option>';
            portDetailsElement.textContent =
                "Aucun périphérique USB disponible.";
            setStatus("Aucun port USB détecté.", true);
            return;
        }

        for (const port of detectedPorts) {
            const option = document.createElement("option");
            option.value = port.device;
            option.textContent =
                `${port.device} - ${port.description || "Sans description"}`;
            portSelect.appendChild(option);
        }

        portSelect.value = detectedPorts[0].device;
        renderPortDetails();

        if (showInventory) {
            // Changement de carte possible : on repart de panneaux propres.
            clearReadPanels();
            if (typeof showInventoryForSelectedPort === "function") {
                await showInventoryForSelectedPort();
            }
        }

        setStatus(`${detectedPorts.length} port(s) USB détecté(s).`);
    } catch (error) {
        setStatus(error.message, true);
    } finally {
        refreshPortsButton.disabled = false;
        refreshPortsButton.textContent = "Actualiser les ports";
    }
}

/** Affiche les détails du port sélectionné (texte uniquement). */
function renderPortDetails() {
    const port = detectedPorts.find(item => item.device === portSelect.value);

    if (!port) {
        portDetailsElement.textContent = "Aucun port sélectionné";
        return;
    }

    portDetailsElement.innerHTML = `
        Fabricant : ${escapeHtml(port.manufacturer || "Inconnu")}<br>
        Produit : ${escapeHtml(port.product || "Inconnu")}<br>
        Numéro de série : ${escapeHtml(port.serial_number || "Inconnu")}<br>
        VID : ${escapeHtml(port.vid ?? "Inconnu")} -
        PID : ${escapeHtml(port.pid ?? "Inconnu")}
    `;
}

/**
 * Changement manuel de port (onchange du menu) : met à jour les détails ET
 * l'inventaire affiché (uniquement sur action de l'utilisateur).
 */
function updatePortDetails() {
    renderPortDetails();
    // Nouvelle carte sélectionnée : on vide les lectures de la précédente.
    clearReadPanels();
    if (typeof showInventoryForSelectedPort === "function") {
        showInventoryForSelectedPort();
    }
}
