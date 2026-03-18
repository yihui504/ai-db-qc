"""LLM-Driven Semantic Test Data Generator for Vector Database Testing.

This module addresses the core challenge of "semantic-void random vectors":
traditional random vectors cannot probe semantic boundary conditions.

Four data generation strategies:
  1. PositivePairs    - semantically similar text pairs (should be nearby in vector space)
  2. NegativePairs    - semantically dissimilar text pairs (should be far apart)
  3. HardNegatives    - surface-similar but semantically different pairs (edge cases)
  4. BoundaryVectors  - text near semantic decision boundaries

Design principle:
  LLM generates semantically rich text → Embedding model converts to vectors →
  Vectors carry semantic ground truth labels → Used for Oracle evaluation

Usage:
    generator = SemanticDataGenerator(llm_client=..., embedding_fn=...)
    dataset = generator.generate(domain="finance", n_positives=50, n_hard_negatives=50)
    dataset.save("datasets/finance_semantic_test.json")
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────

@dataclass
class TextPair:
    """A labeled pair of texts for semantic testing."""
    pair_id: str
    text_a: str
    text_b: str
    pair_type: str          # "positive", "negative", "hard_negative", "boundary"
    domain: str
    expected_relation: str  # "close", "far", "ambiguous"
    semantic_notes: str = ""
    vector_a: Optional[List[float]] = None
    vector_b: Optional[List[float]] = None


@dataclass
class SemanticTestDataset:
    """A complete semantic test dataset with metadata."""
    dataset_id: str
    domain: str
    created_at: str
    generator_version: str = "1.0"
    pairs: List[TextPair] = field(default_factory=list)
    metamorphic_relations: List[Dict[str, Any]] = field(default_factory=list)

    def save(self, path: str) -> None:
        """Save dataset to JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Dataset saved: {path} ({len(self.pairs)} pairs)")

    @classmethod
    def load(cls, path: str) -> "SemanticTestDataset":
        """Load dataset from JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ds = cls(
            dataset_id=data["dataset_id"],
            domain=data["domain"],
            created_at=data["created_at"],
            generator_version=data.get("generator_version", "1.0"),
        )
        for p in data.get("pairs", []):
            ds.pairs.append(TextPair(**p))
        ds.metamorphic_relations = data.get("metamorphic_relations", [])
        return ds

    def _to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "domain": self.domain,
            "created_at": self.created_at,
            "generator_version": self.generator_version,
            "pairs": [asdict(p) for p in self.pairs],
            "metamorphic_relations": self.metamorphic_relations,
            "stats": self.stats(),
        }

    def stats(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for p in self.pairs:
            counts[p.pair_type] = counts.get(p.pair_type, 0) + 1
        return counts

    def get_pairs_by_type(self, pair_type: str) -> List[TextPair]:
        return [p for p in self.pairs if p.pair_type == pair_type]


# ─────────────────────────────────────────────────────────────
# Prompt templates
# ─────────────────────────────────────────────────────────────

PROMPTS = {
    "positive_pairs": """Generate {n} pairs of semantically SIMILAR texts in the {domain} domain.

Requirements:
- Each pair should be about the same concept/topic but worded differently
- Texts should be 1-3 sentences each
- The pairs should be genuinely semantically equivalent (paraphrase or close synonyms)
- Domain: {domain}

Output ONLY a JSON array (no markdown):
[
  {{"text_a": "...", "text_b": "...", "notes": "brief explanation of similarity"}},
  ...
]""",

    "negative_pairs": """Generate {n} pairs of semantically DISSIMILAR texts in the {domain} domain.

Requirements:
- Each pair should be about clearly different concepts
- Texts should be 1-3 sentences each
- The pairs should be semantically unrelated despite being from the same domain
- Domain: {domain}

Output ONLY a JSON array (no markdown):
[
  {{"text_a": "...", "text_b": "...", "notes": "brief explanation of dissimilarity"}},
  ...
]""",

    "hard_negatives": """Generate {n} HARD NEGATIVE pairs in the {domain} domain.

Hard negatives are pairs that APPEAR similar (same topic area, similar keywords) but are
semantically DIFFERENT in meaning. These are the most challenging test cases.

Examples of hard negatives:
- "The patient is stable" vs "The patient's condition is deteriorating" (both medical, but opposite meaning)
- "Interest rates rose sharply" vs "Interest rates fell sharply" (financial, opposite direction)
- "The drug is effective for treatment" vs "The drug is contraindicated for treatment" (medical, opposite recommendation)

Requirements:
- Surface similarity: similar keywords, same domain, similar sentence structure
- Semantic difference: opposite meaning, different entity, negated statement, subtle distinction
- Texts should be 1-3 sentences each
- Domain: {domain}

Output ONLY a JSON array (no markdown):
[
  {{"text_a": "...", "text_b": "...", "notes": "explain why they look similar but are semantically different"}},
  ...
]""",

    "boundary_cases": """Generate {n} BOUNDARY/AMBIGUOUS text pairs in the {domain} domain.

Boundary cases are pairs where semantic similarity is genuinely ambiguous - a reasonable
embedding model might classify them as similar OR different depending on context.

Requirements:
- Genuinely ambiguous: reasonable people might disagree on similarity
- Relevant to the domain
- Texts should be 1-3 sentences each
- Domain: {domain}

Output ONLY a JSON array (no markdown):
[
  {{"text_a": "...", "text_b": "...", "notes": "explain the ambiguity"}},
  ...
]""",

    "metamorphic_relations": """You are an expert in metamorphic testing for vector databases.

Generate {n} metamorphic relations for testing vector search correctness in the {domain} domain.

A metamorphic relation defines: "If input changes in way X, output should change in way Y"

Examples of metamorphic relations for vector search:
1. "If two queries are semantically equivalent, their top-K results should overlap by >= 80%"
2. "If a query Q retrieves document D, then a paraphrase of Q should also retrieve D with high probability"
3. "If document A is more similar to query Q than document B, then rank(A) < rank(B)"
4. "The distance between Q and D_retrieved must be <= distance between Q and D_not_retrieved (for any D_not_retrieved)"

Generate specific, testable metamorphic relations for {domain}:

Output ONLY a JSON array (no markdown):
[
  {{
    "relation_id": "MR-{domain_short}-01",
    "name": "short descriptive name",
    "description": "formal statement of the relation",
    "input_transformation": "what transformation is applied to the input",
    "expected_output_property": "what property should hold on the output",
    "domain": "{domain}",
    "testable": true/false,
    "test_strategy": "how to operationalize this as a test"
  }},
  ...
]"""
}


# ─────────────────────────────────────────────────────────────
# LLM call abstraction (supports multiple providers)
# ─────────────────────────────────────────────────────────────

def _call_llm_openai_compatible(
    prompt: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Call an OpenAI-compatible LLM API. Returns the response text."""
    try:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"LLM API call failed: {e}") from e


def _parse_json_from_response(text: str) -> Any:
    """Extract and parse JSON from LLM response (handles markdown code blocks)."""
    # Remove markdown code blocks if present
    text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON array or object within the text
        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"Cannot parse JSON from response: {text[:200]}...")


# ─────────────────────────────────────────────────────────────
# Fallback: rule-based generation (no LLM needed)
# ─────────────────────────────────────────────────────────────

DOMAIN_TEMPLATES: Dict[str, Dict[str, List[Tuple[str, str, str]]]] = {
    "finance": {
        "positive": [
            ("The company reported strong quarterly earnings growth.", "The firm achieved significant profit increases this quarter.", "paraphrase"),
            ("Interest rates were raised by the central bank.", "The central bank increased its benchmark interest rate.", "paraphrase"),
            ("The stock price fell sharply after the earnings report.", "Share prices dropped significantly following the earnings announcement.", "paraphrase"),
            ("Credit risk assessment is critical for loan approval.", "Evaluating creditworthiness is essential in the lending process.", "paraphrase"),
            ("Market volatility increased due to geopolitical uncertainty.", "Geopolitical tensions led to higher market fluctuations.", "paraphrase"),
        ],
        "negative": [
            ("The company reported strong quarterly earnings.", "The weather forecast calls for rain this weekend.", "unrelated"),
            ("Interest rates are rising globally.", "Advances in quantum computing are accelerating.", "unrelated"),
            ("Inflation has reached a 40-year high.", "The team won the championship game.", "unrelated"),
        ],
        "hard_negative": [
            ("The bond yield rose to 5%.", "The bond yield fell to 5%.", "rise vs fall"),
            ("The merger was approved by regulators.", "The merger was blocked by regulators.", "approved vs blocked"),
            ("Revenue increased by 20% year-over-year.", "Revenue decreased by 20% year-over-year.", "increase vs decrease"),
            ("The company is profitable and expanding.", "The company is losing money and contracting.", "opposite financial health"),
            ("The credit rating was upgraded to AA.", "The credit rating was downgraded to BB.", "upgrade vs downgrade"),
        ],
    },
    "medical": {
        "positive": [
            ("The patient is recovering well after surgery.", "The patient shows good post-operative progress.", "paraphrase"),
            ("Hypertension increases the risk of stroke.", "High blood pressure is a major risk factor for cerebrovascular events.", "paraphrase"),
            ("The drug inhibits tumor cell proliferation.", "The medication prevents cancer cells from dividing.", "paraphrase"),
        ],
        "negative": [
            ("The patient has been diagnosed with diabetes.", "The algorithm achieved state-of-the-art performance on benchmarks.", "unrelated"),
            ("Blood pressure should be monitored regularly.", "The latest smartphone features an improved camera.", "unrelated"),
        ],
        "hard_negative": [
            ("The medication is effective for treating hypertension.", "The medication is contraindicated for patients with hypertension.", "effective vs contraindicated"),
            ("The biopsy results were benign.", "The biopsy results were malignant.", "benign vs malignant"),
            ("The patient's condition improved significantly.", "The patient's condition deteriorated significantly.", "improved vs deteriorated"),
            ("The drug has minimal side effects.", "The drug has severe side effects.", "minimal vs severe"),
        ],
    },
    "general": {
        "positive": [
            ("The quick brown fox jumps over the lazy dog.", "A fast auburn fox leaps across a sleepy canine.", "paraphrase"),
            ("Machine learning models require large amounts of training data.", "Deep learning systems need extensive datasets for training.", "paraphrase"),
            ("Climate change is causing global temperatures to rise.", "Global warming is increasing average temperatures worldwide.", "paraphrase"),
        ],
        "negative": [
            ("The recipe calls for two cups of flour.", "The rocket reached escape velocity.", "unrelated"),
            ("She plays piano every evening.", "The database query returned 1000 results.", "unrelated"),
        ],
        "hard_negative": [
            ("The experiment was successful.", "The experiment was unsuccessful.", "success vs failure"),
            ("The solution is optimal.", "The solution is suboptimal.", "optimal vs suboptimal"),
            ("The results confirm the hypothesis.", "The results reject the hypothesis.", "confirm vs reject"),
        ],
    },
    "legal": {
        "positive": [
            ("The defendant was found guilty of the charges.", "The court convicted the accused on all counts.", "paraphrase"),
            ("The contract was terminated due to breach.", "The agreement was voided following a violation of its terms.", "paraphrase"),
            ("The court issued an injunction to halt the proceedings.", "A court order was granted to stop the action.", "paraphrase"),
            ("The plaintiff seeks damages for negligence.", "The claimant demands compensation for careless conduct.", "paraphrase"),
            ("The statute of limitations has expired.", "The legal time limit for filing the claim has passed.", "paraphrase"),
        ],
        "negative": [
            ("The defendant filed a motion to dismiss.", "The patient was prescribed antibiotics.", "unrelated"),
            ("The jury returned a verdict of not guilty.", "The algorithm converged after 100 epochs.", "unrelated"),
            ("The merger was approved by the antitrust authority.", "The atmospheric pressure dropped significantly.", "unrelated"),
        ],
        "hard_negative": [
            ("The defendant is liable for the damages.", "The defendant is not liable for the damages.", "liable vs not liable"),
            ("The contract is enforceable under current law.", "The contract is unenforceable under current law.", "enforceable vs unenforceable"),
            ("The court upheld the lower court's decision.", "The court overturned the lower court's decision.", "upheld vs overturned"),
            ("The accused was acquitted of all charges.", "The accused was convicted of all charges.", "acquitted vs convicted"),
            ("The injunction was granted by the judge.", "The injunction was denied by the judge.", "granted vs denied"),
            ("The appeal was successful and the verdict was reversed.", "The appeal was unsuccessful and the verdict was upheld.", "reversed vs upheld"),
        ],
    },
    "code": {
        "positive": [
            ("The function returns None if the input is invalid.", "The method returns null when the provided argument is not valid.", "paraphrase"),
            ("The loop iterates over each element in the list.", "The for-loop processes every item in the array.", "paraphrase"),
            ("The variable is declared as a constant and cannot be reassigned.", "The identifier is defined as immutable and its value cannot change.", "paraphrase"),
            ("The API endpoint accepts a POST request with a JSON body.", "The REST endpoint handles HTTP POST with a JSON payload.", "paraphrase"),
            ("The recursive function calls itself until the base case is reached.", "The self-referential function terminates when it hits the stopping condition.", "paraphrase"),
        ],
        "negative": [
            ("The function sorts the list in ascending order.", "The bond yield rose sharply this quarter.", "unrelated"),
            ("The class inherits from the base interface.", "The patient's blood pressure is elevated.", "unrelated"),
            ("The database query uses an index for faster lookup.", "The stock market fell 3% today.", "unrelated"),
        ],
        "hard_negative": [
            ("The function raises an exception when the file is not found.", "The function silently returns None when the file is not found.", "raises vs silent"),
            ("The loop terminates when the condition is True.", "The loop terminates when the condition is False.", "True vs False termination"),
            ("The sort is stable: equal elements preserve their original order.", "The sort is unstable: equal elements may change their original order.", "stable vs unstable"),
            ("The function is thread-safe and can be called concurrently.", "The function is not thread-safe and must be called sequentially.", "thread-safe vs unsafe"),
            ("The cache stores the result of the computation.", "The cache invalidates and discards the result of the computation.", "stores vs invalidates"),
            ("The API call is synchronous and blocks until completion.", "The API call is asynchronous and returns a promise immediately.", "sync vs async"),
        ],
    },
}


def _generate_rule_based(
    domain: str,
    n_positive: int,
    n_negative: int,
    n_hard_negative: int,
    n_boundary: int,
) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict]]:
    """Generate pairs using rule-based templates (no LLM fallback)."""
    templates = DOMAIN_TEMPLATES.get(domain, DOMAIN_TEMPLATES["general"])
    rng = random.Random(42)

    def _sample(items: List, n: int) -> List:
        if len(items) >= n:
            return rng.sample(items, n)
        # With replacement if not enough templates
        return [rng.choice(items) for _ in range(n)]

    positives = [{"text_a": a, "text_b": b, "notes": note}
                 for a, b, note in _sample(templates.get("positive", []), n_positive)]
    negatives = [{"text_a": a, "text_b": b, "notes": note}
                 for a, b, note in _sample(templates.get("negative", []), n_negative)]
    hard_negs = [{"text_a": a, "text_b": b, "notes": note}
                 for a, b, note in _sample(templates.get("hard_negative", []), n_hard_negative)]
    # Generate simple boundary cases by mixing positive/hard-negative
    boundary = []
    for i in range(n_boundary):
        base = rng.choice(templates.get("hard_negative", templates["positive"]))
        boundary.append({"text_a": base[0], "text_b": base[1], "notes": f"boundary: {base[2]}"})

    return positives, negatives, hard_negs, boundary


# ─────────────────────────────────────────────────────────────
# Main generator class
# ─────────────────────────────────────────────────────────────

class SemanticDataGenerator:
    """LLM-driven semantic test data generator for vector database testing.

    Can operate in two modes:
    1. LLM mode: Calls an LLM API to generate rich, diverse semantic pairs
    2. Fallback mode: Uses built-in templates (no API key needed)

    Example usage (LLM mode):
        gen = SemanticDataGenerator(
            api_key="sk-...",
            model="gpt-4o-mini",
        )
        ds = gen.generate(domain="finance", n_positives=30, n_hard_negatives=30)
        ds.save("datasets/finance.json")

    Example usage (offline mode):
        gen = SemanticDataGenerator()
        ds = gen.generate(domain="finance", n_positives=5, n_hard_negatives=5)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        embedding_fn: Optional[Callable[[List[str]], List[List[float]]]] = None,
        temperature: float = 0.7,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.embedding_fn = embedding_fn
        self.temperature = temperature
        self._use_llm = api_key is not None

    def _call_llm(self, prompt: str) -> str:
        """Call LLM and return response text."""
        return _call_llm_openai_compatible(
            prompt=prompt,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            temperature=self.temperature,
        )

    def _generate_pairs_llm(
        self,
        pair_type: str,
        domain: str,
        n: int,
    ) -> List[Dict[str, str]]:
        """Generate pairs using LLM. Returns list of {text_a, text_b, notes} dicts."""
        prompt_key = {
            "positive": "positive_pairs",
            "negative": "negative_pairs",
            "hard_negative": "hard_negatives",
            "boundary": "boundary_cases",
        }[pair_type]

        prompt = PROMPTS[prompt_key].format(n=n, domain=domain)
        raw = self._call_llm(prompt)
        return _parse_json_from_response(raw)

    def _generate_metamorphic_relations_llm(self, domain: str, n: int = 5) -> List[Dict]:
        """Generate metamorphic relations using LLM."""
        domain_short = domain[:3].upper()
        prompt = PROMPTS["metamorphic_relations"].format(
            n=n, domain=domain, domain_short=domain_short
        )
        raw = self._call_llm(prompt)
        return _parse_json_from_response(raw)

    def _default_metamorphic_relations(self, domain: str) -> List[Dict]:
        """Return default metamorphic relations (no LLM needed)."""
        return [
            {
                "relation_id": f"MR-{domain[:3].upper()}-01",
                "name": "Semantic Equivalence Consistency",
                "description": "If two queries are semantically equivalent, their top-K results should have ≥80% overlap",
                "input_transformation": "Replace query with a semantically equivalent paraphrase",
                "expected_output_property": "Recall(results_Q1, results_Q2) >= 0.80",
                "domain": domain,
                "testable": True,
                "test_strategy": "Generate positive pairs as query pairs; measure result set overlap",
            },
            {
                "relation_id": f"MR-{domain[:3].upper()}-02",
                "name": "Semantic Distance Monotonicity",
                "description": "If doc A is semantically closer to query Q than doc B, rank(A) must be better than rank(B)",
                "input_transformation": "Compare two documents with known relative semantic distances to a query",
                "expected_output_property": "rank(closer_doc) < rank(further_doc)",
                "domain": domain,
                "testable": True,
                "test_strategy": "Use ground-truth labeled pairs; verify ranking order",
            },
            {
                "relation_id": f"MR-{domain[:3].upper()}-03",
                "name": "Hard Negative Discrimination",
                "description": "Hard negative pairs (surface-similar but semantically different) should NOT appear as top-1 results for each other",
                "input_transformation": "Use text_a as query, search for text_b",
                "expected_output_property": "rank(text_b) > K/2 when searching with text_a (not in top half)",
                "domain": domain,
                "testable": True,
                "test_strategy": "Use hard_negative pairs; search text_a for text_b and verify rank",
            },
            {
                "relation_id": f"MR-{domain[:3].upper()}-04",
                "name": "Negative Pair Rejection",
                "description": "Semantically dissimilar texts should not appear in each other's top-K results",
                "input_transformation": "Use text_a as query, check if text_b appears in top-K",
                "expected_output_property": "text_b NOT in top-K results when searching with text_a",
                "domain": domain,
                "testable": True,
                "test_strategy": "Use negative pairs; verify neither text appears in the other's top-K",
            },
            {
                "relation_id": f"MR-{domain[:3].upper()}-05",
                "name": "Distance Symmetry",
                "description": "Distance(A, B) should approximately equal Distance(B, A)",
                "input_transformation": "Swap query and document roles",
                "expected_output_property": "|rank_A_in_results_B - rank_B_in_results_A| <= tolerance",
                "domain": domain,
                "testable": True,
                "test_strategy": "Search both directions; compare relative rankings",
            },
        ]

    def generate(
        self,
        domain: str = "general",
        n_positives: int = 20,
        n_negatives: int = 10,
        n_hard_negatives: int = 20,
        n_boundary: int = 10,
        n_metamorphic_relations: int = 5,
        embed_vectors: bool = False,
    ) -> SemanticTestDataset:
        """Generate a complete semantic test dataset.

        Args:
            domain: Domain for generated texts (e.g., "finance", "medical", "general")
            n_positives: Number of positive (similar) pairs
            n_negatives: Number of negative (dissimilar) pairs
            n_hard_negatives: Number of hard negative pairs (core innovation)
            n_boundary: Number of boundary/ambiguous pairs
            n_metamorphic_relations: Number of metamorphic relations to generate
            embed_vectors: If True and embedding_fn is set, embed all texts to vectors

        Returns:
            SemanticTestDataset with all pairs and metamorphic relations
        """
        ds = SemanticTestDataset(
            dataset_id=f"sem-{domain}-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            domain=domain,
            created_at=datetime.now().isoformat(),
        )

        type_configs = [
            ("positive",      n_positives,     "close"),
            ("negative",      n_negatives,     "far"),
            ("hard_negative", n_hard_negatives,"far"),  # surface similar, but semantically far
            ("boundary",      n_boundary,      "ambiguous"),
        ]

        if self._use_llm:
            print(f"  Generating with LLM ({self.model})...")
        else:
            print(f"  Generating with built-in templates (no LLM)...")
            # Pre-generate all rule-based data
            rb_pos, rb_neg, rb_hard, rb_bound = _generate_rule_based(
                domain, n_positives, n_negatives, n_hard_negatives, n_boundary
            )
            rule_based_data = {
                "positive": rb_pos,
                "negative": rb_neg,
                "hard_negative": rb_hard,
                "boundary": rb_bound,
            }

        pair_counter = 0
        for pair_type, n, expected_relation in type_configs:
            if n <= 0:
                continue
            print(f"    Generating {n} {pair_type} pairs...")

            if self._use_llm:
                try:
                    raw_pairs = self._generate_pairs_llm(pair_type, domain, n)
                except Exception as e:
                    print(f"    WARNING: LLM failed for {pair_type}: {e}. Using fallback.")
                    rb_pos, rb_neg, rb_hard, rb_bound = _generate_rule_based(domain, n, n, n, n)
                    raw_pairs = {"positive": rb_pos, "negative": rb_neg,
                                 "hard_negative": rb_hard, "boundary": rb_bound}[pair_type]
            else:
                raw_pairs = rule_based_data[pair_type]

            for i, item in enumerate(raw_pairs[:n]):
                pair = TextPair(
                    pair_id=f"{domain}-{pair_type}-{pair_counter:04d}",
                    text_a=item.get("text_a", ""),
                    text_b=item.get("text_b", ""),
                    pair_type=pair_type,
                    domain=domain,
                    expected_relation=expected_relation,
                    semantic_notes=item.get("notes", ""),
                )
                ds.pairs.append(pair)
                pair_counter += 1

        # Generate metamorphic relations
        print(f"    Generating {n_metamorphic_relations} metamorphic relations...")
        if self._use_llm:
            try:
                ds.metamorphic_relations = self._generate_metamorphic_relations_llm(domain, n_metamorphic_relations)
            except Exception as e:
                print(f"    WARNING: LLM failed for metamorphic relations: {e}. Using defaults.")
                ds.metamorphic_relations = self._default_metamorphic_relations(domain)
        else:
            ds.metamorphic_relations = self._default_metamorphic_relations(domain)

        # Optionally embed all texts
        if embed_vectors and self.embedding_fn is not None:
            print(f"    Embedding {len(ds.pairs) * 2} texts...")
            all_texts = []
            for pair in ds.pairs:
                all_texts.append(pair.text_a)
                all_texts.append(pair.text_b)
            vectors = self.embedding_fn(all_texts)
            for i, pair in enumerate(ds.pairs):
                pair.vector_a = vectors[i * 2]
                pair.vector_b = vectors[i * 2 + 1]

        print(f"  Dataset generated: {ds.stats()}")
        return ds


# ─────────────────────────────────────────────────────────────
# Convenience functions
# ─────────────────────────────────────────────────────────────

def generate_offline(
    domain: str = "general",
    n_positives: int = 10,
    n_negatives: int = 5,
    n_hard_negatives: int = 10,
    n_boundary: int = 5,
) -> SemanticTestDataset:
    """Generate a semantic dataset without any LLM API calls (for development/testing)."""
    gen = SemanticDataGenerator()
    return gen.generate(
        domain=domain,
        n_positives=n_positives,
        n_negatives=n_negatives,
        n_hard_negatives=n_hard_negatives,
        n_boundary=n_boundary,
        n_metamorphic_relations=5,
        embed_vectors=False,
    )


def generate_with_llm(
    api_key: str,
    domain: str = "general",
    model: str = "gpt-4o-mini",
    base_url: str = "https://api.openai.com/v1",
    n_positives: int = 30,
    n_negatives: int = 15,
    n_hard_negatives: int = 30,
    n_boundary: int = 15,
    embedding_fn: Optional[Callable] = None,
) -> SemanticTestDataset:
    """Generate a full LLM-enriched semantic dataset."""
    gen = SemanticDataGenerator(
        api_key=api_key,
        base_url=base_url,
        model=model,
        embedding_fn=embedding_fn,
    )
    return gen.generate(
        domain=domain,
        n_positives=n_positives,
        n_negatives=n_negatives,
        n_hard_negatives=n_hard_negatives,
        n_boundary=n_boundary,
        n_metamorphic_relations=5,
        embed_vectors=(embedding_fn is not None),
    )
