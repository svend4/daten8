"""
Crawler for eBay Kleinanzeigen (kleinanzeigen.de)
"""

from typing import Dict, List, Optional
import logging
from bs4 import BeautifulSoup
from datetime import datetime
import hashlib

from .base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class EbayCrawler(BaseCrawler):
    """Crawler for eBay Kleinanzeigen free items section."""

    def __init__(self, config: Dict):
        """Initialize eBay crawler with specific configuration."""
        super().__init__(config)
        self.selectors = config.get("selectors", {})
        self.search_config = config.get("search", {})

    def fetch_listings(self, max_pages: int = 10) -> List[Dict]:
        """
        Fetch listing pages from eBay Kleinanzeigen.

        Args:
            max_pages: Maximum number of pages to crawl

        Returns:
            List of ad data dictionaries
        """
        ads = []
        search_query = self.search_config.get("query", "")
        pagination_template = self.search_config.get("pagination", "")

        for page in range(1, max_pages + 1):
            # Construct URL
            if page == 1:
                url = f"{self.base_url}{search_query}"
            else:
                pagination = pagination_template.format(page=page)
                url = f"{self.base_url}{search_query}{pagination}"

            logger.info(f"Fetching listings page {page}: {url}")

            # Fetch page
            html = self._fetch_page(url)
            if not html:
                logger.warning(f"Failed to fetch page {page}, stopping")
                break

            # Parse listings
            page_ads = self._parse_listings_page(html)
            if not page_ads:
                logger.info(f"No ads found on page {page}, stopping")
                break

            ads.extend(page_ads)
            logger.info(f"Found {len(page_ads)} ads on page {page}")

            # Check if we should continue
            if len(page_ads) < 10:  # Heuristic: last page has fewer items
                logger.info("Reached last page")
                break

        return ads

    def _parse_listings_page(self, html: str) -> List[Dict]:
        """
        Parse a listings page and extract ad data.

        Args:
            html: HTML content of the listings page

        Returns:
            List of ad dictionaries
        """
        soup = BeautifulSoup(html, "lxml")
        ads = []

        # Find all ad containers
        container_selector = self.selectors.get("listing_container", "article.aditem")
        ad_elements = soup.select(container_selector)

        logger.debug(f"Found {len(ad_elements)} ad elements")

        for element in ad_elements:
            try:
                ad_data = self._extract_listing_data(element)
                if ad_data:
                    ads.append(ad_data)
            except Exception as e:
                logger.error(f"Error parsing ad element: {e}")

        return ads

    def _extract_listing_data(self, element) -> Optional[Dict]:
        """
        Extract data from a single listing element.

        Args:
            element: BeautifulSoup element

        Returns:
            Ad data dictionary or None
        """
        try:
            # Extract URL
            link_selector = self.selectors.get("listing_link", "a.ellipsis")
            link_element = element.select_one(link_selector)
            if not link_element:
                return None

            ad_url = link_element.get("href", "")
            if not ad_url.startswith("http"):
                ad_url = self.base_url + ad_url

            # Extract title
            title_selector = self.selectors.get("listing_title", "a.ellipsis")
            title_element = element.select_one(title_selector)
            title = title_element.get_text(strip=True) if title_element else "No title"

            # Extract location
            location_selector = self.selectors.get("listing_location", "div.aditem-main--top--left")
            location_element = element.select_one(location_selector)
            location_text = location_element.get_text(strip=True) if location_element else ""
            location = self._extract_location(location_text)

            # Extract date
            date_selector = self.selectors.get("listing_date", "div.aditem-main--top--right")
            date_element = element.select_one(date_selector)
            posted_date = self._parse_date(date_element.get_text(strip=True)) if date_element else None

            # Generate unique ID from URL
            ad_id = hashlib.md5(ad_url.encode()).hexdigest()

            ad_data = {
                "id": ad_id,
                "source": self.source_name,
                "url": ad_url,
                "title": title,
                "location": location,
                "posted_date": posted_date,
                "crawled_date": datetime.now(),
            }

            # Optionally fetch full details
            if self.config.get("fetch_details", True):
                details = self._fetch_ad_details(ad_url)
                if details:
                    ad_data.update(details)

            return ad_data

        except Exception as e:
            logger.error(f"Error extracting listing data: {e}")
            return None

    def _fetch_ad_details(self, url: str) -> Optional[Dict]:
        """
        Fetch and parse detailed ad page.

        Args:
            url: URL of the ad detail page

        Returns:
            Dictionary with additional ad details
        """
        html = self._fetch_page(url)
        if not html:
            return None

        return self.parse_ad(html, url)

    def parse_ad(self, html: str, url: str) -> Optional[Dict]:
        """
        Parse individual ad detail page.

        Args:
            html: HTML content of the ad page
            url: URL of the ad

        Returns:
            Dictionary with ad details
        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # Extract description
            desc_selector = self.selectors.get("detail_description", "p#viewad-description-text")
            desc_element = soup.select_one(desc_selector)
            description = desc_element.get_text(strip=True) if desc_element else ""

            # Extract images
            img_selector = self.selectors.get("detail_images", "div.galleryimage-element img")
            img_elements = soup.select(img_selector)
            images = [img.get("src") for img in img_elements if img.get("src")]

            # Extract detailed location
            location_selector = self.selectors.get("detail_location", "span#viewad-locality")
            location_element = soup.select_one(location_selector)
            location_text = location_element.get_text(strip=True) if location_element else ""

            return {
                "description": description,
                "images": images,
                "location_detail": location_text,
            }

        except Exception as e:
            logger.error(f"Error parsing ad detail: {e}")
            return None

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse German date formats from eBay Kleinanzeigen.

        Args:
            date_text: Date string (e.g., "Heute, 10:30", "Gestern", "28.12.2025")

        Returns:
            datetime object or None
        """
        try:
            from dateutil import parser
            import re

            # Handle relative dates
            now = datetime.now()

            if "heute" in date_text.lower():
                # Extract time if present
                time_match = re.search(r"(\d{2}):(\d{2})", date_text)
                if time_match:
                    hour, minute = map(int, time_match.groups())
                    return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                return now

            elif "gestern" in date_text.lower():
                from datetime import timedelta
                yesterday = now - timedelta(days=1)
                return yesterday

            else:
                # Try to parse as regular date
                return parser.parse(date_text, dayfirst=True, fuzzy=True)

        except Exception as e:
            logger.debug(f"Could not parse date '{date_text}': {e}")
            return None
