"""Earnings-call deception scoring — Larcker & Zakolyukina (2012) (MASTER_PLAN V7).

A deterministic lexical scorer (no LLM anywhere): per-narrative standardized
rates of the paper's word categories, combined with the signs the paper found
for CEO vs CFO narratives. The self-constructed category phrase lists
(general-knowledge references, shareholder value, value creation) follow the
paper's panel B; the LIWC-style categories use compact open word lists in the
same spirit (LIWC itself is proprietary).

Honesty box, stated everywhere this surfaces: the paper's result is **6–16%
above-chance out-of-sample CLASSIFICATION accuracy** against restatement
labels — not a return edge (its CFO-model portfolio alpha was *negative* for
high-deception firms; the CEO model produced no significant alpha). Real
transcripts are a later data source; until then the module ships a synthetic
labeled generator so the scorer's skill is demonstrated leak-free and pinned
against noise, exactly like every other edge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from ..ml.cv import PurgedWalkForwardCV

# --------------------------------------------------------------- word lists
# Panel-B self-constructed categories (phrases, from the paper):
GENERAL_KNOWLEDGE = (
    "you know", "you guys know", "you folks know", "you well know",
    "everybody knows", "everybody would agree", "everyone would agree",
    "others know", "others would agree", "they know", "they would agree",
    "investors know", "investors well know", "shareholders know",
    "as you know", "as we all know",
)
SHAREHOLDER_VALUE = (
    "shareholder value", "shareholder welfare", "value for our shareholders",
    "stockholder value", "value for our stockholders", "investor welfare",
    "value for investors",
)
VALUE_CREATION = (
    "value creation", "create value", "creates value", "creating value",
    "unlock value", "unlocking value", "improve value", "improving value",
    "increase value", "deliver value", "delivering value", "enhance value",
    "enhancing value", "expand value",
)
# LIWC-spirit compact lists (open substitutes):
EXTREME_POSITIVE = (
    "fantastic", "incredible", "phenomenal", "outstanding", "spectacular",
    "extraordinary", "tremendous", "amazing", "superb", "unbelievable",
)
NONEXTREME_POSITIVE = (
    "good", "nice", "solid", "fine", "pleased", "happy", "glad", "positive",
    "healthy", "steady", "encouraging", "comfortable",
)
ANXIETY = (
    "worried", "worry", "concern", "concerned", "afraid", "nervous",
    "anxious", "fear", "risk averse", "uneasy",
)
NEGATION = ("no", "not", "never", "none", "cannot", "can't", "don't", "won't", "didn't")
ASSENT = ("yes", "yeah", "okay", "ok", "agree", "absolutely", "correct", "right")
TENTATIVE = (
    "maybe", "perhaps", "guess", "possibly", "probably", "somewhat", "sort of",
    "kind of", "we believe", "we estimate", "we think", "roughly", "approximately",
)
CERTAINTY = (
    "always", "definitely", "certainly", "clearly", "absolutely certain",
    "without question", "we will", "committed", "guarantee",
)
HESITATION = ("um", "uh", "er", "hmm", "well,")
SELF_REFERENCE = ("i", "me", "my", "mine", "myself")
GROUP_REFERENCE = ("we", "us", "our", "ours", "ourselves")
IMPERSONAL = ("everybody", "anybody", "nobody", "everyone", "anyone", "somebody", "something")

#: category -> (phrases, sign in the deception composite, applies_to)
#: signs follow the paper: + pushes toward deceptive, - toward truthful.
#: "both" categories were significant for CEOs and CFOs; speaker-specific ones
#: enter only that executive's composite (extreme positives were a CEO effect,
#: negation/extreme-negative a CFO effect, anxiety a CEO effect).
CATEGORIES: dict[str, tuple[tuple[str, ...], float, str]] = {
    "general_knowledge": (GENERAL_KNOWLEDGE, +1.0, "both"),
    "shareholder_value": (SHAREHOLDER_VALUE, -1.0, "both"),
    "value_creation": (VALUE_CREATION, -1.0, "both"),
    "nonextreme_positive": (NONEXTREME_POSITIVE, -1.0, "both"),
    "extreme_positive": (EXTREME_POSITIVE, +1.0, "ceo"),
    "anxiety": (ANXIETY, -1.0, "ceo"),
    "negation": (NEGATION, +1.0, "cfo"),
    "assent": (ASSENT, -1.0, "both"),
    "tentative": (TENTATIVE, +1.0, "both"),
    "certainty": (CERTAINTY, -1.0, "both"),
    "hesitation": (HESITATION, -1.0, "both"),
    "self_reference": (SELF_REFERENCE, -1.0, "both"),
    "group_reference": (GROUP_REFERENCE, +1.0, "both"),
    "impersonal_pronoun": (IMPERSONAL, +1.0, "both"),
}

_WORD = re.compile(r"[a-z']+")


def category_rates(text: str) -> dict[str, float]:
    """Per-1,000-word standardized count of every category (the paper divides
    by instance length; we standardize per mille for determinism)."""
    lowered = text.lower()
    words = _WORD.findall(lowered)
    n = len(words)
    if n == 0:
        return {name: 0.0 for name in CATEGORIES}
    padded = " " + " ".join(words) + " "
    rates: dict[str, float] = {}
    for name, (phrases, _sign, _who) in CATEGORIES.items():
        count = 0
        for phrase in phrases:
            count += padded.count(" " + phrase.strip() + " ")
        rates[name] = 1000.0 * count / n
    return rates


def deception_score(text: str, speaker: str = "ceo") -> float:
    """Signed composite of category rates for one narrative. Higher = more of
    the deception-associated language. A raw lexical score — NOT a probability
    and NOT an accusation; calibration happens per-corpus, out-of-sample."""
    if speaker not in ("ceo", "cfo"):
        raise ValueError("speaker must be 'ceo' or 'cfo'")
    rates = category_rates(text)
    score = 0.0
    for name, (_phrases, sign, who) in CATEGORIES.items():
        if who in ("both", speaker):
            score += sign * rates[name]
    return score


# ------------------------------------------------- tiny 1-D Platt calibration


@dataclass
class _Platt:
    a: float = 0.0
    b: float = 0.0

    def fit(self, scores: np.ndarray, labels: np.ndarray, iters: int = 200, lr: float = 0.1):
        s = (scores - scores.mean()) / (scores.std() + 1e-12)
        a, b = 0.0, 0.0
        for _ in range(iters):
            p = 1.0 / (1.0 + np.exp(-(a * s + b)))
            grad_a = float(np.mean((p - labels) * s))
            grad_b = float(np.mean(p - labels))
            a -= lr * grad_a
            b -= lr * grad_b
        self.a, self.b = a, b
        self._mu, self._sd = float(scores.mean()), float(scores.std() + 1e-12)
        return self

    def predict(self, scores: np.ndarray) -> np.ndarray:
        s = (scores - self._mu) / self._sd
        return 1.0 / (1.0 + np.exp(-(self.a * s + self.b)))


def auc(labels: np.ndarray, scores: np.ndarray) -> float:
    """Rank AUC (Mann-Whitney). 0.5 = a random classifier."""
    labels = np.asarray(labels, dtype=float)
    scores = np.asarray(scores, dtype=float)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return 0.5
    ranks = np.argsort(np.argsort(np.concatenate([pos, neg]))) + 1
    r_pos = ranks[: len(pos)].sum()
    u = r_pos - len(pos) * (len(pos) + 1) / 2.0
    return float(u / (len(pos) * len(neg)))


# -------------------------------------------------- synthetic labeled corpus

_FILLER = (
    "revenue for the quarter came in at four hundred million with gross margin "
    "near forty percent and operating expenses in line with the plan for the "
    "segment while cash flow from operations supported the capital program and "
    "inventory levels normalized across the distribution channel during the period"
).split()


def synthetic_narratives(
    n: int = 200,
    seed: int = 0,
    strength: float = 1.0,
    speaker: str = "ceo",
) -> tuple[list[str], np.ndarray]:
    """Labeled synthetic narratives: deceptive ones over-sample the paper's
    positive-sign markers, truthful ones the negative-sign markers.
    ``strength=0`` breaks the link entirely — the honest null."""
    rng = np.random.default_rng(seed)
    labels = (rng.uniform(size=n) < 0.5).astype(float)
    texts: list[str] = []
    pos_phrases = [p for ph, s, w in CATEGORIES.values() if s > 0 and w in ("both", speaker) for p in ph]
    neg_phrases = [p for ph, s, w in CATEGORIES.values() if s < 0 and w in ("both", speaker) for p in ph]
    for y in labels:
        body = list(rng.choice(_FILLER, size=120))
        lean = strength * (1.0 if y == 1 else -1.0)
        n_pos = rng.poisson(max(0.2, 3.0 + 2.5 * lean))
        n_neg = rng.poisson(max(0.2, 3.0 - 2.5 * lean))
        inserts = [str(rng.choice(pos_phrases)) for _ in range(n_pos)]
        inserts += [str(rng.choice(neg_phrases)) for _ in range(n_neg)]
        for phrase in inserts:
            k = int(rng.integers(0, len(body)))
            body.insert(k, phrase)
        texts.append(" ".join(body))
    return texts, labels


def deception_skill_report(seed: int = 0, strength: float = 1.0, speaker: str = "ceo") -> dict:
    """OOS AUC + Brier-skill-vs-base of the scorer under the purged/blocked CV.

    Each fold fits only the 1-D Platt calibration on its train block; the
    lexical score itself is deterministic. ``strength=0`` must pin ~0 skill.
    """
    texts, labels = synthetic_narratives(n=240, seed=seed, strength=strength, speaker=speaker)
    scores = np.array([deception_score(t, speaker=speaker) for t in texts])
    times = np.arange(len(texts))
    cv = PurgedWalkForwardCV(n_splits=4, horizon=1)
    ys, ps = [], []
    for train_idx, test_idx in cv.split(times):
        platt = _Platt().fit(scores[train_idx], labels[train_idx])
        ys.append(labels[test_idx])
        ps.append(platt.predict(scores[test_idx]))
    y = np.concatenate(ys)
    p = np.concatenate(ps)
    base = float(y.mean())
    brier_model = float(np.mean((p - y) ** 2))
    brier_base = float(np.mean((base - y) ** 2))
    return {
        "oos_auc": auc(y, np.concatenate([scores[t] for _, t in cv.split(times)])),
        "brier_skill_vs_base": 0.0 if brier_base == 0 else 1.0 - brier_model / brier_base,
        "n": int(len(y)),
        "caveat": (
            "Paper-grounded expectation: 6-16% above-chance CLASSIFICATION accuracy "
            "(restatement labels), not a return edge. Synthetic demonstration until "
            "real transcripts are wired."
        ),
    }
