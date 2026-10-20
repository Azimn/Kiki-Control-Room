"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.resolve(__dirname, "..");
const js = fs.readFileSync(path.join(root, "web/companion-presence.js"), "utf8");
const html = fs.readFileSync(path.join(root, "web/index.html"), "utf8");
const css = fs.readFileSync(path.join(root, "web/companion-presence.css"), "utf8");
function harness(withVoice = true) {
  const elements = new Map();
  const make = () => ({
    textContent: "", value: "", checked: false, disabled: false,
    dataset: {}, attributes: {}, listeners: {}, children: [],
    setAttribute(k, v) {this.attributes[k] = v;},
    addEventListener(k, f) {this.listeners[k] = f;},
    appendChild(c) {this.children.push(c);},
    replaceChildren() {this.children = [];},
    emit(k) {this.listeners[k]?.();}
  });
  for (const id of ["kikiMouth", "says", "voiceSpeak", "voiceStop", "voiceSelect", "voiceAuto", "voiceStatus"]) elements.set(id, make());
  elements.get("says").textContent = "Hello.";
  const portrait = make();
  const utterances = [];
  const synth = {
    getVoices() {return [{voiceURI:"en-test",name:"Test",lang:"en-US",localService:true}];},
    cancel() {},
    speak(utterance) {utterances.push(utterance.text); utterance.onstart(); utterance.onend();},
    addEventListener() {}
  };
  const win = {addEventListener() {}, setTimeout() {}, ...(withVoice ? {
    speechSynthesis:synth,
    SpeechSynthesisUtterance:class {constructor(text) {this.text = text;}}
  } : {})};
  const document = {
    readyState: "complete", hidden: false,
    getElementById(id) {return elements.get(id);},
    querySelector(s) {return s === ".portrait" ? portrait : null;},
    createElement() {return make();},
    addEventListener() {}
  };
  const store = new Map();
  const localStorage = {getItem(k) {return store.get(k) ?? null;},setItem(k,v) {store.set(k,v);}};
  let nextTimer = 0;
  vm.runInNewContext(js, {window:win,document,localStorage,
    setInterval() {return ++nextTimer;},clearInterval() {}}, {timeout:1000});
  return {win,document,portrait,elements,utterances,store};
}
test("dashboard and local server expose the new static assets", () => {
  const source = fs.readFileSync(path.join(root, "runtime/local/kiki_local.py"), "utf8");
  for (const f of ["companion-presence.js","companion-presence.css"]) {
    assert.ok(html.includes("/" + f));
    assert.ok(source.includes('"/' + f + '"'));
  }
  for (const id of ["kikiEyeLeft","kikiEyeRight","kikiMouth","voiceSpeak","voiceSelect","voiceAuto"]) {
    assert.ok(html.includes('id="' + id + '"'));
  }
});
test("voice works without a server or microphone and resets the portrait", () => {
  const h = harness();
  assert.equal(h.win.KikiPresence.hear("Hi there."), true);
  assert.deepEqual(h.utterances, ["Hi there."]);
  assert.equal(h.portrait.dataset.state, "idle");
  assert.equal(h.elements.get("kikiMouth").attributes.fill, "none");
  assert.equal(h.elements.get("voiceStatus").textContent, "Finished speaking");
});
test("historical replies are never automatically replayed and polling deduplicates", () => {
  const h = harness();
  const api = h.win.KikiPresence;
  const first = [{id:1,text:"hello",reply:"Original reply"}];
  api.onConversations(first);
  assert.equal(h.utterances.length, 0);
  const auto = h.elements.get("voiceAuto");
  auto.checked = true;
  auto.emit("change");
  api.onConversations(first);
  assert.equal(h.utterances.length, 0);
  api.onConversations([{id:2,text:"question",reply:"New reply"},...first]);
  assert.deepEqual(h.utterances, ["New reply"]);
  api.onConversations([{id:2,text:"question",reply:"New reply"},...first]);
  assert.equal(h.utterances.length, 1);
  assert.equal(h.elements.get("says").textContent, "New reply");
});
test("unsupported browsers degrade to text and disabled voice controls", () => {
  const h = harness(false);
  assert.equal(h.win.KikiPresence.hear("hello"),false);
  assert.equal(h.elements.get("voiceSpeak").disabled,true);
  assert.equal(h.elements.get("voiceAuto").disabled,true);
  assert.equal(h.elements.get("voiceStatus").textContent,"Speech unavailable on this browser");
});
test("CSS honors motion preferences and text is not injected as HTML", () => {
  assert.match(css,/prefers-reduced-motion:reduce/);
  assert.match(js,/saying\.textContent = currentText/);
  assert.doesNotMatch(js,/innerHTML/);
});
