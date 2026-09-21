/* ==========================================================================
   ESP32-Lab - accès à l'API HTTP
   ========================================================================== */

/**
 * Charge, depuis la base (par MAC de la carte affichée), la dernière lecture
 * d'une section (efuse, sfdp, partitions, nvs, inventory). Renvoie l'objet
 * reading, ou null si rien en base. Lève une erreur explicite si aucune carte
 * n'est identifiée. Permet de réafficher ces données sur un autre poste, sans
 * la carte branchée.
 */
async function loadStoredReading(section) {
    const mac = currentInventory && currentInventory.identification
        && currentInventory.identification.mac;

    if (!mac) {
        throw new Error(
            "Aucune carte identifiée. Affichez d'abord une carte (onglet " +
            "Général : « Actualiser les ports » ou « Scanner la carte »)."
        );
    }

    const result = await apiGet(
        "/api/db/reading?mac=" + encodeURIComponent(mac) +
        "&section=" + encodeURIComponent(section)
    );
    return result.reading || null;
}

/** GET JSON. Lève une erreur si la réponse n'est pas OK. */
async function apiGet(path) {
    const response = await fetch(path);

    if (!response.ok) {
        let message = `Erreur HTTP ${response.status}`;

        try {
            const body = await response.json();
            if (body && body.message) {
                message = body.message;
            }
        } catch (error) {
            /* Corps non JSON : on conserve le message par défaut. */
        }

        throw new Error(message);
    }

    return response.json();
}

/** POST JSON (corps optionnel). Renvoie le corps décodé. */
async function apiPost(path, body = null) {
    const options = { method: "POST" };

    if (body !== null) {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(body);
    }

    const response = await fetch(path, options);
    const result = await response.json();

    if (!response.ok || result.status === "error") {
        throw new Error(result.message || `Erreur HTTP ${response.status}`);
    }

    return result;
}
