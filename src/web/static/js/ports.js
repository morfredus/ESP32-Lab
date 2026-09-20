/* ==========================================================================
   ESP32-Lab — détection et sélection des ports série
   ========================================================================== */

async function loadPorts() {
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
        updatePortDetails();

        setStatus(`${detectedPorts.length} port(s) USB détecté(s).`);
    } catch (error) {
        setStatus(error.message, true);
    } finally {
        refreshPortsButton.disabled = false;
        refreshPortsButton.textContent = "Actualiser les ports";
    }
}

function updatePortDetails() {
    const selectedPort = portSelect.value;
    const port = detectedPorts.find(item => item.device === selectedPort);

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
