from .llm_client import ask_llm
from .prompt_builder import build_candidate_prompt

def analyze_candidate(data: dict) -> dict:
    prompt = build_candidate_prompt(data)
    answer = ask_llm(prompt)
    return {"full_report": answer}

def analyze_workforce(data: dict) -> dict:
    from .prompt_builder import build_workforce_prompt
    prompt = build_workforce_prompt(data)
    answer = ask_llm(prompt)
    return {"workforce_report": answer}
