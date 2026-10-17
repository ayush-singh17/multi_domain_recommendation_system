"""
encoder.py — one place that loads the text encoder, used by BOTH the embedding script
and the app, so journals and abstracts are always embedded the same way.

    from encoder import load_encoder
    model = load_encoder("allenai/specter2_base", adapter=True)   # SPECTER2 + retrieval adapter
    model = load_encoder("sentence-transformers/all-mpnet-base-v2")   # any sentence-transformers model
    vecs = model.encode(["some text"], normalize_embeddings=True)    # numpy, L2-normalised

The adapter version needs:  pip install adapters
It uses the CLS-token embedding, which is how SPECTER2 is meant to be used.
"""
import numpy as np


def _device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class SpecterAdapterEncoder:
    """allenai/specter2_base + the allenai/specter2 retrieval adapter, CLS embedding."""

    def __init__(self, base="allenai/specter2_base", adapter_repo="allenai/specter2", max_length=512):
        import torch
        from transformers import AutoTokenizer
        from adapters import AutoAdapterModel
        self.torch, self.max_length = torch, max_length
        self.tok = AutoTokenizer.from_pretrained(base)
        self.model = AutoAdapterModel.from_pretrained(base)
        name = self.model.load_adapter(adapter_repo, source="hf", load_as="proximity", set_active=True)
        self.model.set_active_adapters(name)            # make sure it is really switched on
        self.dev = _device()
        self.model.to(self.dev).eval()
        print(f"  Encoder: {base} + adapter '{adapter_repo}' on {self.dev}")

    def encode(self, texts, batch_size=32, normalize_embeddings=True, **kwargs):
        if isinstance(texts, str):
            texts = [texts]
        out = []
        with self.torch.no_grad():
            for i in range(0, len(texts), batch_size):
                b = self.tok(list(texts[i:i + batch_size]), padding=True, truncation=True,
                             max_length=self.max_length, return_tensors="pt",
                             return_token_type_ids=False).to(self.dev)
                h = self.model(**b).last_hidden_state[:, 0, :]          # CLS token
                if normalize_embeddings:
                    h = self.torch.nn.functional.normalize(h, dim=1)
                out.append(h.cpu().numpy())
        return np.vstack(out).astype(np.float32)


def load_encoder(model_name="allenai/specter2_base", adapter=False):
    if adapter:
        return SpecterAdapterEncoder(base=model_name)
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(model_name)
    dev = _device()
    if dev != "cpu":
        m = m.to(dev)
    print(f"  Encoder: {model_name} on {dev}")
    return m
