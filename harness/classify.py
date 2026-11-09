"""Stage 5 (classify): decide whether each event is for young people, and
assign categories from harness/context/categories.md.

Two classifiers, same output ({"categories": [...], "youth": "yes|no|unsure"}):
- LLMClassifier: Claude reads the category list and the event. Used when
  ANTHROPIC_API_KEY is set. Bounded by a call and token budget.
- BaselineClassifier: deterministic rules (source categories + keywords). Used
  offline, as the fallback when the LLM fails or the budget is spent, and as a
  comparison point in evaluation.
"""
from __future__ import annotations

import json
import re

from .config import CONTEXT_DIR

CATEGORY_LINE = re.compile(r"^- `([a-z_]+)`:", re.MULTILINE)
YOUTH_VALUES = {"yes", "no", "unsure"}


def load_categories() -> tuple[set[str], str]:
    text = (CONTEXT_DIR / "categories.md").read_text(encoding="utf-8")
    ids = set(CATEGORY_LINE.findall(text))
    if not ids:
        raise RuntimeError("No categories found in harness/context/categories.md")
    return ids, text


# ---------------------------------------------------------------- baseline

# Kulturnett-style source categories (as shown in the Hva skjer filter).
SOURCE_MAP = {
    "konsert": "music", "musikk": "music",
    "idrett": "sports", "sport": "sports",
    "dans": "arts_culture", "teater": "arts_culture", "utstilling": "arts_culture", "kunst": "arts_culture",
    "film": "film", "kino": "film",
    "tur": "outdoors", "friluftsliv": "outdoors",
    "mat": "food",
    "kurs": "learning", "foredrag": "learning",
}
KEYWORDS = {
    "gaming": ["gaming", "e-sport", "esport", " lan-", " lan ", "brettspill", "spillkveld", "konsoll", "rollespill"],
    "social": ["quiz", "drop-in", "ungdomsklubb", "treff", "møteplass", "kom alene"],
    "learning": ["workshop", "kurs", "foredrag", "leksehjelp", "språkkafé"],
    "outdoors": ["fottur", "friluft", "fisketur", "skitur"],
    "food": ["pizza", "middag", "matlaging", "baking", "spiser sammen"],
    "film": ["filmkveld", "kino"],
    "music": ["konsert", "open mic", "åpen scene"],
    "arts_culture": ["teater", "utstilling", "dansekurs", "tegne", "maling", "stand-up"],
    "sports": ["klatring", "vannpolo", "fotball", "håndball", "ishockey", "basket", "svømm"],
}
YOUTH_SOURCE = {"ungdom", "barn og ungdom"}
YOUTH_WORDS = ["ungdom", "for unge", "unge ", "13–", "13-", "tenåring", "ungdomsskole", "videregående", "student"]
NOT_YOUTH_WORDS = ["senior", "pensjon", "babysang", "barn 0", "småbarn", "barnehage"]


class BaselineClassifier:
    name = "baseline"

    def __init__(self, allowed: set[str]):
        self.allowed = allowed

    def youth(self, ev: dict) -> str:
        text = f" {ev.get('title', '')} {ev.get('description', '')} ".casefold()
        if any(w in text for w in NOT_YOUTH_WORDS):
            return "no"
        if {c.casefold() for c in ev.get("source_categories", [])} & YOUTH_SOURCE:
            return "yes"
        if any(w in text for w in YOUTH_WORDS):
            return "yes"
        return "unsure"

    def categories(self, ev: dict) -> list[str]:
        cats: list[str] = []

        def add(c: str) -> None:
            if c in self.allowed and c not in cats:
                cats.append(c)

        text = f" {ev.get('title', '')} {ev.get('description', '')} ".casefold()
        for cat, words in KEYWORDS.items():  # what people do comes first
            if any(w in text for w in words):
                add(cat)
        for sc in ev.get("source_categories", []):
            if sc.casefold() in SOURCE_MAP:
                add(SOURCE_MAP[sc.casefold()])
        return cats[:3]

    def classify(self, ev: dict) -> dict:
        return {"categories": self.categories(ev), "youth": self.youth(ev)}


# ---------------------------------------------------------------- LLM

def parse_llm_output(text: str, allowed: set[str]) -> dict:
    """Parse the model's JSON reply. Raises ValueError if it is not valid."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")
    cats = data.get("categories")
    if not isinstance(cats, list) or not all(isinstance(c, str) for c in cats):
        raise ValueError("reply has no 'categories' list of strings")
    unknown = [c for c in cats if c not in allowed]
    if unknown:
        raise ValueError(f"unknown categories: {unknown}")
    if len(cats) > 3:
        raise ValueError("more than 3 categories")
    youth = data.get("youth")
    if youth not in YOUTH_VALUES:
        raise ValueError(f"'youth' must be one of {sorted(YOUTH_VALUES)}")
    return {"categories": list(dict.fromkeys(cats)), "youth": youth}


def combine_answers(answers: list[dict]) -> dict:
    """Combine repeated classifications of one event (see LLMClassifier.classify).

    Audience disagreement -> youth "unsure" (human review). Category-only
    disagreement -> keep the first answer's categories: sending those to review
    added reviewer work without any safety gain (regression run, 9 Nov).
    """
    first = answers[0]
    if len(answers) == 1:
        return first
    youths = {a["youth"] for a in answers}
    cats_agree = all(set(a["categories"]) == set(first["categories"]) for a in answers)
    if len(youths) > 1:
        union = list(dict.fromkeys(c for a in answers for c in a["categories"]))[:3]
        return {"categories": union, "youth": "unsure", "disagreement": "youth"}
    if not cats_agree:
        return {"categories": first["categories"], "youth": first["youth"], "disagreement": "categories"}
    return first


class BudgetExceeded(RuntimeError):
    pass


class LLMClassifier:
    name = "llm"

    def __init__(self, allowed: set[str], categories_text: str, cfg: dict, api_key: str):
        import anthropic  # imported here so offline runs don't need the package

        self.client = anthropic.Anthropic(api_key=api_key)
        self.allowed = allowed
        self.cfg = cfg["classify"]
        prompt = (CONTEXT_DIR / "classify_prompt.md").read_text(encoding="utf-8")
        self.system = f"{prompt}\n\n<category_list>\n{categories_text}\n</category_list>"
        self.calls = 0
        self.tokens = 0

    def _check_budget(self) -> None:
        if self.calls >= self.cfg["max_llm_calls"]:
            raise BudgetExceeded("max_llm_calls reached")
        if self.tokens >= self.cfg["max_total_tokens"]:
            raise BudgetExceeded("max_total_tokens reached")

    def classify(self, ev: dict) -> dict:
        """Ask `self_consistency` times (default 2). Stress-test repair for model
        variance: if the answers disagree about the audience, the event goes to
        human review; if they only disagree about categories, the first answer's
        categories are kept."""
        n = max(1, int(self.cfg.get("self_consistency", 2)))
        answers = [self._classify_once(ev) for _ in range(n)]
        return combine_answers(answers)

    def _classify_once(self, ev: dict) -> dict:
        payload = {k: ev.get(k) for k in ("title", "description", "venue_name", "source_categories", "price")}
        user = f"<event>\n{json.dumps(payload, ensure_ascii=False)}\n</event>"
        last_err: Exception | None = None
        last_text = ""
        for _ in range(2):  # one retry on malformed output
            self._check_budget()
            resp = self.client.messages.create(
                model=self.cfg["model"],
                max_tokens=self.cfg["max_output_tokens"],
                system=self.system,
                messages=[{"role": "user", "content": user}],
                # Sent via extra_body so it works with any version of the anthropic package.
                extra_body={"output_config": {"effort": self.cfg.get("effort", "medium")}},
            )
            self.calls += 1
            self.tokens += resp.usage.input_tokens + resp.usage.output_tokens
            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            last_text = text
            if resp.stop_reason == "max_tokens":
                # Thinking used up the output limit before any answer. Retrying at the
                # same limit rarely helps, so fail now and let the baseline decide.
                raise ValueError(f"output limit ({self.cfg['max_output_tokens']} tokens) reached before an "
                                 f"answer; raise classify.max_output_tokens | reply starts: {text[:300]!r}")
            try:
                return parse_llm_output(text, self.allowed)
            except (ValueError, json.JSONDecodeError) as e:
                last_err = e
        # Include the start of the model's actual reply, so we can see what went wrong.
        raise ValueError(f"LLM output invalid twice: {last_err} | stop_reason={resp.stop_reason} "
                         f"| reply starts: {last_text[:300]!r}")


def classify_all(events: list[dict], primary, fallback: BaselineClassifier) -> dict:
    """Classify in place. Returns stats. Falls back to the baseline per event on
    errors, and for all remaining events once the budget is spent."""
    stats = {"classifier": primary.name, "llm_errors": 0, "fallback_used": 0, "budget_exhausted": False}
    use_fallback_only = primary is fallback
    for ev in events:
        if not use_fallback_only:
            try:
                result = dict(primary.classify(ev))
                disagreement = result.pop("disagreement", None)
                ev.update(result)
                if disagreement:
                    stats["llm_disagreements"] = stats.get("llm_disagreements", 0) + 1
                    ev["flags"].append(f"llm_disagreement:{disagreement}")
                continue
            except BudgetExceeded:
                stats["budget_exhausted"] = True
                use_fallback_only = True
            except Exception as e:  # network error, invalid output, ...
                stats["llm_errors"] += 1
                ev["flags"].append(f"llm_error:{type(e).__name__}")
                # Keep a few examples in the run report (report.json -> classification).
                samples = stats.setdefault("llm_error_samples", [])
                if len(samples) < 10:
                    samples.append({"id": ev["id"], "title": ev.get("title", ""), "error": str(e)[:500]})
        ev.update(fallback.classify(ev))
        if primary is not fallback:
            stats["fallback_used"] += 1
            ev["flags"].append("classified_by_baseline")
    if hasattr(primary, "calls"):
        stats["llm_calls"] = primary.calls
        stats["llm_tokens"] = primary.tokens
    return stats
