"use strict";
const assert = require("node:assert/strict");
const {test} = require("node:test");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");
const asset = name => readFileSync(join(__dirname, "../wissenswiki_core/static/wissenswiki/", name), "utf8");

class Element {
    constructor(tag) { this.tag = tag; this.children = []; this.textContent = ""; }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
}
const document = {
    createElement: tag => new Element(tag),
    createTextNode: text => ({textContent: text}),
};
const block = {
    id: "a", title: "A", text: "**Strong**", text_html: "<p><strong>Strong</strong></p>",
    revision: "1", parts: [], relations: [],
};
const graph = asset("graph.js");
const showContent = graph.slice(graph.indexOf("function showContent("), graph.indexOf("function reflectSelection("));

test("graph content uses sanitized HTML and keeps an explicit plain-text source view", () => {
    const container = new Element("div");
    const context = vm.createContext({document, blocks: [block], source: {value: "a"},
        target: {value: ""}, label: value => value.title, container});
    vm.runInContext(showContent + "\nshowContent(container);", context);
    const [selected, empty] = container.children;
    assert.equal(selected.children[1].tag, "div");
    assert.equal(selected.children[1].innerHTML, block.text_html);
    assert.equal(selected.children[2].tag, "details");
    assert.equal(selected.children[2].children[1].textContent, block.text);
    assert.equal(empty.children[1].textContent, "Bitte einen Block im Netz auswählen.");
    assert.equal(empty.children.length, 2);
});

test("empty graph content shows a readable message without an empty source toggle", () => {
    const container = new Element("div");
    const context = vm.createContext({document, blocks: [{...block, text: ""}],
        source: {value: "a"}, target: {value: ""}, label: value => value.title, container});
    vm.runInContext(showContent + "\nshowContent(container);", context);
    assert.equal(container.children[0].children[1].textContent, "Dieser Block hat keinen Textinhalt.");
    assert.equal(container.children[0].children.length, 2);
});

const workspace = asset("workspace.js");
const render = workspace.slice(workspace.indexOf("function render(side)"), workspace.indexOf("function clean("));
test("parts preview renders each saved part and reports missing parts as plain text", () => {
    const fields = Object.fromEntries(
        ["select", "title", "text", "identity", "relations", "parts", "preview"]
            .map(name => [name, new Element("div")]));
    const composition = {...block, id: "composition", parts: ["a", "<missing>"]};
    const blocks = [composition, block];
    const context = vm.createContext({document, blocks, state: {left: {id: "composition"}},
        find: id => blocks.find(item => item.id === id),
        label: value => value ? value.title : "Nicht gefunden",
        element: (side, name) => fields[name], button: text => new Element("button")});
    vm.runInContext(render + '\nrender("left");', context);
    assert.equal(fields.preview.children[0].innerHTML, block.text_html);
    assert.equal(fields.preview.children[1].textContent, "[Bestandteil nicht gefunden: <missing>]");
    assert.equal(fields.preview.children[1].innerHTML, undefined);
    assert.equal(fields.text.value, composition.text);
    context.state.left.id = "";
    vm.runInContext('render("left");', context);
    assert.equal(fields.preview.children.length, 0);
});
