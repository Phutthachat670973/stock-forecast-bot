import json
import os

def _safe_json_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(s[start:end+1])
        raise

def summarize_news_with_ai(ticker: str, company: str, headlines: list[dict], ai_cfg: dict) -> dict | None:
    provider = (ai_cfg.get("provider") or "gemini").lower()
    if provider != "gemini":
        raise RuntimeError("Only gemini provider is implemented.")

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    from google import genai

    model_name = ai_cfg.get("model", "gemini-2.5-flash")
    lang = ai_cfg.get("language", "th")
    top_pick = int(ai_cfg.get("top_pick", 5))

    client = genai.Client(api_key=api_key)

    lines = []
    for i, h in enumerate(headlines, start=1):
        title = h.get("title", "")
        src = h.get("source", "")
        pub = h.get("published", "")
        lines.append(f"[{i}] {title} (source: {src}; published: {pub})")

    prompt = f"""
You are a finance news assistant. You MUST use only the provided headlines list.
Do NOT invent facts or details beyond the headline text.

Task:
1) Select up to {top_pick} headlines that are most relevant to {ticker} ({company}).
2) For each selected headline, assign stance:
   - bullish (may support price up)
   - bearish (may pressure price down)
   - neutral
3) Provide confidence 0-100.
4) Write Thai if language=th, otherwise English.
5) Reference each item by its headline index.

Output STRICT JSON only:
{{
  "picks": [
    {{"idx": 1, "stance": "bullish|bearish|neutral", "confidence": 0-100, "summary": "...", "why": "..."}}
  ],
  "overall": {{"stance": "bullish|bearish|neutral", "confidence": 0-100, "note": "..."}}
}}

language = "{lang}"

Headlines:
{chr(10).join(lines)}
""".strip()

    resp = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    text = (resp.text or "").strip()
    if not text:
        return None

    data = _safe_json_load(text)
    if "picks" not in data or "overall" not in data:
        return None

    n = len(headlines)
    valid = []
    for p in data.get("picks", []):
        try:
            idx = int(p.get("idx"))
            if 1 <= idx <= n:
                valid.append({
                    "idx": idx,
                    "stance": str(p.get("stance", "neutral")).lower(),
                    "confidence": int(p.get("confidence", 50)),
                    "summary": str(p.get("summary", "")).strip(),
                    "why": str(p.get("why", "")).strip()
                })
        except Exception:
            continue

    data["picks"] = valid[:top_pick]
    return data
