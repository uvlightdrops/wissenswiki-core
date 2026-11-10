"use strict";

const ATTRIBUTE_GROUPS = [
    {id: "object", label: "Eigenschaften der Auswahl"},
    {id: "document", label: "Dokumentkontext"},
    {id: "storage", label: "Ablage und Technik"}
];

function flattenAttributes(value, prefix = "", result = {}) {
    for (const [key, item] of Object.entries(value || {})) {
        const name = prefix ? prefix + "." + key : key;
        if (item && typeof item === "object" && !Array.isArray(item)) {
            if (Object.keys(item).length) flattenAttributes(item, name, result);
            else result[name] = "{}";
        } else {
            result[name] = item === null ? "null" : typeof item === "object" ? JSON.stringify(item) : String(item);
        }
    }
    return result;
}
function attributeShortName(name) { return name.split(".").pop(); }
function attributeGroup(name) {
    if (name === "dokument_metadaten" || name.startsWith("dokument_metadaten.")) return "document";
    if (["datei", "ordner", "revision"].includes(name)) return "storage";
    return "object";
}
function attributeSettingsKey(domainName, version = 2) {
    return `wissenswiki.attributes.v${version}.` + (domainName ? "domain." + domainName : "wiki");
}
function stringList(value) {
    return Array.isArray(value) && value.every(item => typeof item === "string");
}
function loadAttributeSettings(domainName) {
    const stored = JSON.parse(localStorage.getItem(attributeSettingsKey(domainName)) || "null");
    if (stored === null) {
        const legacy = JSON.parse(localStorage.getItem(attributeSettingsKey(domainName, 1)) || "null");
        if (legacy === null) return {preset: "block", hidden: []};
        if (!legacy || !stringList(legacy.hidden)) {
            throw new Error("Ungültiges Format der bisherigen Attributeinstellungen");
        }
        return {preset: "custom", hidden: [], legacyHidden: legacy.hidden};
    }
    if (!stored || !["block", "all", "custom"].includes(stored.preset) || !stringList(stored.hidden)) {
        throw new Error("Ungültiges Format der Attributeinstellungen");
    }
    return {preset: stored.preset, hidden: stored.hidden};
}
function attributeVisible(name, settings) {
    if (settings.preset === "block") return attributeGroup(name) === "object";
    if (settings.preset === "all") return true;
    return !settings.hidden.includes(name) && !(settings.legacyHidden || []).includes(attributeShortName(name));
}
function customAttributeSettings(settings, names) {
    return {preset: "custom", hidden: [...new Set([
        ...settings.hidden.filter(name => !names.has(name)),
        ...[...names].filter(name => !attributeVisible(name, settings))
    ])]};
}
function saveAttributeSettings(domainName, settings) {
    localStorage.setItem(attributeSettingsKey(domainName), JSON.stringify({
        preset: settings.preset, hidden: [...settings.hidden].sort()
    }));
}
