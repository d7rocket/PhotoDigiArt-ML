"""CLIP BPE tokenizer for text label encoding.

Pure Python/numpy implementation -- no torch dependency required.
Loads vocabulary from OpenAI's bpe_simple_vocab_16e6.txt.gz file.

Based on OpenAI CLIP simple_tokenizer.py (MIT license).
"""

from __future__ import annotations

import gzip
import html
import logging
import os
import re
from functools import lru_cache

import numpy as np

logger = logging.getLogger(__name__)

# CLIP special tokens
_SOT_TOKEN = 49406  # <|startoftext|>
_EOT_TOKEN = 49407  # <|endoftext|>
_CONTEXT_LENGTH = 77


@lru_cache()
def _bytes_to_unicode() -> dict[int, str]:
    """Map byte values to unicode characters (BPE vocabulary encoding)."""
    bs = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("\xa1"), ord("\xac") + 1))
        + list(range(ord("\xae"), ord("\xff") + 1))
    )
    cs = bs[:]
    n = 0
    for b in range(2**8):
        if b not in bs:
            bs.append(b)
            cs.append(2**8 + n)
            n += 1
    return dict(zip(bs, [chr(c) for c in cs]))


def _get_pairs(word: tuple[str, ...]) -> set[tuple[str, str]]:
    """Get all adjacent symbol pairs in a word."""
    pairs = set()
    prev = word[0]
    for char in word[1:]:
        pairs.add((prev, char))
        prev = char
    return pairs


def _basic_clean(text: str) -> str:
    """Basic text cleaning."""
    text = html.unescape(html.unescape(text))
    return text.strip()


def _whitespace_clean(text: str) -> str:
    """Collapse whitespace."""
    return re.sub(r"\s+", " ", text).strip()


class CLIPTokenizer:
    """BPE tokenizer for CLIP text encoder.

    Tokenizes text labels into (1, 77) int32 arrays matching the
    CLIP text encoder input format.

    Args:
        vocab_path: Path to bpe_simple_vocab_16e6.txt.gz vocabulary file.
    """

    def __init__(self, vocab_path: str = "models/bpe_simple_vocab_16e6.txt.gz") -> None:
        self._vocab_path = vocab_path
        self._bpe_ranks: dict[tuple[str, str], int] | None = None
        self._encoder: dict[str, int] | None = None
        self._decoder: dict[int, str] | None = None
        self._byte_encoder = _bytes_to_unicode()
        self._byte_decoder = {v: k for k, v in self._byte_encoder.items()}
        self._cache: dict[str, str] = {}
        # Pattern matching CLIP's original tokenizer but using standard re
        # instead of \p{L}/\p{N} unicode property escapes
        self._pat = re.compile(
            r"""<\|startoftext\|>|<\|endoftext\|>|'s|'t|'re|'ve|'m|'ll|'d|[a-zA-Z]+|[0-9]|[^\s\w]+""",
            re.IGNORECASE,
        )

    def _ensure_loaded(self) -> None:
        """Load vocabulary on first use."""
        if self._bpe_ranks is not None:
            return

        if not os.path.isfile(self._vocab_path):
            raise FileNotFoundError(
                f"BPE vocabulary not found at '{self._vocab_path}'. "
                "Download bpe_simple_vocab_16e6.txt.gz from "
                "https://github.com/openai/CLIP/blob/main/clip/bpe_simple_vocab_16e6.txt.gz "
                "and place it in the models/ directory."
            )

        with gzip.open(self._vocab_path, "rt", encoding="utf-8") as f:
            lines = f.read().split("\n")

        # First line is version header, merges start at line 1
        merges = lines[1 : 49152 - 256 - 2 + 1]
        merges = [tuple(merge.split()) for merge in merges]
        self._bpe_ranks = dict(zip(merges, range(len(merges))))

        # Build encoder vocabulary
        vocab = list(_bytes_to_unicode().values())
        vocab = vocab + [v + "</w>" for v in vocab]
        for merge in merges:
            vocab.append("".join(merge))
        vocab.extend(["<|startoftext|>", "<|endoftext|>"])
        self._encoder = dict(zip(vocab, range(len(vocab))))
        self._decoder = {v: k for k, v in self._encoder.items()}

    def _bpe(self, token: str) -> str:
        """Apply BPE encoding to a single token."""
        if token in self._cache:
            return self._cache[token]

        word = tuple(token[:-1]) + (token[-1] + "</w>",)
        pairs = _get_pairs(word)

        if not pairs:
            return token + "</w>"

        while True:
            bigram = min(pairs, key=lambda pair: self._bpe_ranks.get(pair, float("inf")))
            if bigram not in self._bpe_ranks:
                break
            first, second = bigram
            new_word: list[str] = []
            i = 0
            while i < len(word):
                try:
                    j = word.index(first, i)
                except ValueError:
                    new_word.extend(word[i:])
                    break
                new_word.extend(word[i:j])
                i = j
                if word[i] == first and i < len(word) - 1 and word[i + 1] == second:
                    new_word.append(first + second)
                    i += 2
                else:
                    new_word.append(word[i])
                    i += 1
            word = tuple(new_word)
            if len(word) == 1:
                break
            pairs = _get_pairs(word)

        result = " ".join(word)
        self._cache[token] = result
        return result

    def _encode(self, text: str) -> list[int]:
        """Encode text to BPE token IDs."""
        self._ensure_loaded()
        bpe_tokens: list[int] = []
        text = _whitespace_clean(_basic_clean(text)).lower()
        for token in re.findall(self._pat, text):
            encoded = "".join(self._byte_encoder[b] for b in token.encode("utf-8"))
            bpe_tokens.extend(
                self._encoder[bpe_token] for bpe_token in self._bpe(encoded).split(" ")
            )
        return bpe_tokens

    def tokenize(self, text: str) -> np.ndarray:
        """Tokenize text into a (1, 77) int32 array for CLIP text encoder.

        Adds SOT/EOT tokens and zero-pads to context length 77.

        Args:
            text: Input text string.

        Returns:
            numpy array of shape (1, 77), dtype int32.
        """
        tokens = [_SOT_TOKEN] + self._encode(text) + [_EOT_TOKEN]
        result = np.zeros((1, _CONTEXT_LENGTH), dtype=np.int32)
        tokens = tokens[:_CONTEXT_LENGTH]  # Truncate if too long
        result[0, : len(tokens)] = tokens
        return result

    def tokenize_batch(self, texts: list[str]) -> np.ndarray:
        """Tokenize multiple texts into (N, 77) int32 array.

        Args:
            texts: List of input text strings.

        Returns:
            numpy array of shape (N, 77), dtype int32.
        """
        result = np.zeros((len(texts), _CONTEXT_LENGTH), dtype=np.int32)
        for i, text in enumerate(texts):
            tokens = [_SOT_TOKEN] + self._encode(text) + [_EOT_TOKEN]
            tokens = tokens[:_CONTEXT_LENGTH]
            result[i, : len(tokens)] = tokens
        return result
