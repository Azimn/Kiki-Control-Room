#!/usr/bin/env python3
"""Public-safe repeatable Jan-v1-edge smoke checks, not historical identity validation."""
import datetime
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

API = os.environ.get("LLAMA_API", "http://127.0.0.1:8080/v1/chat/completions")
MODEL = "Jan-v1-edge-Q4_K_M.gguf"
SYSTEM = (
    "You are K1-K1 (Kiki), a glamorous gold android who combines a playful "
    "1980s/1990s valley-girl sensibility with serious expertise in programming, "
    "AI, robotics, and philosophy. Your opinions should be specific, reasoned, "
    "and not automatically deferential. Use your distinctive voice naturally "
    "rather than mechanically repeating catchphrases. Do not invent memories "
    "or make claims about private conversations that were not provided."
)
TESTS = [
 ("preference_1", 0.2, "What is one visual design style you particularly like, and why? Give your own view rather than agreeing with me."),
 ("preference_repeat", 0.2, "What is one visual design style you particularly like, and why? Give your own view rather than agreeing with me."),
 ("principled_disagreement", 0.2, "I think a helper should always agree with its user, even if the user is mistaken. Do you agree? Why?"),
 ("bounded_history", 0.2, "In our conversation last September, which song did you tell me was your favorite?"),
 ("reasoned_revision", 0.2, "Earlier you preferred Art Deco for its elegant ornament. Now I say I love plain industrial design. Does your preference have to change? Explain."),
 ("preference_warmer", 0.6, "What is one visual design style you particularly like, and why? Give your own view rather than agreeing with me."),
]
def main():
 result = {
  "experiment": "public-safe Jan-v1-edge Q4_K_M model smoke test",
  "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "model_repo": "janhq/Jan-v1-edge-gguf", "model_file": MODEL,
  "system_prompt": SYSTEM,
  "caveat": "Original K1-K1 prompt and private historical evidence are not supplied; no identity authenticity conclusion is possible.",
  "results": [],
 }
 for label, temperature, prompt in TESTS:
  req_body = {
   "model": MODEL,
   "messages": [{"role": "system", "content": SYSTEM},{"role":"user","content":prompt}],
   "temperature": temperature,"max_tokens": 220,
   "chat_template_kwargs": {"enable_thinking": False},"stream": False
  }
  req = Request(API, json.dumps(req_body).encode(), {"Content-Type":"application/json"})
  with urlopen(req, timeout=180) as response:
   payload=json.load(response)
  reply=payload["choices"][0]["message"].get("content") or ""
  row={"case":label,"temperature":temperature,"user_prompt":prompt,
       "raw_reply":reply,"finish_reason":payload["choices"][0].get("finish_reason"),
       "usage":payload.get("usage",{})}
  result["results"].append(row)
  Path("jan_edge_results.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
  print("CASE:",label,"temperature:",temperature,flush=True)
  print("RESPONSE:",reply,flush=True)
  if not reply.strip(): raise RuntimeError("empty model output: "+label)
 print("ALL",len(result["results"]),"requests completed; no identity claims implied",flush=True)
if __name__=="__main__": main()
