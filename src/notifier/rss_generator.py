"""
RSS/Atom feed generator for classified ads.
"""

from typing import Dict, List
import logging
from pathlib import Path
from datetime import datetime
from feedgen.feed import FeedGenerator

logger = logging.getLogger(__name__)


class RSSGenerator:
    """Generate RSS/Atom feeds for ads."""

    def __init__(self, config: Dict):
        """
        Initialize RSS generator.

        Args:
            config: RSS configuration
        """
        self.config = config
        self.output_dir = Path(config.get("output_directory", "data/rss"))
        self.base_url = config.get("base_url", "https://yourserver.com/rss/")
        self.max_items = config.get("max_items_per_feed", 100)

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_feed(self, ads: List[Dict], title: str, description: str,
                     filename: str, link: str = None) -> str:
        """
        Generate RSS feed from ads.

        Args:
            ads: List of ad dictionaries
            title: Feed title
            description: Feed description
            filename: Output filename (without path)
            link: Feed link URL

        Returns:
            Path to generated RSS file
        """
        try:
            # Create feed
            fg = FeedGenerator()
            fg.title(title)
            fg.link(href=link or self.base_url, rel='alternate')
            fg.description(description)
            fg.language('de')  # German
            fg.updated(datetime.now())

            # Add items
            for ad in ads[:self.max_items]:
                fe = fg.add_entry()
                fe.id(ad.get("url", ad.get("id")))
                fe.title(ad.get("title", "No title"))
                fe.link(href=ad.get("url", ""))
                fe.description(self._format_description(ad))

                # Published date
                if ad.get("posted_date"):
                    if isinstance(ad["posted_date"], str):
                        from dateutil import parser
                        posted_date = parser.parse(ad["posted_date"])
                    else:
                        posted_date = ad["posted_date"]
                    fe.published(posted_date)

                # Category
                if ad.get("category"):
                    fe.category(term=ad["category"])

                # Geolocation
                if ad.get("location"):
                    location = ad["location"]
                    if isinstance(location, dict):
                        if location.get("latitude") and location.get("longitude"):
                            fg.load_extension('geo', rss=True, atom=True)
                            fe.geo.lat(str(location["latitude"]))
                            fe.geo.long(str(location["longitude"]))

            # Save feed
            output_path = self.output_dir / filename
            fg.rss_file(str(output_path), pretty=True)

            logger.info(f"Generated RSS feed: {output_path} ({len(ads)} items)")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error generating RSS feed: {e}")
            return None

    def _format_description(self, ad: Dict) -> str:
        """
        Format ad description for RSS.

        Args:
            ad: Ad dictionary

        Returns:
            Formatted HTML description
        """
        description = ad.get("description", "No description available")
        location = ad.get("location", {})

        # Build HTML description
        html_parts = []

        # Category
        if ad.get("category"):
            html_parts.append(f"<p><strong>Kategorie:</strong> {ad['category']}</p>")

        # Location
        if isinstance(location, dict):
            location_str = ", ".join(filter(None, [
                location.get("city"),
                location.get("district"),
                location.get("postal_code")
            ]))
            if location_str:
                html_parts.append(f"<p><strong>Standort:</strong> {location_str}</p>")
        elif isinstance(location, str):
            html_parts.append(f"<p><strong>Standort:</strong> {location}</p>")

        # Description
        html_parts.append(f"<p>{description}</p>")

        # Features
        if ad.get("features"):
            features = ad["features"]
            if isinstance(features, dict):
                if features.get("condition"):
                    html_parts.append(f"<p><strong>Zustand:</strong> {features['condition']}</p>")
                if features.get("brand"):
                    html_parts.append(f"<p><strong>Marke:</strong> {features['brand']}</p>")

        # Images
        if ad.get("images") and len(ad["images"]) > 0:
            html_parts.append(f"<p><strong>Bilder:</strong> {len(ad['images'])}</p>")
            # Include first image
            html_parts.append(f'<img src="{ad["images"][0]}" alt="Ad image" style="max-width: 300px;"/>')

        return "\n".join(html_parts)

    def generate_category_feeds(self, db_manager, categories: List[str]):
        """
        Generate RSS feeds for each category.

        Args:
            db_manager: Database manager instance
            categories: List of category names
        """
        for category in categories:
            # Get ads for category
            ads = db_manager.search_ads({"categories": [category]}, limit=self.max_items)

            if ads:
                self.generate_feed(
                    ads=ads,
                    title=f"Kostenlose Anzeigen - {category}",
                    description=f"Kostenlose Artikel in der Kategorie {category}",
                    filename=f"{category}.xml",
                    link=f"{self.base_url}{category}.xml"
                )

    def generate_city_feeds(self, db_manager, cities: List[str]):
        """
        Generate RSS feeds for each city.

        Args:
            db_manager: Database manager instance
            cities: List of city names
        """
        for city in cities:
            # Get ads for city
            ads = db_manager.search_ads({"city": city}, limit=self.max_items)

            if ads:
                self.generate_feed(
                    ads=ads,
                    title=f"Kostenlose Anzeigen - {city}",
                    description=f"Kostenlose Artikel in {city}",
                    filename=f"{city.lower().replace(' ', '_')}.xml",
                    link=f"{self.base_url}{city}.xml"
                )

    def generate_all_feeds(self, db_manager):
        """
        Generate all RSS feeds.

        Args:
            db_manager: Database manager instance
        """
        # Generate general feed
        ads = db_manager.search_ads({}, limit=self.max_items)
        self.generate_feed(
            ads=ads,
            title="Kostenlose Anzeigen - Alle",
            description="Alle kostenlosen Artikel",
            filename="all.xml",
            link=f"{self.base_url}all.xml"
        )

        # Generate category feeds
        categories = self.config.get("categories", [])
        if categories:
            self.generate_category_feeds(db_manager, categories)

        logger.info("All RSS feeds generated successfully")
