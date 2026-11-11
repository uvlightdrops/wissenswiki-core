"use strict";
const assert = require("node:assert/strict");
const {test} = require("node:test");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");
const source = readFileSync(join(__dirname, "../wissenswiki_core/static/wissenswiki/graph.js"), "utf8");
const populate = source.slice(source.indexOf("function populateRelations("), source.indexOf("async function action("));

class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.style = {}; }
    append(...children) { this.children.push(...children); for (const child of children) child.parent = this; }
    remove() { this.parent.children = this.parent.children.filter(child => child !== this); }
    querySelectorAll(selector) {
        if (selector === ".relation-type") return this.children.filter(child => child.className === "relation-type");
        return this.children.flatMap(child => child.children || []).filter(child =>
            child.tag === "input" && child.name === "relation-type");
    }
}
function render(catalog, used = [], selected = "") {
    const legend = new Element("fieldset"), connect = new Element("button");
    if (selected) {
        const line = new Element("label"), radio = new Element("input");
        line.className = "relation-type";
        radio.name = "relation-type"; radio.value = selected; radio.checked = true;
        line.append(radio); legend.append(line);
    }
    const colors = Object.create(null);
    const context = vm.createContext({colors, blocks:[{relations:used.map(type => ({type}))}],
        document: {
            querySelector: selector => selector === "fieldset.legend" ? legend :
                legend.querySelectorAll("input").find(radio => radio.checked),
            createElement: tag => new Element(tag),
            createTextNode: text => ({text}),
            getElementById: () => connect,
        }});
    vm.runInContext(populate, context);
    context.catalog = catalog;
    vm.runInContext("populateRelations(catalog)", context);
    return {legend, connect, colors, radios:legend.querySelectorAll("input")};
}
const definition = (key, enabled = true, color = "gray") =>
    ({key, label:key.toUpperCase(), description:`Ausgang → Ziel: ${key}`, color, enabled});

test("all usable definitions appear even unused, legacy used definitions are read-only", () => {
    const {legend, radios, connect, colors} = render(
        [definition("reference", true, "#123abc"), definition("disabled", false, "red")],
        ["disabled", "unknown"]);
    assert.deepEqual(radios.map(radio => radio.value), ["reference"]);
    assert.equal(radios[0].checked, true);
    assert.equal(connect.disabled, false);
    assert.equal(legend.children.length, 3);
    assert.equal(legend.children[0].title, "Ausgang → Ziel: reference");
    assert.equal(legend.children[0].style.color, "#123abc");
    assert.equal(legend.children[1].children[0].text, " DISABLED (disabled) – nur lesbar");
    assert.equal(colors.disabled, "red");
    assert.equal(colors.unknown, "gray");
});

test("unused disabled types are omitted, selection survives reload and switches safely", () => {
    const result = render([definition("a"), definition("b"), definition("off", false)], [], "b");
    assert.equal(result.legend.children.length, 2);
    assert.deepEqual(result.radios.map(radio => radio.checked), [false, true]);
    const switched = render([definition("a"), definition("b", false)], ["b"], "b");
    assert.equal(switched.radios[0].checked, true);
});

test("no enabled choices disables connect while keeping legacy edges readable", () => {
    const result = render([definition("old", false)], ["old", "unknown"], "old");
    assert.equal(result.connect.disabled, true);
    assert.equal(result.radios.length, 0);
    assert.equal(result.legend.children.length, 2);
    assert.match(source, /if \(!relation\) throw new Error\("Keine aktivierten Beziehungstypen verfügbar."\)/);
});
