from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.ai.preprocess import TextPreprocessor


SegmentBoundary = Literal[
    "continuation",
    "sentence",
    "paragraph",
    "none",
]


@dataclass(
    frozen=True,
    slots=True,
)
class TextSegment:
    """
    One engine-safe part of a longer synthesis request.

    source_text:
        Readable normalized text suitable for diagnostics.

    synthesis_text:
        Text sent to the selected speech engine, including supported
        technical-term expansions.

    boundary_after:
        A signal later used by the WAV joiner to choose the pause
        inserted after this segment.
    """

    index: int
    paragraph_index: int
    source_text: str
    synthesis_text: str
    boundary_after: SegmentBoundary

    @property
    def source_character_count(
        self,
    ) -> int:
        return len(self.source_text)

    @property
    def synthesis_character_count(
        self,
    ) -> int:
        return len(self.synthesis_text)


@dataclass(
    frozen=True,
    slots=True,
)
class _AtomicTextUnit:
    text: str
    boundary_after: SegmentBoundary


class TextSegmenter:
    """
    Deterministically split API-valid text into engine-safe segments.

    This class performs text work only. It does not choose engines,
    generate audio, join WAV files, or create history records.
    """

    DEFAULT_MAX_SYNTHESIS_CHARACTERS = (
        TextPreprocessor.MAX_SINGLE_REQUEST_CHARACTERS
    )

    _CLOSING_CHARACTERS = frozenset(
        {
            '"',
            "'",
            ")",
            "]",
            "}",
        }
    )

    _NON_TERMINAL_ABBREVIATIONS = frozenset(
        {
            "dr.",
            "e.g.",
            "etc.",
            "i.e.",
            "jr.",
            "mr.",
            "mrs.",
            "ms.",
            "prof.",
            "sr.",
            "vs.",
        }
    )

    @classmethod
    def _prepare_synthesis_text(
        cls,
        source_text: str,
    ) -> str:
        flattened = re.sub(
            r"\s+",
            " ",
            source_text,
        ).strip()

        return TextPreprocessor.expand_technical_terms(
            flattened
        )

    @classmethod
    def _fits(
        cls,
        source_text: str,
        maximum: int,
    ) -> bool:
        return (
            len(
                cls._prepare_synthesis_text(
                    source_text
                )
            )
            <= maximum
        )

    @classmethod
    def _sentence_boundary_end(
        cls,
        text: str,
        index: int,
    ) -> int | None:
        character = text[index]

        if character not in {
            ".",
            "!",
            "?",
        }:
            return None

        if character == ".":
            # Only the final dot of an ellipsis may end a sentence.
            if (
                index + 1 < len(text)
                and text[index + 1] == "."
            ):
                return None

            # Do not split decimal numbers such as 3.14.
            if (
                index > 0
                and index + 1 < len(text)
                and text[index - 1].isdigit()
                and text[index + 1].isdigit()
            ):
                return None

            token_start = index

            while (
                token_start > 0
                and not text[
                    token_start - 1
                ].isspace()
            ):
                token_start -= 1

            token = (
                text[
                    token_start:index + 1
                ]
                .strip()
                .lower()
            )

            if (
                token
                in cls._NON_TERMINAL_ABBREVIATIONS
            ):
                return None

        cursor = index + 1

        while (
            cursor < len(text)
            and text[cursor]
            in cls._CLOSING_CHARACTERS
        ):
            cursor += 1

        if (
            cursor == len(text)
            or text[cursor].isspace()
        ):
            return cursor

        return None

    @classmethod
    def _split_sentences(
        cls,
        paragraph: str,
    ) -> list[str]:
        sentences: list[str] = []

        start = 0
        index = 0

        while index < len(paragraph):
            boundary_end = (
                cls._sentence_boundary_end(
                    paragraph,
                    index,
                )
            )

            if boundary_end is None:
                index += 1
                continue

            sentence = paragraph[
                start:boundary_end
            ].strip()

            if sentence:
                sentences.append(sentence)

            index = boundary_end

            while (
                index < len(paragraph)
                and paragraph[index].isspace()
            ):
                index += 1

            start = index

        remainder = paragraph[start:].strip()

        if remainder:
            sentences.append(remainder)

        return sentences

    @classmethod
    def _split_oversized_unit(
        cls,
        text: str,
        maximum: int,
    ) -> list[str]:
        if cls._fits(
            text,
            maximum,
        ):
            return [text]

        words = text.split()

        if not words:
            return []

        chunks: list[str] = []
        current_words: list[str] = []

        for word in words:
            if not cls._fits(
                word,
                maximum,
            ):
                raise ValueError(
                    "A single token exceeds the "
                    f"{maximum}-character synthesis limit. "
                    "Shorten or separate that token before "
                    "generating speech."
                )

            candidate_words = [
                *current_words,
                word,
            ]

            candidate = " ".join(
                candidate_words
            )

            if cls._fits(
                candidate,
                maximum,
            ):
                current_words = (
                    candidate_words
                )

                continue

            if current_words:
                chunks.append(
                    " ".join(
                        current_words
                    )
                )

            current_words = [word]

        if current_words:
            chunks.append(
                " ".join(
                    current_words
                )
            )

        return chunks

    @classmethod
    def _paragraph_units(
        cls,
        paragraph: str,
        maximum: int,
    ) -> list[_AtomicTextUnit]:
        sentences = cls._split_sentences(
            paragraph
        )

        units: list[_AtomicTextUnit] = []

        for sentence in sentences:
            chunks = (
                cls._split_oversized_unit(
                    sentence,
                    maximum,
                )
            )

            for chunk_index, chunk in enumerate(
                chunks
            ):
                is_final_chunk = (
                    chunk_index
                    == len(chunks) - 1
                )

                boundary: SegmentBoundary = (
                    "sentence"
                    if is_final_chunk
                    else "continuation"
                )

                units.append(
                    _AtomicTextUnit(
                        text=chunk,
                        boundary_after=boundary,
                    )
                )

        return units

    @classmethod
    def _pack_paragraph_units(
        cls,
        units: list[_AtomicTextUnit],
        maximum: int,
    ) -> list[
        tuple[
            str,
            SegmentBoundary,
        ]
    ]:
        packed: list[
            tuple[
                str,
                SegmentBoundary,
            ]
        ] = []

        current_text = ""
        current_boundary: SegmentBoundary = (
            "none"
        )

        for unit in units:
            candidate = (
                unit.text
                if not current_text
                else (
                    current_text
                    + " "
                    + unit.text
                )
            )

            if (
                current_text
                and not cls._fits(
                    candidate,
                    maximum,
                )
            ):
                packed.append(
                    (
                        current_text,
                        current_boundary,
                    )
                )

                current_text = unit.text
                current_boundary = (
                    unit.boundary_after
                )

                continue

            current_text = candidate
            current_boundary = (
                unit.boundary_after
            )

        if current_text:
            packed.append(
                (
                    current_text,
                    current_boundary,
                )
            )

        return packed

    @classmethod
    def segment(
        cls,
        text: str,
        *,
        max_synthesis_characters: int | None = None,
    ) -> list[TextSegment]:
        """
        Split API-valid text into ordered engine-safe segments.

        Paragraphs are never merged together. Sentences inside the
        same paragraph are greedily packed while remaining below the
        engine limit.
        """

        maximum = (
            max_synthesis_characters
            if max_synthesis_characters
            is not None
            else (
                cls.DEFAULT_MAX_SYNTHESIS_CHARACTERS
            )
        )

        if not isinstance(
            maximum,
            int,
        ):
            raise TypeError(
                "The segment character limit must be an integer."
            )

        if maximum < 16:
            raise ValueError(
                "The segment character limit must be at least 16."
            )

        if (
            maximum
            > TextPreprocessor.MAX_SINGLE_REQUEST_CHARACTERS
        ):
            raise ValueError(
                "The segment character limit cannot exceed "
                f"{TextPreprocessor.MAX_SINGLE_REQUEST_CHARACTERS}."
            )

        normalized = (
            TextPreprocessor.validate_api_text(
                text
            )
        )

        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(
                r"\n{2,}",
                normalized,
            )
            if paragraph.strip()
        ]

        pending_segments: list[
            tuple[
                int,
                str,
                SegmentBoundary,
            ]
        ] = []

        for paragraph_index, paragraph in enumerate(
            paragraphs
        ):
            units = cls._paragraph_units(
                paragraph,
                maximum,
            )

            packed_units = (
                cls._pack_paragraph_units(
                    units,
                    maximum,
                )
            )

            if not packed_units:
                continue

            final_paragraph = (
                paragraph_index
                == len(paragraphs) - 1
            )

            for packed_index, (
                source_text,
                boundary_after,
            ) in enumerate(
                packed_units
            ):
                final_in_paragraph = (
                    packed_index
                    == len(packed_units) - 1
                )

                if final_in_paragraph:
                    boundary_after = (
                        "none"
                        if final_paragraph
                        else "paragraph"
                    )

                pending_segments.append(
                    (
                        paragraph_index,
                        source_text,
                        boundary_after,
                    )
                )

        segments: list[TextSegment] = []

        for index, (
            paragraph_index,
            source_text,
            boundary_after,
        ) in enumerate(
            pending_segments
        ):
            synthesis_text = (
                cls._prepare_synthesis_text(
                    source_text
                )
            )

            if not source_text:
                raise RuntimeError(
                    "The segmenter produced an empty source segment."
                )

            if not synthesis_text:
                raise RuntimeError(
                    "The segmenter produced an empty synthesis segment."
                )

            if len(synthesis_text) > maximum:
                raise RuntimeError(
                    "The segmenter produced an over-limit segment."
                )

            segments.append(
                TextSegment(
                    index=index,
                    paragraph_index=(
                        paragraph_index
                    ),
                    source_text=source_text,
                    synthesis_text=(
                        synthesis_text
                    ),
                    boundary_after=(
                        boundary_after
                    ),
                )
            )

        if not segments:
            raise ValueError(
                "No speech segments could be produced."
            )

        return segments

    @classmethod
    def split(
        cls,
        text: str,
        *,
        max_synthesis_characters: int | None = None,
    ) -> list[TextSegment]:
        """
        Backward-friendly alias for segment().
        """

        return cls.segment(
            text,
            max_synthesis_characters=(
                max_synthesis_characters
            ),
        )


text_segmenter = TextSegmenter()
