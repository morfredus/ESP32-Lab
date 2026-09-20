/* ==========================================================================
   ESP32-Lab — état applicatif partagé et références DOM
   ========================================================================== */

/* Références DOM globales (les scripts sont chargés en fin de <body>,
   le DOM est donc déjà analysé). */
const statusElement = document.getElementById("status");
const contentElement = document.getElementById("content");
const portSelect = document.getElementById("port-select");
const portDetailsElement = document.getElementById("port-details");
const refreshButton = document.getElementById("refresh-button");
const refreshPortsButton = document.getElementById("refresh-ports-button");
const compareButton = document.getElementById("compare-button");
const selectionInfo = document.getElementById("selection-info");
const historyContent = document.getElementById("history-content");
const comparisonContent = document.getElementById("comparison-content");

/* État mutable partagé entre modules. */
let detectedPorts = [];
let currentInventory = null;
let historyData = [];
let historyByMac = {};
let devicesData = [];
let selectedHistoryIndexes = new Set();
let historyModalSelectedIndexes = new Set();
let showDifferencesOnly = false;

/** Affiche un message dans la bannière de statut. */
function setStatus(message, isError = false) {
    statusElement.className = isError ? "error" : "status";
    statusElement.textContent = message;
}
