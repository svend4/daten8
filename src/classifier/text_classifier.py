"""
Text classification for categorizing ads.
"""

from typing import Dict, List, Optional, Tuple
import logging
import joblib
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class TextClassifier:
    """Classify ads into categories using TF-IDF and Naive Bayes."""

    def __init__(self, config: Dict):
        """
        Initialize classifier.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.model = None
        self.categories = config.get("categories", [])
        self.model_path = config.get("model_path", "data/models/classifier.pkl")
        self.min_confidence = config.get("min_confidence", 0.6)

        # Load model if exists
        if os.path.exists(self.model_path):
            self.load_model()

    def train(self, texts: List[str], labels: List[str]):
        """
        Train the classifier on labeled data.

        Args:
            texts: List of ad texts (title + description)
            labels: List of category labels
        """
        from sklearn.pipeline import Pipeline
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.model_selection import cross_val_score

        logger.info(f"Training classifier on {len(texts)} samples")

        # Create pipeline
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=self.config.get("max_features", 5000),
                ngram_range=tuple(self.config.get("ngram_range", [1, 2])),
                stop_words='german',  # or 'english' based on language
                min_df=2,  # Ignore terms that appear in fewer than 2 documents
                max_df=0.8,  # Ignore terms that appear in more than 80% of documents
            )),
            ('clf', MultinomialNB())
        ])

        # Train
        self.model.fit(texts, labels)

        # Evaluate
        scores = cross_val_score(self.model, texts, labels, cv=5)
        logger.info(f"Cross-validation accuracy: {scores.mean():.2f} (+/- {scores.std():.2f})")

        # Save model
        self.save_model()

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predict category for a single text.

        Args:
            text: Ad text (title + description)

        Returns:
            Tuple of (category, confidence)
        """
        if self.model is None:
            logger.warning("Model not loaded, cannot predict")
            return "other", 0.0

        try:
            # Predict
            prediction = self.model.predict([text])[0]

            # Get probability/confidence
            probabilities = self.model.predict_proba([text])[0]
            confidence = max(probabilities)

            # If confidence is too low, classify as "other"
            if confidence < self.min_confidence:
                logger.debug(f"Low confidence ({confidence:.2f}), classifying as 'other'")
                return "other", confidence

            return prediction, confidence

        except Exception as e:
            logger.error(f"Error predicting: {e}")
            return "other", 0.0

    def predict_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Predict categories for multiple texts.

        Args:
            texts: List of ad texts

        Returns:
            List of (category, confidence) tuples
        """
        if self.model is None:
            logger.warning("Model not loaded, cannot predict")
            return [("other", 0.0)] * len(texts)

        try:
            predictions = self.model.predict(texts)
            probabilities = self.model.predict_proba(texts)
            confidences = [max(probs) for probs in probabilities]

            results = []
            for pred, conf in zip(predictions, confidences):
                if conf < self.min_confidence:
                    results.append(("other", conf))
                else:
                    results.append((pred, conf))

            return results

        except Exception as e:
            logger.error(f"Error predicting batch: {e}")
            return [("other", 0.0)] * len(texts)

    def extract_features(self, ad_data: Dict) -> Dict:
        """
        Extract features from ad data.

        Args:
            ad_data: Ad dictionary with title and description

        Returns:
            Dictionary with extracted features
        """
        import re

        text = f"{ad_data.get('title', '')} {ad_data.get('description', '')}"

        features = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "has_images": len(ad_data.get("images", [])) > 0,
            "image_count": len(ad_data.get("images", [])),
        }

        # Extract condition keywords (German)
        condition_keywords = {
            "neu": "new",
            "neuwertig": "like_new",
            "gebraucht": "used",
            "defekt": "broken",
            "kaputt": "broken",
            "funktioniert": "working",
        }

        text_lower = text.lower()
        for keyword, condition in condition_keywords.items():
            if keyword in text_lower:
                features["condition"] = condition
                break
        else:
            features["condition"] = "unknown"

        # Extract brand/model (simplified)
        # This could be improved with NER
        brands = ["hp", "dell", "apple", "samsung", "sony", "ikea", "bosch", "siemens"]
        for brand in brands:
            if brand in text_lower:
                features["brand"] = brand.upper()
                break
        else:
            features["brand"] = None

        # Extract size/dimensions
        size_pattern = r"(\d+)\s*(?:x|×)\s*(\d+)(?:\s*(?:x|×)\s*(\d+))?\s*cm"
        size_match = re.search(size_pattern, text_lower)
        if size_match:
            features["dimensions"] = size_match.group(0)
        else:
            features["dimensions"] = None

        return features

    def classify_ad(self, ad_data: Dict) -> Dict:
        """
        Classify an ad and extract features.

        Args:
            ad_data: Ad dictionary

        Returns:
            Updated ad dictionary with category and features
        """
        # Combine title and description
        text = f"{ad_data.get('title', '')} {ad_data.get('description', '')}"

        # Predict category
        category, confidence = self.predict(text)

        # Extract features
        features = self.extract_features(ad_data)

        # Update ad data
        ad_data["category"] = category
        ad_data["category_confidence"] = confidence
        ad_data["features"] = features

        return ad_data

    def save_model(self):
        """Save trained model to disk."""
        if self.model is None:
            logger.warning("No model to save")
            return

        # Create directory if needed
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)

        # Save
        joblib.dump(self.model, self.model_path)
        logger.info(f"Model saved to {self.model_path}")

    def load_model(self):
        """Load trained model from disk."""
        try:
            self.model = joblib.load(self.model_path)
            logger.info(f"Model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self.model = None
