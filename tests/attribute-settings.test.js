"use strict";
const assert = require("node:assert/strict");
const {test} = require("node:test");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");
const scripts = join(__dirname, "../wissenswiki_core/static/wissenswiki");

function context(entries = {}) {
    const storage = new Map(Object.entries(entries));
    const ctx = vm.createContext({
        localStorage: {
            getItem: key => storage.get(key) ?? null,
            setItem: (key, value) => storage.set(key, value)
        }
    });
    vm.runInContext(readFileSync(join(scripts, "attribute-settings.js"), "utf8"), ctx);
    return {ctx, storage, run: code => vm.runInContext(code, ctx)};
}

test("block preset excludes document and storage context, but keeps own wiki metadata", () => {
    const {run} = context();
    assert.equal(run('loadAttributeSettings("Doku").preset'), "block");
    for (const name of ["art", "block_id", "metadaten.status", "metadaten.project"]) {
        assert.equal(run(`attributeVisible("${name}", loadAttributeSettings("Doku"))`), true);
    }
    for (const name of ["datei", "ordner", "revision", "dokument_metadaten", "dokument_metadaten.status"]) {
        assert.equal(run(`attributeVisible("${name}", loadAttributeSettings("Doku"))`), false);
        assert.equal(run(`attributeVisible("${name}", {preset: "all", hidden: ["${name}"]})`), true);
    }
});

test("custom settings use full paths and round-trip independently per domain", () => {
    const {run} = context();
    run('saveAttributeSettings("Doku", {preset: "custom", hidden: ["dokument_metadaten.status"]})');
    assert.equal(run('attributeVisible("metadaten.status", loadAttributeSettings("Doku"))'), true);
    assert.equal(run('attributeVisible("dokument_metadaten.status", loadAttributeSettings("Doku"))'), false);
    assert.equal(run('loadAttributeSettings("Andere").preset'), "block");
    assert.equal(run('loadAttributeSettings("").preset'), "block");
    run('saveAttributeSettings("", {preset: "all", hidden: []})');
    assert.equal(run('loadAttributeSettings("").preset'), "all");
    assert.equal(run('loadAttributeSettings("Doku").preset'), "custom");
});

test("legacy short names retain their effect until explicitly edited", () => {
    const {run, storage} = context({
        "wissenswiki.attributes.v1.domain.Doku": '{"hidden":["status","art"]}'
    });
    for (const name of ["metadaten.status", "dokument_metadaten.status", "art"]) {
        assert.equal(run(`attributeVisible("${name}", loadAttributeSettings("Doku"))`), false);
    }
    assert.equal(run('attributeVisible("block_id", loadAttributeSettings("Doku"))'), true);
    run(`saveAttributeSettings("Doku", customAttributeSettings(loadAttributeSettings("Doku"),
        new Set(["metadaten.status", "dokument_metadaten.status", "art", "block_id"])))`);
    assert.deepEqual(JSON.parse(storage.get("wissenswiki.attributes.v2.domain.Doku")), {
        preset: "custom", hidden: ["art", "dokument_metadaten.status", "metadaten.status"]
    });
    assert.equal(run('attributeVisible("metadaten.status", loadAttributeSettings("Doku"))'), false);
    assert.equal(storage.get("wissenswiki.attributes.v1.domain.Doku"), '{"hidden":["status","art"]}');
});

test("custom preset starts from current visibility, including after all", () => {
    const {run} = context();
    assert.equal(run(`customAttributeSettings({preset: "all", hidden: ["art", "absent"]},
        new Set(["art", "datei"])).hidden.join(",")`), "absent");
    assert.equal(run(`customAttributeSettings({preset: "block", hidden: []},
        new Set(["art", "datei", "dokument_metadaten.status"])).hidden.sort().join(",")`),
    "datei,dokument_metadaten.status");
});

test("malformed preferences and unavailable storage raise explicit errors", () => {
    for (const value of ["{", "false", '{"preset":"unknown","hidden":[]}',
        '{"preset":"custom","hidden":[7]}', '{"preset":"all"}']) {
        const {run} = context({"wissenswiki.attributes.v2.wiki": value});
        assert.throws(() => run('loadAttributeSettings("")'));
    }
    const {run, ctx} = context({"wissenswiki.attributes.v1.wiki": '{"hidden":42}'});
    assert.throws(() => run('loadAttributeSettings("")'), /bisherigen/);
    ctx.localStorage.setItem = () => { throw new Error("storage blocked"); };
    assert.throws(() => run('saveAttributeSettings("", {preset:"block", hidden:[]})'), /storage blocked/);
});

class Element {
    constructor(tag = "div") {
        this.tag = tag; this.children = []; this.listeners = {}; this.value = "";
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    getAttribute() { return "/graph-header/"; }
    setAttribute(name, value) { this[name] = value; }
    addEventListener(event, listener) { this.listeners[event] = listener; }
    querySelectorAll(tag) {
        return this.children.filter(child => child instanceof Element).flatMap(child =>
            [...(child.tag === tag ? [child] : []), ...child.querySelectorAll(tag)]);
    }
}

async function settingsPage(entries) {
    const state = context(entries);
    const elements = new Map();
    const element = id => {
        if (!elements.has(id)) elements.set(id, new Element());
        return elements.get(id);
    };
    Object.assign(state.ctx, {
        document: {
            getElementById: element,
            querySelector: () => ({content: "/api"}),
            createElement: tag => new Element(tag)
        },
        location: {search: "?domain=Doku"}, URLSearchParams,
        matchMedia: () => ({matches: false}),
        fetch: async () => ({ok: true, json: async () => ({blocks: [
            {attributes: {art: "Abschnitt", block_id: "one", datei: "DOC.md",
                dokument_metadaten: {status: "draft"}}},
            {attributes: {art: "Wiki-Block", metadaten: {status: "active"}}}
        ]})})
    });
    state.run(readFileSync(join(scripts, "settings.js"), "utf8"));
    await new Promise(resolve => setImmediate(resolve));
    return {...state, element};
}

test("settings UI groups provenance, edits collisions separately and preserves graph height", async () => {
    const {element, storage} = await settingsPage({
        "wissenswiki.graph.v1.domain.Doku": '{"graphHeight":85,"color":"folder"}'
    });
    const options = element("attribute-options");
    assert.deepEqual(options.children.map(fieldset => fieldset.children[0].textContent),
        ["Eigenschaften der Auswahl", "Dokumentkontext", "Ablage und Technik"]);
    const boxes = () => options.querySelectorAll("input");
    assert.equal(boxes().find(box => box.value === "metadaten.status").checked, true);
    assert.equal(boxes().find(box => box.value === "dokument_metadaten.status").checked, false);
    assert.equal(element("graph-height").value, "85");
    boxes().find(box => box.value === "metadaten.status").checked = false;
    options.listeners.change();
    assert.equal(element("attribute-selection").textContent, "Benutzerdefiniert");
    assert.equal(element("show-block")["aria-pressed"], "false");
    const key = "wissenswiki.attributes.v2.domain.Doku";
    assert.deepEqual(JSON.parse(storage.get(key)).hidden,
        ["datei", "dokument_metadaten.status", "metadaten.status"]);
    element("show-all").listeners.click();
    assert.ok(boxes().every(box => box.checked));
    assert.equal(element("show-all")["aria-pressed"], "true");
    assert.equal(element("attribute-selection").textContent, "Alle Attribute");
    element("show-none").listeners.click();
    assert.ok(boxes().every(box => !box.checked));
    assert.equal(element("show-none")["aria-pressed"], "true");
    assert.equal(element("attribute-selection").textContent, "Keine");
    element("show-block").listeners.click();
    assert.equal(boxes().find(box => box.value === "block_id").checked, true);
    assert.equal(boxes().find(box => box.value === "dokument_metadaten.status").checked, false);
    assert.equal(element("show-block")["aria-pressed"], "true");
    assert.equal(element("show-none")["aria-pressed"], "false");
    assert.equal(element("attribute-selection").textContent, "Nur Blockattribute");
    boxes().find(box => box.value === "dokument_metadaten.status").checked = true;
    options.listeners.change();
    assert.equal(element("attribute-selection").textContent, "Benutzerdefiniert");
    assert.equal(JSON.parse(storage.get(key)).hidden.includes("dokument_metadaten.status"), false);
    assert.equal(storage.get("wissenswiki.graph.v1.domain.Doku"), '{"graphHeight":85,"color":"folder"}');
});

test("settings UI surfaces read and write errors", async () => {
    const {ctx, element} = await settingsPage({"wissenswiki.attributes.v2.domain.Doku": "{"});
    assert.match(element("status").textContent, /nicht lesbar/);
    ctx.localStorage.setItem = () => { throw new Error("quota"); };
    element("show-none").listeners.click();
    assert.match(element("status").textContent, /nicht gespeichert.*quota/);
});
