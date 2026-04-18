import re

import spacy


class SpacyPreprocessor:
    def __init__(self, model_name: str = "en_core_web_sm"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError as exc:
            raise RuntimeError(
                f"spaCy model '{model_name}' is not installed. "
                f"Run: python -m spacy download {model_name}"
            ) from exc

    def transform(self, texts: list[str]) -> list[str]:
        cleaned_texts: list[str] = []

        for doc in self.nlp.pipe(texts, batch_size=64):
            lemmas: list[str] = []

            for token in doc:
                if token.is_stop or token.is_punct or token.is_space:
                    continue

                lemma = token.lemma_.strip().lower()
                if not lemma:
                    continue

                if not re.match(r"^[a-z0-9][a-z0-9\-\+_]*$", lemma):
                    continue

                lemmas.append(lemma)

            cleaned_texts.append(" ".join(lemmas))

        return cleaned_texts
