"""BERTScore (Zhang et al., ICLR 2020), implemented here after course slides L14 p34-36 (Track C).

Each token of the candidate and of the reference gets a contextual vector from one layer of a pre-trained encoder; S[i, j] is the cosine of candidate
token i and reference token j. Greedy matching: P = mean over candidate tokens of max_j S, R = mean over reference tokens of max_i S, F = 2PR/(P+R).
Optional idf weighting (idf(w) = -log((df+1)/(N+1)), smoothed so an unseen token is finite) makes rare tokens count more.
Not rescaled: raw cosines sit high even for unrelated text, so compare rankings under identical settings, never raw numbers across settings.
Why our own code instead of the `bert_score` package: the Thai model and layer are chosen by a test (scripts/select_bertscore_model.py), and the
package ships layer defaults and baselines only for a few models. The pure maths (`greedy_scores`) is tested without any model.
"""

from __future__ import annotations

import math
from collections import Counter

import numpy as np


def greedy_scores(cand: np.ndarray, ref: np.ndarray, cand_w: np.ndarray | None = None, ref_w: np.ndarray | None = None) -> tuple[float, float, float]:
    """cand (n, d) and ref (m, d), rows L2-normalised. Returns (P, R, F1)."""
    sim = cand @ ref.T
    cw = np.ones(len(cand)) if cand_w is None else cand_w
    rw = np.ones(len(ref)) if ref_w is None else ref_w
    p = float((sim.max(axis=1) * cw).sum() / cw.sum())
    r = float((sim.max(axis=0) * rw).sum() / rw.sum())
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


class BertScorer:
    """`layers` lists every layer that may be scored (hidden_states index, 1..n); one forward pass keeps all of them, so a layer search is cheap."""

    def __init__(self, model_name: str, layer: int | None = None, idf_texts: list[str] | None = None, max_length: int = 512, device: str = "cpu",
                 layers: list[int] | None = None):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch, self.name, self.max_length, self.device = torch, model_name, max_length, device
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(device).eval()
        n_layers = self.model.config.num_hidden_layers
        self.layer = n_layers if layer is None else layer          # hidden_states[0] is the embedding layer; n_layers is the last
        self.layers = sorted(set(layers or []) | {self.layer})
        if not all(1 <= i <= n_layers for i in self.layers):
            raise ValueError(f"layers must be within 1..{n_layers}")
        self._cache: dict[str, tuple[dict[int, np.ndarray], list[int]]] = {}
        self.idf: dict[int, float] | None = None
        if idf_texts:
            df: Counter = Counter()
            for t in idf_texts:
                df.update(set(self._ids(t)))
            n = len(idf_texts)
            self.idf = {i: -math.log((c + 1) / (n + 1)) for i, c in df.items()}
            self._idf_default = -math.log(1 / (n + 1))

    def _ids(self, text: str) -> list[int]:
        return self.tok(text, add_special_tokens=False, truncation=True, max_length=self.max_length - 2)["input_ids"]

    def embed(self, text: str) -> tuple[dict[int, np.ndarray], list[int]]:
        if text not in self._cache:
            enc = self.tok(text, return_tensors="pt", truncation=True, max_length=self.max_length).to(self.device)
            with self.torch.no_grad():
                states = self.model(**enc, output_hidden_states=True).hidden_states
            ids = enc["input_ids"][0].tolist()
            keep = [i for i, t in enumerate(ids) if t not in self.tok.all_special_ids]      # drop <s>, </s>, [CLS], [SEP], padding
            vecs = {}
            for layer in self.layers:
                v = states[layer][0][keep].cpu().numpy().astype("float32")
                vecs[layer] = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
            self._cache[text] = (vecs, [ids[i] for i in keep])
        return self._cache[text]

    def _weights(self, ids: list[int]) -> np.ndarray | None:
        return None if self.idf is None else np.array([self.idf.get(i, self._idf_default) for i in ids])

    def score(self, candidate: str, reference: str, layer: int | None = None) -> dict:
        layer = layer or self.layer
        c, cid = self.embed(candidate)
        r, rid = self.embed(reference)
        if not len(cid) or not len(rid):
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        p, rec, f = greedy_scores(c[layer], r[layer], self._weights(cid), self._weights(rid))
        return {"precision": p, "recall": rec, "f1": f}
