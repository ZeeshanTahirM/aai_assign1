\
import os

def llm_complete(prompt: str, model: str = None, temperature: float = 0.2) -> str:
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "groq":
        try:
            from groq import Groq
            client = Groq(api_key=os.getenv("GROQ_API_KEY"))
            resp = client.chat.completions.create(
                model=model or "llama-3.3-70b-versatile",
                messages=[{"role":"system","content":"You are a rigorous crisis planner."},
                          {"role":"user","content":prompt}],
                temperature=temperature,
            )
            return resp.choices[0].message.content
        except Exception as e:
            return f"FinalAnswer: ERROR calling Groq: {e}"
    elif provider == "gemini":
        try:
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            mdl = genai.GenerativeModel(model or "gemini-1.5-flash")
            resp = mdl.generate_content(prompt)
            return resp.text
        except Exception as e:
            return f"FinalAnswer: ERROR calling Gemini: {e}"
    else:
        return "FinalAnswer: {\"commands\": \"USE_FALLBACK_HEURISTIC\"}"
