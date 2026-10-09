from __future__ import annotations

import re
import unicodedata


class TextPreprocessor:
    """
    Deterministic text preparation shared by language detection and TTS.

    Milestone 10.5 handles one synthesis request at a time.
    Long-script segmentation and audio joining belong to Milestone 10.6.
    """

    MAX_API_CHARACTERS = 10_000
    MAX_SINGLE_REQUEST_CHARACTERS = 1_500

    # These formatting characters commonly appear after copying text
    # from websites, documents, messaging applications, or AI tools.
    #
    # ZWNJ and ZWJ are deliberately preserved because Indic scripts
    # can use them for shaping and pronunciation.
    _REMOVED_CHARACTERS = str.maketrans(
        {
            "\ufeff": None,  # Byte-order mark
            "\u200b": None,  # Zero-width space
            "\u2060": None,  # Word joiner
            "\u00ad": None,  # Soft hyphen
        }
    )

    _PUNCTUATION_TRANSLATION = str.maketrans(
        {
            "\u2018": "'",
            "\u2019": "'",
            "\u201a": "'",
            "\u201b": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u201e": '"',
            "\u201f": '"',
            "\u2013": "-",
            "\u2014": "-",
            "\u2212": "-",
            "\u2026": "...",
        }
    )

    # Conservative acronym pronunciation helpers.
    #
    # Only uppercase standalone tokens are expanded. Lowercase text
    # and tokens inside URLs are deliberately preserved.
    _TECHNICAL_TERMS = {
        "AI": "A I",
        "API": "A P I",
        "CPU": "C P U",
        "DNS": "D N S",
        "GPU": "G P U",
        "HTTP": "H T T P",
        "HTTPS": "H T T P S",
        "IP": "I P",
        "JWT": "J W T",
        "ML": "M L",
        "SSL": "S S L",
        "TLS": "T L S",
        "UI": "U I",
        "URL": "U R L",
        "UX": "U X",
    }

    _TECHNICAL_TERM_PATTERN = re.compile(
        r"\b("
        + "|".join(
            sorted(
                _TECHNICAL_TERMS,
                key=len,
                reverse=True,
            )
        )
        + r")\b"
    )

    _URL_PATTERN = re.compile(
        r"\b(?:https?://|www\.)[^\s<>'\"]+",
        re.IGNORECASE,
    )

    # This is a conservative signal, not a complete language model.
    # At least two standalone marker words are required.
    _ROMANIZED_TELUGU_MARKERS = {
        "aithe",
        "ante",
        "asalu",
        "avuthundi",
        "chesi",
        "cheyyandi",
        "chuddam",
        "ela",
        "enduku",
        "enti",
        "ippudu",
        "jarugutundi",
        "kani",
        "ki",
        "kodithe",
        "kottandi",
        "lo",
        "mana",
        "manam",
        "meeku",
        "meeru",
        "mundu",
        "nunchi",
        "oka",
        "pampisthe",
        "tarvatha",
        "telusukundam",
        "tho",
        "undi",
        "untundi",
    }

    @classmethod
    def normalize(
        cls,
        text: str,
    ) -> str:
        """
        Normalise user text without expanding technical terms.

        This representation is suitable for display, history storage,
        validation, and language detection.
        """

        if not isinstance(text, str):
            raise TypeError(
                "Speech text must be a string."
            )

        normalized = unicodedata.normalize(
            "NFKC",
            text,
        )

        normalized = normalized.translate(
            cls._REMOVED_CHARACTERS
        )

        normalized = normalized.translate(
            cls._PUNCTUATION_TRANSLATION
        )

        normalized = normalized.replace(
            "\r\n",
            "\n",
        ).replace(
            "\r",
            "\n",
        )

        normalized = normalized.replace(
            "\u00a0",
            " ",
        ).replace(
            "\u202f",
            " ",
        )

        # Remove control and surrogate characters while keeping tabs
        # and newlines. Normal Telugu combining characters are kept.
        normalized = "".join(
            character
            for character in normalized
            if (
                character in {
                    "\n",
                    "\t",
                }
                or unicodedata.category(
                    character
                )
                not in {
                    "Cc",
                    "Cs",
                }
            )
        )

        # Normalise horizontal whitespace while retaining paragraphs.
        normalized = re.sub(
            r"[^\S\n]+",
            " ",
            normalized,
        )

        normalized = re.sub(
            r" *\n *",
            "\n",
            normalized,
        )

        normalized = re.sub(
            r"\n{3,}",
            "\n\n",
            normalized,
        )

        # Conservative punctuation cleanup.
        normalized = re.sub(
            r"\s+([,.;:!?])",
            r"\1",
            normalized,
        )

        normalized = re.sub(
            r"\.{4,}",
            "...",
            normalized,
        )

        normalized = re.sub(
            r"!{2,}",
            "!",
            normalized,
        )

        normalized = re.sub(
            r"\?{2,}",
            "?",
            normalized,
        )

        normalized = re.sub(
            r",{2,}",
            ",",
            normalized,
        )

        return normalized.strip()

    @classmethod
    def validate_api_text(
        cls,
        text: str,
    ) -> str:
        """
        Validate and return text accepted at the main API boundary.
        """

        normalized = cls.normalize(text)

        if not normalized:
            raise ValueError(
                "Speech text cannot be empty after preprocessing."
            )

        if (
            len(normalized)
            > cls.MAX_API_CHARACTERS
        ):
            raise ValueError(
                "Speech text cannot exceed "
                f"{cls.MAX_API_CHARACTERS} characters."
            )

        return normalized

    @classmethod
    def _protect_urls(
        cls,
        text: str,
    ) -> tuple[
        str,
        list[str],
    ]:
        urls: list[str] = []

        def replace_url(
            match: re.Match[str],
        ) -> str:
            urls.append(
                match.group(0)
            )

            return (
                f"\ue000"
                f"{len(urls) - 1}"
                f"\ue001"
            )

        protected = cls._URL_PATTERN.sub(
            replace_url,
            text,
        )

        return protected, urls

    @staticmethod
    def _restore_urls(
        text: str,
        urls: list[str],
    ) -> str:
        restored = text

        for index, url in enumerate(
            urls
        ):
            restored = restored.replace(
                f"\ue000{index}\ue001",
                url,
            )

        return restored

    @classmethod
    def expand_technical_terms(
        cls,
        text: str,
    ) -> str:
        """
        Expand supported uppercase acronyms while preserving URLs.
        """

        protected_text, urls = (
            cls._protect_urls(text)
        )

        expanded = (
            cls._TECHNICAL_TERM_PATTERN.sub(
                lambda match: (
                    cls._TECHNICAL_TERMS[
                        match.group(0)
                    ]
                ),
                protected_text,
            )
        )

        return cls._restore_urls(
            expanded,
            urls,
        )

    @classmethod
    def prepare_for_synthesis(
        cls,
        text: str,
    ) -> str:
        """
        Produce the single-request text sent to a speech engine.
        """

        normalized = cls.validate_api_text(
            text
        )

        synthesis_text = re.sub(
            r"\s*\n+\s*",
            " ",
            normalized,
        )

        synthesis_text = re.sub(
            r"\s+",
            " ",
            synthesis_text,
        ).strip()

        synthesis_text = (
            cls.expand_technical_terms(
                synthesis_text
            )
        )

        if (
            len(synthesis_text)
            > cls.MAX_SINGLE_REQUEST_CHARACTERS
        ):
            raise ValueError(
                "Single-request synthesis text cannot exceed "
                f"{cls.MAX_SINGLE_REQUEST_CHARACTERS} characters. "
                "Long-script segmentation will be added in "
                "Milestone 10.6."
            )

        return synthesis_text

    @classmethod
    def is_probably_romanized_telugu(
        cls,
        text: str,
    ) -> bool:
        """
        Return a conservative signal for Latin-script Telugu.

        This helper does not change routing by itself. Live-routing
        behaviour will be decided after isolated and audio tests.
        """

        normalized = cls.normalize(
            text
        ).lower()

        if any(
            "\u0c00"
            <= character
            <= "\u0c7f"
            for character in normalized
        ):
            return False

        tokens = set(
            re.findall(
                r"[a-z]+",
                normalized,
            )
        )

        marker_count = len(
            tokens
            & cls._ROMANIZED_TELUGU_MARKERS
        )

        return marker_count >= 2

    @classmethod
    def clean(
        cls,
        text: str,
    ) -> str:
        """
        Backward-compatible alias for normalisation.
        """

        return cls.normalize(text)

    @classmethod
    def validate(
        cls,
        text: str,
    ) -> bool:
        """
        Backward-compatible validation at the API boundary.
        """

        cls.validate_api_text(text)

        return True
