"use strict";
const apiUrl = document.querySelector('meta[name="wissenswiki-api"]').content;

const domain = new URLSearchParams(location.search).get("domain") || "";
const status = document.getElementById("status");
const options = document.getElementById("attribute-options");
const graphHeight = document.getElementById("graph-height");
const graphHeightValue = document.getElementById("graph-height-value");
const graphSettingsKey = "wissenswiki.graph.v1." + (domain ? "domain." + domain : "wiki");
const showBlock = document.getElementById("show-block");
const showAll = document.getElementById("show-all");
const showNone = document.getElementById("show-none");
const attributeSelection = document.getElementById("attribute-selection");
let names = new Set();
let attributeSettings = {preset: "block", hidden: []};

const backLink = document.getElementById("back-link");
backLink.href = backLink.getAttribute("href") + location.search;

function defaultGraphHeight() {
    return matchMedia("(max-width: 800px)").matches ? 60 : 75;
}
function readGraphSettings() {
    const stored = JSON.parse(localStorage.getItem(graphSettingsKey) || "{}");
    if (!stored || typeof stored !== "object" || Array.isArray(stored)) {
        throw new Error("Ungültiges Format der Ansichtseinstellungen");
    }
    return stored;
}
function showGraphHeight(value) {
    graphHeight.value = String(value);
    graphHeightValue.value = `${value} vh`;
}
function saveGraphHeight(value) {
    try {
        const settings = readGraphSettings();
        settings.graphHeight = value;
        localStorage.setItem(graphSettingsKey, JSON.stringify(settings));
        showGraphHeight(value);
        status.textContent = "Höhe der Netzansicht gespeichert.";
    } catch (error) {
        status.textContent = `Ansichtseinstellungen konnten nicht gespeichert werden: ${error.message}`;
    }
}
try {
    const settings = readGraphSettings();
    const height = settings.graphHeight;
    showGraphHeight(Number.isInteger(height) && height >= 30 && height <= 100
        ? height : defaultGraphHeight());
} catch (error) {
    showGraphHeight(defaultGraphHeight());
    status.textContent = `Ansichtseinstellungen konnten nicht gelesen werden: ${error.message}`;
}
graphHeight.addEventListener("input", () => saveGraphHeight(Number(graphHeight.value)));
document.getElementById("reset-graph-height").addEventListener("click", () => {
    try {
        const settings = readGraphSettings();
        delete settings.graphHeight;
        localStorage.setItem(graphSettingsKey, JSON.stringify(settings));
        showGraphHeight(defaultGraphHeight());
        status.textContent = "Responsive Standardhöhe wiederhergestellt.";
    } catch (error) {
        status.textContent = `Ansichtseinstellungen konnten nicht gespeichert werden: ${error.message}`;
    }
});

function reflectAttributeSelection() {
    const none = names.size > 0 && [...names].every(name => !attributeVisible(name, attributeSettings));
    showBlock.setAttribute("aria-pressed", String(attributeSettings.preset === "block"));
    showAll.setAttribute("aria-pressed", String(attributeSettings.preset === "all"));
    showNone.setAttribute("aria-pressed", String(none));
    attributeSelection.textContent = none ? "Keine"
        : {block: "Nur Blockattribute", all: "Alle Attribute", custom: "Benutzerdefiniert"}[attributeSettings.preset];
}
function renderAttributes() {
    options.replaceChildren();
    reflectAttributeSelection();
    for (const group of ATTRIBUTE_GROUPS) {
        const groupNames = [...names].filter(name => attributeGroup(name) === group.id).sort();
        if (!groupNames.length) continue;
        const fieldset = document.createElement("fieldset");
        const legend = document.createElement("legend");
        legend.textContent = group.label;
        fieldset.append(legend);
        for (const name of groupNames) {
            const label = document.createElement("label");
            const box = document.createElement("input");
            box.type = "checkbox"; box.value = name; box.checked = attributeVisible(name, attributeSettings);
            label.title = name;
            label.append(box, " " + name);
            fieldset.append(label);
        }
        options.append(fieldset);
    }
}
function saveAttributes() {
    try {
        saveAttributeSettings(domain, attributeSettings);
        status.textContent = "Gespeichert.";
    } catch (error) {
        status.textContent = `Einstellungen konnten nicht gespeichert werden: ${error.message}`;
    }
}
async function load() {
    const response = await fetch(apiUrl + (domain ? "?domain=" + encodeURIComponent(domain) : ""));
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Blöcke konnten nicht geladen werden.");
    names = new Set();
    for (const block of result.blocks) {
        for (const name of Object.keys(flattenAttributes(block.attributes))) {
            names.add(name);
        }
    }
    try { attributeSettings = loadAttributeSettings(domain); }
    catch (error) {
        status.textContent = `Gespeicherte Einstellungen nicht lesbar, Standard angezeigt: ${error.message}`;
    }
    renderAttributes();
    showBlock.disabled = false;
    showAll.disabled = false;
    showNone.disabled = false;
    if (!names.size) status.textContent = "Keine Attribute vorhanden.";
}
options.addEventListener("change", () => {
    const hidden = new Set(customAttributeSettings(attributeSettings, names).hidden);
    for (const box of options.querySelectorAll("input")) {
        if (box.checked) hidden.delete(box.value);
        else hidden.add(box.value);
    }
    attributeSettings = {preset: "custom", hidden: [...hidden]};
    reflectAttributeSelection();
    saveAttributes();
});
for (const [button, preset] of [[showBlock, "block"], [showAll, "all"]]) {
    button.addEventListener("click", () => {
        attributeSettings = {preset, hidden: attributeSettings.hidden};
        renderAttributes(); saveAttributes();
    });
}
showNone.addEventListener("click", () => {
    attributeSettings = {preset: "custom", hidden: [...new Set([...attributeSettings.hidden, ...names])]};
    renderAttributes(); saveAttributes();
});
load().catch(error => { status.textContent = error.message; });
