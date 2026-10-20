/* Kiki presence: browser-native voice and lightweight SVG animation.
   Presentation only. No new task authority, model, secrets, or microphone access. */
(() => {
  "use strict";
  const init = () => {
    const portrait = document.querySelector(".portrait");
    const mouth = document.getElementById("kikiMouth");
    const saying = document.getElementById("says");
    const speakButton = document.getElementById("voiceSpeak");
    const stopButton = document.getElementById("voiceStop");
    const voiceList = document.getElementById("voiceSelect");
    const autoVoice = document.getElementById("voiceAuto");
    const statusLabel = document.getElementById("voiceStatus");
    if (!portrait || !mouth || !saying || !speakButton || !stopButton || !voiceList || !autoVoice || !statusLabel) return;

    const synth = typeof window.speechSynthesis !== "undefined" ? window.speechSynthesis : null;
    const canSpeak = !!(synth && typeof window.SpeechSynthesisUtterance === "function");
    const STORAGE_KEY = "kiki.presence.voice.v1";
    let settings = {voiceURI: "", auto: false, rate: 1};
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
      if (typeof saved.voiceURI === "string") settings.voiceURI = saved.voiceURI;
      if (typeof saved.auto === "boolean") settings.auto = saved.auto;
    } catch (_) { /* Private browsing and restricted storage are supported. */ }
    const save = () => { try { localStorage.setItem(STORAGE_KEY, JSON.stringify(settings)); } catch (_) {} };
    let currentText = saying.textContent.trim();
    let seenReply = null;
    let initialized = false;
    let voiceChoices = [];
    let mouthTimer = null;
    let talkToken = 0;
    let active = false;
    const mouthRest = "M109 177Q131 189 152 172";
    const mouthOpen = "M110 173Q130 164 152 172Q149 193 132 195Q117 191 110 173Z";
    const setMouth = open => {
      mouth.setAttribute("d", open ? mouthOpen : mouthRest);
      mouth.setAttribute("fill", open ? "#5b2647" : "none");
      mouth.setAttribute("stroke", "#813d65");
      mouth.setAttribute("stroke-width", "4");
    };
    const setState = next => {
      const valid = ["idle", "thinking", "speaking", "listening", "celebrating"];
      portrait.dataset.state = valid.includes(next) ? next : "idle";
    };
    const stopMouth = () => {
      if (mouthTimer !== null) clearInterval(mouthTimer);
      mouthTimer = null;
      setMouth(false);
    };
    const stop = () => {
      talkToken += 1;
      active = false;
      stopMouth();
      if (synth) synth.cancel();
      setState("idle");
      if (canSpeak) statusLabel.textContent = "Ready to speak";
    };
    const refreshVoices = () => {
      if (!canSpeak) return;
      voiceChoices = synth.getVoices().filter(v => /^en(?:-|$)/i.test(v.lang));
      const prior = voiceList.value || settings.voiceURI;
      voiceList.replaceChildren();
      if (!voiceChoices.length) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "System default";
        voiceList.appendChild(opt);
      } else {
        for (const v of voiceChoices) {
          const opt = document.createElement("option");
          opt.value = v.voiceURI;
          opt.textContent = v.name + " (" + v.lang + (v.localService ? ", device" : "") + ")";
          voiceList.appendChild(opt);
        }
        const match = voiceChoices.find(v => v.voiceURI === prior);
        if (match) voiceList.value = match.voiceURI;
        else {
          const preferred = voiceChoices.find(v => v.lang.toLowerCase() === "en-us") || voiceChoices[0];
          voiceList.value = preferred.voiceURI;
        }
      }
    };
    const chunks = text => {
      const sentences = text.match(/[^.!?\n]+(?:[.!?]+|\n|$)/g) || [text];
      const out = [];
      let part = "";
      for (const sentence of sentences) {
        for (let remaining = sentence.trim(); remaining.length;) {
          const room = 220 - part.length;
          if (room < 50) { out.push(part.trim()); part = ""; continue; }
          if (remaining.length <= room) { part += (part ? " " : "") + remaining; break; }
          let cut = remaining.lastIndexOf(" ", room);
          if (cut < 50) cut = room;
          part += (part ? " " : "") + remaining.slice(0, cut);
          out.push(part.trim()); part = "";
          remaining = remaining.slice(cut).trim();
        }
      }
      if (part.trim()) out.push(part.trim());
      return out;
    };
    const speak = text => {
      if (!canSpeak) { statusLabel.textContent = "Speech unavailable on this browser"; return false; }
      const content = String(text || "").trim();
      if (!content) return false;
      stop();
      const token = talkToken;
      const queue = chunks(content);
      if (!queue.length) return false;
      const beginMouth = () => {
        stopMouth();
        let open = true;
        setMouth(true);
        mouthTimer = setInterval(() => { open = !open; setMouth(open); }, 160);
      };
      const speakPart = index => {
        if (token !== talkToken) return;
        if (index >= queue.length) {
          active = false; stopMouth(); setState("idle");
          statusLabel.textContent = "Finished speaking";
          return;
        }
        const utterance = new window.SpeechSynthesisUtterance(queue[index]);
        utterance.lang = "en-US";
        utterance.rate = settings.rate;
        const voice = voiceChoices.find(v => v.voiceURI === voiceList.value);
        if (voice) { utterance.voice = voice; utterance.lang = voice.lang; }
        utterance.onstart = () => { if (token !== talkToken) return; active = true; setState("speaking"); beginMouth(); statusLabel.textContent = "Kiki is speaking"; };
        utterance.onend = () => { if (token !== talkToken) return; stopMouth(); speakPart(index + 1); };
        utterance.onerror = event => {
          if (token !== talkToken) return;
          active = false; stopMouth(); setState("idle");
          statusLabel.textContent = event.error === "not-allowed" ? "Tap Hear Kiki to allow audio" : "Speech playback failed";
        };
        synth.speak(utterance);
      };
      speakPart(0);
      return true;
    };
    const normalizeReply = conversations => {
      if (!Array.isArray(conversations)) return null;
      const latest = conversations.find(c => typeof c.reply === "string" && c.reply.trim() && c.reply !== "Queued for local Jan");
      if (!latest) return null;
      return {key: String(latest.id ?? latest.request_id ?? latest.text ?? "") + "\u0000" + latest.reply, reply: latest.reply};
    };
    const onConversations = conversations => {
      const latest = normalizeReply(conversations);
      if (!latest) { if (!initialized) initialized = true; return; }
      if (!initialized) {
        initialized = true;
        seenReply = latest.key;
        currentText = latest.reply;
        saying.textContent = currentText;
        return;
      }
      if (latest.key === seenReply) return;
      seenReply = latest.key;
      currentText = latest.reply;
      saying.textContent = currentText;
      setState("idle");
      if (settings.auto) speak(currentText);
    };
    const celebrate = () => {
      if (active) return;
      setState("celebrating");
      window.setTimeout(() => {
        if (!active && portrait.dataset.state === "celebrating") setState("idle");
      }, 1800);
    };
    voiceList.addEventListener("change", () => { settings.voiceURI = voiceList.value; save(); });
    autoVoice.checked = settings.auto;
    autoVoice.addEventListener("change", () => { settings.auto = autoVoice.checked; save(); statusLabel.textContent = settings.auto ? "New replies will be spoken when supported" : "Automatic speech off"; });
    speakButton.addEventListener("click", () => speak(currentText));
    stopButton.addEventListener("click", stop);
    if (!canSpeak) {
      speakButton.disabled = true; stopButton.disabled = true; voiceList.disabled = true; autoVoice.disabled = true;
      statusLabel.textContent = "Speech unavailable on this browser";
    } else {
      refreshVoices();
      if (typeof synth.addEventListener === "function") synth.addEventListener("voiceschanged", refreshVoices);
      statusLabel.textContent = "Ready to speak";
    }
    window.addEventListener("pagehide", stop);
    document.addEventListener("visibilitychange", () => { if (document.hidden && active) stop(); });
    window.KikiPresence = {
      setState, celebrate, stop, hear: speak, onConversations,
      setText(text) { if (typeof text === "string" && text.trim()) currentText = text.trim(); }
    };
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, {once: true});
  else init();
})();
