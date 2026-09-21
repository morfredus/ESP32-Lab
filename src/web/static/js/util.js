/* ==========================================================================
   ESP32-Lab - utilitaires communs
   ========================================================================== */

const PLACEHOLDER = " - ";

/** Échappe une chaîne pour une insertion HTML sûre. */
function escapeHtml(value) {
    if (value === null || value === undefined) {
        return PLACEHOLDER;
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

/** Formate une date ISO en date/heure locale française. */
function formatDateTime(value) {
    if (!value) {
        return PLACEHOLDER;
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return new Intl.DateTimeFormat("fr-FR", {
        dateStyle: "medium",
        timeStyle: "short"
    }).format(date);
}

/** Ajoute une unité à une valeur, ou renvoie le placeholder si vide. */
function formatUnit(value, unit) {
    if (value === null || value === undefined || value === "") {
        return PLACEHOLDER;
    }

    return `${value} ${unit}`;
}

/** Renvoie une valeur affichable, ou le placeholder si vide. */
function orPlaceholder(value) {
    if (value === null || value === undefined || value === "") {
        return PLACEHOLDER;
    }

    return value;
}

/** Formate un nombre d'octets en Ko / Mo (base 1024, style « MiB »). */
function formatBytes(bytes) {
    if (bytes === null || bytes === undefined) {
        return PLACEHOLDER;
    }

    if (bytes >= 1024 * 1024) {
        return (bytes / (1024 * 1024))
            .toFixed(3)
            .replace(/\.?0+$/, "")
            .replace(".", ",") + " Mio";
    }

    if (bytes >= 1024) {
        return Math.round(bytes / 1024) + " Kio";
    }

    return bytes + " o";
}

/** Formate un entier en hexadécimal 0x000000. */
function formatHex(value) {
    return "0x" + Number(value).toString(16).toUpperCase().padStart(6, "0");
}

/* Codes de type NVS ESP-IDF : [libellé, taille octets, signé]. Le rapport
   ne nomme pas tous ces codes ; on décode donc à partir du code brut. */
const NVS_INT_TYPES = {
    0x01: [1, false],  // U8
    0x11: [1, true],   // I8
    0x02: [2, false],  // U16
    0x12: [2, true],   // I16
    0x04: [4, false],  // U32
    0x14: [4, true],   // I32
    0x08: [8, false],  // U64
    0x18: [8, true]    // I64
};

const NVS_TYPE_STR = 0x21;
const NVS_TYPE_BLOB = 0x41;
const NVS_TYPE_BLOB_DATA = 0x42;
const NVS_TYPE_BLOB_IDX = 0x48;

/**
 * Décode une entrée NVS en valeur lisible.
 * - entiers (u8..i64) : valeur entière little-endian ;
 * - chaîne : longueur déclarée ;
 * - blob : taille du binaire ;
 * - type inconnu / donnée absente : placeholder.
 * Le décodage s'appuie en priorité sur le code de type brut (`type_raw`),
 * plus fiable que le libellé `type_name` (souvent « unknown » dans le rapport).
 */
function decodeNvsHuman(decoded) {
    if (!decoded) {
        return PLACEHOLDER;
    }

    const hex = String(decoded.data_hex || "").replace(/[^0-9a-f]/gi, "");
    if (!hex) {
        return PLACEHOLDER;
    }

    const bytes = hex.match(/../g).map(pair => parseInt(pair, 16));

    const intLE = (count, signed) => {
        let value = 0n;
        for (let i = 0; i < count && i < bytes.length; i++) {
            value |= BigInt(bytes[i]) << BigInt(8 * i);
        }
        if (signed) {
            const bits = BigInt(8 * count);
            const half = 1n << (bits - 1n);
            if (value >= half) {
                value -= 1n << bits;
            }
        }
        return value.toString();
    };

    const sizeLE16 = () => bytes[0] | (bytes[1] << 8);
    const sizeLE32 = () =>
        bytes[0] | (bytes[1] << 8) | (bytes[2] << 16) | (bytes[3] << 24);

    // Code de type brut (ex. "0x14"), prioritaire.
    let typeRaw = null;
    if (decoded.type_raw !== undefined && decoded.type_raw !== null) {
        typeRaw = parseInt(String(decoded.type_raw), 16);
    }

    if (typeRaw !== null) {
        if (NVS_INT_TYPES[typeRaw]) {
            const [count, signed] = NVS_INT_TYPES[typeRaw];
            return intLE(count, signed);
        }
        if (typeRaw === NVS_TYPE_STR) {
            return `chaîne (${sizeLE16()} octets)`;
        }
        if (typeRaw === NVS_TYPE_BLOB || typeRaw === NVS_TYPE_BLOB_DATA) {
            return `binaire (${sizeLE16()} octets)`;
        }
        if (typeRaw === NVS_TYPE_BLOB_IDX) {
            return `binaire (${sizeLE32()} octets)`;
        }
    }

    // Repli sur le libellé de type si le code brut est absent/inconnu.
    const name = String(decoded.type_name || "").toLowerCase();
    switch (name) {
        case "u8": return intLE(1, false);
        case "i8": return intLE(1, true);
        case "u16": return intLE(2, false);
        case "i16": return intLE(2, true);
        case "u32": return intLE(4, false);
        case "i32": return intLE(4, true);
        case "u64": return intLE(8, false);
        case "i64": return intLE(8, true);
        case "str":
        case "string": return `chaîne (${sizeLE16()} octets)`;
        case "blob":
        case "blob_data":
        case "blob_idx": return `binaire (${sizeLE16()} octets)`;
        default: return PLACEHOLDER;
    }
}

/* --- Catalogue Flash (miroir léger de core/flash_catalog.py) --------------- */

const FLASH_MANUFACTURERS = {
    "EF": "Winbond", "C8": "GigaDevice", "68": "Boya (BoHong)",
    "20": "XMC / Micron", "5E": "Zbit", "0B": "XTX", "85": "Puya",
    "1C": "EON", "C2": "Macronix", "9D": "ISSI", "A1": "Fudan (FM)",
    "51": "GigaDevice", "D8": "GigaDevice"
};

const FLASH_DEVICES = {
    "4014": "W25Q80 (1 Mo)", "4015": "W25Q16 (2 Mo)",
    "4016": "W25Q32 (4 Mo)", "4017": "W25Q64 (8 Mo)",
    "4018": "W25Q128 / BY25Q128 (16 Mo)", "4019": "W25Q256 (32 Mo)",
    "7018": "GD25Q128 (16 Mo)"
};

function normalizeFlashId(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value).trim().toUpperCase().replace(/^0X/, "");
}

function flashManufacturerLabel(value) {
    const id = normalizeFlashId(value);
    if (!id) {
        return PLACEHOLDER;
    }
    const name = FLASH_MANUFACTURERS[id];
    return name ? `${name} (ID ${id})` : `Inconnu (ID ${id})`;
}

function flashDeviceLabel(value) {
    const id = normalizeFlashId(value);
    if (!id) {
        return PLACEHOLDER;
    }
    const name = FLASH_DEVICES[id];
    return name ? `${name} (ID ${id})` : `Inconnu (ID ${id})`;
}
