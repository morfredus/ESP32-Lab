/* ==========================================================================
   ESP32-Lab - analyse de la structure NVS

   Toutes les valeurs affichées proviennent du rapport d'analyse réel
   (data/analysis/reports/nvs_structure_analysis.json). Aucune donnée n'est
   inventée : on indique la présence d'une clé et sa valeur décodée
   lorsqu'elle est disponible, sinon « Non détecté » ou « Présent (non décodé) ».
   ========================================================================== */

const NVS_STATE_LABELS = {
    full: "Pleine",
    active: "Active",
    empty_or_uninitialized: "Non initialisée"
};

async function loadNvsAnalysis() {
    const button = document.getElementById("nvs-button");
    const container = document.getElementById("nvs-content");

    const mac = currentInventory && currentInventory.identification
        && currentInventory.identification.mac;

    button.disabled = true;
    button.textContent = "Chargement...";

    try {
        // Carte identifiée : on privilégie le dernier rapport NVS DE CETTE
        // carte, stocké en base (cohérent, par MAC).
        if (mac) {
            const result = await apiGet(
                "/api/db/reading?mac=" + encodeURIComponent(mac) + "&section=nvs"
            );
            const reading = result.reading;

            if (reading && reading.payload && reading.payload.report) {
                renderNvsReport(reading.payload.report);
                setStatus(
                    "Analyse NVS de la carte chargée depuis la base " +
                    `(lecture du ${formatDateTime(reading.recorded_at)}).`
                );
                return;
            }

            // Aucune donnée NVS en base pour cette carte → on analyse.
            if (portSelect.value) {
                container.innerHTML =
                    '<div class="empty">Aucune analyse NVS en base pour cette ' +
                    'carte - lecture de la carte en cours...</div>';
                await triggerNvsAnalysis();
            } else {
                container.innerHTML =
                    '<div class="empty">Aucune analyse NVS en base pour cette ' +
                    'carte. Sélectionnez un port (onglet Général) puis ' +
                    '« Analyser la NVS de la carte ».</div>';
            }
            return;
        }

        // Aucune carte scannée : on affiche le dernier rapport disponible.
        const result = await apiGet("/api/nvs");
        renderNvsReport(result.report || {});
    } catch (error) {
        if (portSelect.value) {
            container.innerHTML =
                '<div class="empty">Aucun rapport enregistré - analyse de ' +
                'la carte en cours...</div>';
            await triggerNvsAnalysis();
        } else {
            container.innerHTML =
                `<div class="empty">${escapeHtml(error.message)} ` +
                'Scannez une carte (onglet Général) puis relancez l\'analyse NVS.</div>';
        }
    } finally {
        button.disabled = false;
        button.textContent = "Actualiser l'analyse NVS";
    }
}

/** Lit la NVS de la carte connectée et affiche le rapport (lecture seule). */
async function triggerNvsAnalysis() {
    const button = document.getElementById("nvs-analyze-button");
    const container = document.getElementById("nvs-content");

    const selectedPort = portSelect.value;
    if (!selectedPort) {
        setStatus("Sélectionnez un port série (onglet Général).", true);
        return;
    }

    const chip = currentInventory && currentInventory.identification
        && currentInventory.identification.chip_family;
    const mac = currentInventory && currentInventory.identification
        && currentInventory.identification.mac;

    if (button) {
        button.disabled = true;
        button.textContent = "Analyse en cours...";
    }
    container.innerHTML =
        '<div class="empty">Lecture de la partition NVS sur la carte ' +
        '(lecture seule)...</div>';

    try {
        let url = "/api/nvs/analyze?port=" + encodeURIComponent(selectedPort);
        if (chip) {
            url += "&chip=" + encodeURIComponent(chip);
        }
        if (mac) {
            url += "&mac=" + encodeURIComponent(mac);
        }

        const result = await apiPost(url);
        renderNvsReport(result.report || {});
        setStatus("Analyse NVS générée depuis la carte.");
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        setStatus("Analyse NVS impossible : " + error.message, true);
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Analyser la NVS de la carte";
        }
    }
}

/** Rend un rapport NVS complet dans le conteneur dédié. */
function renderNvsReport(report) {
    const container = document.getElementById("nvs-content");
    const pages = report.pages || [];

    const writtenEntries = pages.flatMap(page =>
        (page.entries || [])
            .filter(entry => entry.state
                && entry.state.name === "written" && entry.decoded)
            .map(entry => entry.decoded)
    );

    const orderedDecoded = pages.flatMap(page =>
        (page.entries || []).map(entry => entry.decoded || {})
    );

    container.innerHTML =
        renderNvsSummary(writtenEntries, orderedDecoded) +
        renderNvsMeta(report) +
        renderNvsPages(pages) +
        "<h3>Détail des entrées NVS</h3>" +
        renderNvsDetails(pages) +
        renderNvsLimitations(report);

    container.querySelectorAll("details").forEach(detail => {
        detail.open = false;
    });
}

/**
 * Reconstitue la plus longue chaîne ASCII imprimable d'une entrée blob/str
 * répartie sur plusieurs slots (ex. un SSID Wi-Fi). Retourne null si rien
 * d'exploitable. Le premier slot (32 octets) est l'en-tête : on l'ignore.
 */
const NVS_REDACTED = "<redacted>";
const NVS_NOT_STORED = "(non stocké en base)";

/** Une entrée dont le hex a été caviardé (secret non stocké). */
function nvsIsRedacted(entry) {
    return Boolean(entry) &&
        (entry.data_hex === NVS_REDACTED || entry.raw_hex === NVS_REDACTED);
}

function extractNvsString(ordered, index) {
    const descriptor = ordered[index] || {};
    const span = descriptor.span || 1;

    let hex = "";
    for (let j = index; j < index + span && j < ordered.length; j++) {
        const slotHex = ordered[j].raw_hex || "";
        if (slotHex === NVS_REDACTED) {
            return null;   // hex non stocké : rien à reconstituer
        }
        hex += slotHex;
    }

    const bytes = hex.match(/../g) || [];
    const data = bytes.slice(32);   // ignore le slot descripteur

    let best = "";
    let current = "";
    for (const pair of data) {
        const code = parseInt(pair, 16);
        if (code >= 0x20 && code < 0x7f) {
            current += String.fromCharCode(code);
        } else {
            if (current.length > best.length) {
                best = current;
            }
            current = "";
        }
    }
    if (current.length > best.length) {
        best = current;
    }

    return best.length >= 3 ? best : null;
}

function renderNvsSummary(entries, ordered = []) {
    const byKey = key => entries.find(entry => entry.key === key);
    const has = key => Boolean(byKey(key));

    /* Valeur brute (champ data hexadécimal) telle que stockée. */
    const raw = key => {
        const entry = byKey(key);
        if (!entry) {
            return "Non détecté";
        }
        if (nvsIsRedacted(entry)) {
            return NVS_NOT_STORED;
        }
        return entry.data_hex ? entry.data_hex : "Présent";
    };

    /* Valeur lisible décodée selon le type de l'entrée. */
    const human = key => {
        const entry = byKey(key);
        if (!entry) {
            return "Non détecté";
        }
        if (nvsIsRedacted(entry)) {
            return NVS_NOT_STORED;   // hex caviardé : pas de décodage inventé
        }
        return decodeNvsHuman(entry);
    };

    /* SSID : reconstitution du texte depuis le blob multi-slots. */
    const ssid = key => {
        const index = ordered.findIndex(
            item => item.key === key && item.type_raw === "0x42"
        );
        if (index >= 0) {
            const text = extractNvsString(ordered, index);
            if (text) {
                return `« ${text} »`;
            }
        }
        return human(key);
    };

    const secret = key =>
        has(key) ? "Présent (masqué)" : "Non détecté";

    /* [libellé, valeur brute, valeur lisible] */
    const definitions = [
        ["SSID Wi-Fi station", raw("sta.ssid"), ssid("sta.ssid")],
        ["SSID point d'accès", raw("ap.ssid"), ssid("ap.ssid")],
        ["Mot de passe station", secret("sta.pswd"), secret("sta.pswd")],
        ["Mot de passe point d'accès", secret("ap.passwd"), secret("ap.passwd")],
        ["Canal station", raw("sta.chan"), human("sta.chan")],
        ["Canal point d'accès", raw("ap.chan"), human("ap.chan")],
        ["Compteur de démarrages", raw("bl_boot_count"), human("bl_boot_count")],
        ["Compteur de crashs", raw("bl_crash_count"), human("bl_crash_count")],
        ["Version calibration", raw("cal_version"), human("cal_version")]
    ];

    const rows = definitions.map(([label, rawValue, humanValue]) => `
        <tr>
            <td>${escapeHtml(label)}</td>
            <td><code>${escapeHtml(rawValue)}</code></td>
            <td><strong>${escapeHtml(humanValue)}</strong></td>
        </tr>
    `).join("");

    return `
        <section class="nvs-summary" style="margin-bottom:24px;">
            <h3>Résumé des données détectées</h3>
            <p class="note">
                Valeurs issues du rapport d'analyse réel. La colonne
                « Valeur lisible » décode le type (entier, chaîne, binaire) ;
                les clés absentes du dump sont marquées « Non détecté ».
            </p>
            <table>
                <thead>
                    <tr>
                        <th>Paramètre</th>
                        <th>Valeur brute</th>
                        <th>Valeur lisible</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </section>
    `;
}

function renderNvsLimitations(report) {
    const limitations = report.limitations || [];
    if (!limitations.length) {
        return "";
    }

    const items = limitations
        .map(text => `<li>${escapeHtml(text)}</li>`)
        .join("");

    return `
        <section class="panel" style="margin-top:16px;">
            <h3>Limitations connues de l'analyse</h3>
            <p class="note">
                Ces limites proviennent de l'outil qui a généré le rapport,
                pas d'un défaut de la carte. Elles expliquent notamment les
                CRC « Incohérent » et les caractères binaires : les grandes
                zones (calibration Wi-Fi/RF, PHY) sont des données binaires,
                et les slots de données des blobs sont listés comme des
                entrées à part entière.
            </p>
            <ul>${items}</ul>
        </section>
    `;
}

function renderNvsMeta(report) {
    return `
        <div class="info-grid">
            <div><strong>Fichier :</strong> ${escapeHtml(report.file || PLACEHOLDER)}</div>
            <div><strong>Taille :</strong> ${escapeHtml(report.size_bytes ?? PLACEHOLDER)} octets</div>
            <div><strong>Taille page :</strong> ${escapeHtml(report.page_size_bytes ?? PLACEHOLDER)} octets</div>
            <div><strong>Nombre de pages :</strong> ${escapeHtml(report.page_count ?? PLACEHOLDER)}</div>
        </div>
    `;
}

function renderNvsPages(pages) {
    const rows = pages.map(page => {
        const counts = page.entry_counts || {};
        const stateLabel = NVS_STATE_LABELS[page.state_name]
            || page.state_name || PLACEHOLDER;

        const sequence =
            page.state_name === "empty_or_uninitialized"
                || page.sequence === 4294967295
                ? PLACEHOLDER : page.sequence;

        let crc = PLACEHOLDER;
        if (page.state_name === "empty_or_uninitialized") {
            crc = "Non initialisée";
        } else if (page.header_crc_match === true) {
            crc = "OK";
        } else if (page.header_crc_match === false) {
            crc = "Incohérent";
        }

        return `
            <tr>
                <td>${escapeHtml(page.page_index)}</td>
                <td>${escapeHtml(page.offset || PLACEHOLDER)}</td>
                <td>${escapeHtml(stateLabel)}</td>
                <td>${escapeHtml(sequence)}</td>
                <td>${escapeHtml(counts.written ?? PLACEHOLDER)}</td>
                <td>${escapeHtml(counts.erased ?? PLACEHOLDER)}</td>
                <td>${escapeHtml(counts.empty ?? PLACEHOLDER)}</td>
                <td>${escapeHtml(crc)}</td>
            </tr>
        `;
    }).join("");

    return `
        <div class="panel">
            <table>
                <thead>
                    <tr>
                        <th>Page</th><th>Offset</th><th>État</th><th>Séquence</th>
                        <th>Écrites</th><th>Effacées</th><th>Vides</th><th>CRC header</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    `;
}

function renderNvsDetails(pages) {
    return pages.map(page => {
        const entries = (page.entries || []).filter(
            entry => entry.state && entry.state.name === "written");

        if (entries.length === 0) {
            return `
                <details class="nvs-page-details">
                    <summary>Page ${escapeHtml(page.page_index)} - aucune entrée exploitable</summary>
                </details>
            `;
        }

        const entryRows = entries.map(entry => {
            const decoded = entry.decoded || {};
            const crc = decoded.crc_match === true ? "OK"
                : decoded.crc_match === false ? "Incohérent" : PLACEHOLDER;

            return `
                <tr>
                    <td>${escapeHtml(entry.index ?? PLACEHOLDER)}</td>
                    <td>${escapeHtml(entry.offset || PLACEHOLDER)}</td>
                    <td>${escapeHtml(decoded.key || PLACEHOLDER)}</td>
                    <td>${escapeHtml(decoded.type_name || PLACEHOLDER)}</td>
                    <td>${escapeHtml(decoded.span ?? PLACEHOLDER)}</td>
                    <td>${escapeHtml(crc)}</td>
                    <td><code>${escapeHtml(decoded.data_hex || PLACEHOLDER)}</code></td>
                    <td><strong>${escapeHtml(decodeNvsHuman(decoded))}</strong></td>
                </tr>
            `;
        }).join("");

        return `
            <details class="nvs-page-details">
                <summary>Page ${escapeHtml(page.page_index)} - ${entries.length} entrée(s) écrite(s)</summary>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Index</th><th>Offset</th><th>Clé</th><th>Type</th>
                                <th>Span</th><th>CRC</th><th>Données hexadécimales</th>
                                <th>Valeur lisible</th>
                            </tr>
                        </thead>
                        <tbody>${entryRows}</tbody>
                    </table>
                </div>
            </details>
        `;
    }).join("");
}
