"""
Base crawler class for all classified ads sources.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import time
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base class for all crawlers."""

    def __init__(self, config: Dict):
        """
        Initialize the crawler with configuration.

        Args:
            config: Configuration dictionary for the crawler
        """
        self.config = config
        self.source_name = config.get("name", "unknown")
        self.base_url = config.get("base_url", "")
        self.enabled = config.get("enabled", True)

        # HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.get("user_agent", "ClassifiedAdsIndexer/1.0")
        })

        # Rate limiting
        self.delay_between_requests = config.get("delay_between_requests", 2)
        self.last_request_time = 0

        # Statistics
        self.stats = {
            "total_ads": 0,
            "new_ads": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

    def _rate_limit(self):
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self.delay_between_requests:
            sleep_time = self.delay_between_requests - time_since_last_request
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _fetch_page(self, url: str, retries: int = 3) -> Optional[str]:
        """
        Fetch a web page with retry logic.

        Args:
            url: URL to fetch
            retries: Number of retry attempts

        Returns:
            HTML content or None if failed
        """
        self._rate_limit()

        for attempt in range(retries):
            try:
                logger.debug(f"Fetching {url} (attempt {attempt + 1}/{retries})")
                response = self.session.get(
                    url,
                    timeout=self.config.get("timeout", 30)
                )
                response.raise_for_status()
                return response.text

            except requests.RequestException as e:
                logger.warning(f"Error fetching {url}: {e}")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    self.stats["errors"] += 1
                    return None

    @abstractmethod
    def fetch_listings(self, max_pages: int = 10) -> List[Dict]:
        """
        Fetch listing pages and extract ad URLs.

        Args:
            max_pages: Maximum number of pages to crawl

        Returns:
            List of ad data dictionaries
        """
        pass

    @abstractmethod
    def parse_ad(self, html: str, url: str) -> Optional[Dict]:
        """
        Parse individual ad page.

        Args:
            html: HTML content of the ad page
            url: URL of the ad

        Returns:
            Dictionary with ad data or None if parsing failed
        """
        pass

    def _extract_location(self, location_text: str) -> Dict:
        """
        Extract city, district, and postal code from location text.

        Args:
            location_text: Raw location string

        Returns:
            Dictionary with location components
        """
        # Basic implementation - can be overridden in subclasses
        parts = location_text.split(",")

        location = {
            "city": None,
            "district": None,
            "postal_code": None,
            "raw": location_text.strip()
        }

        if len(parts) >= 1:
            # Try to extract postal code
            import re
            postal_match = re.search(r"\b\d{5}\b", parts[0])
            if postal_match:
                location["postal_code"] = postal_match.group()

            # Extract city name
            city_match = re.sub(r"\d{5}", "", parts[0]).strip()
            if city_match:
                location["city"] = city_match

        if len(parts) >= 2:
            location["district"] = parts[1].strip()

        return location

    def run(self, max_pages: int = 10) -> Dict:
        """
        Run the crawler and collect ads.

        Args:
            max_pages: Maximum number of listing pages to crawl

        Returns:
            Statistics dictionary
        """
        if not self.enabled:
            logger.info(f"Crawler {self.source_name} is disabled")
            return self.stats

        logger.info(f"Starting crawler for {self.source_name}")
        self.stats["start_time"] = datetime.now()

        try:
            # Fetch listings
            ads = self.fetch_listings(max_pages)
            self.stats["total_ads"] = len(ads)

            logger.info(f"Collected {len(ads)} ads from {self.source_name}")

            # Process each ad
            for ad_data in ads:
                try:
                    # This will be handled by the database module
                    # For now, just count
                    self.stats["new_ads"] += 1

                except Exception as e:
                    logger.error(f"Error processing ad: {e}")
                    self.stats["errors"] += 1

        except Exception as e:
            logger.error(f"Crawler error: {e}")
            self.stats["errors"] += 1

        finally:
            self.stats["end_time"] = datetime.now()
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            logger.info(f"Crawler finished in {duration:.2f}s")
            logger.info(f"Stats: {self.stats}")

        return self.stats

    def close(self):
        """Clean up resources."""
        self.session.close()
