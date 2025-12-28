"""
Crawler module for collecting classified ads from various sources.
"""

from .base_crawler import BaseCrawler
from .ebay_crawler import EbayCrawler

__all__ = ["BaseCrawler", "EbayCrawler"]
