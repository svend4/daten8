"""
Database manager for Classified Ads Indexer.
"""

import sqlite3
from typing import Dict, List, Optional
import logging
import json
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database operations for the classified ads system."""

    def __init__(self, config: Dict):
        """
        Initialize database manager.

        Args:
            config: Database configuration
        """
        self.config = config
        self.db_type = config.get("type", "sqlite")
        self.db_path = config.get("path", "data/ads.db")
        self.connection = None

        # Create database if it doesn't exist
        self._init_database()

    def _init_database(self):
        """Initialize database schema."""
        # Create directory if needed
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Connect and create schema
        self.connect()

        # Load schema
        schema_path = Path(__file__).parent / "schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema = f.read()
                self.connection.executescript(schema)
                self.connection.commit()
            logger.info("Database schema initialized")
        else:
            logger.warning(f"Schema file not found: {schema_path}")

    def connect(self):
        """Connect to database."""
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Return rows as dictionaries
            logger.debug(f"Connected to database: {self.db_path}")

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("Database connection closed")

    def insert_ad(self, ad_data: Dict) -> bool:
        """
        Insert a new ad into the database.

        Args:
            ad_data: Ad data dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()

            # Extract location data
            location = ad_data.get("location", {})

            # Serialize features as JSON
            features = json.dumps(ad_data.get("features", {}))

            cursor.execute("""
                INSERT OR REPLACE INTO ads (
                    id, source, url, title, description, category, category_confidence,
                    city, district, postal_code, latitude, longitude, location_raw,
                    posted_date, crawled_date, status, hash, features
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ad_data.get("id"),
                ad_data.get("source"),
                ad_data.get("url"),
                ad_data.get("title"),
                ad_data.get("description", ""),
                ad_data.get("category"),
                ad_data.get("category_confidence"),
                location.get("city"),
                location.get("district"),
                location.get("postal_code"),
                location.get("latitude"),
                location.get("longitude"),
                location.get("raw"),
                ad_data.get("posted_date"),
                ad_data.get("crawled_date", datetime.now()),
                ad_data.get("status", "active"),
                ad_data.get("hash"),
                features
            ))

            # Insert images if any
            if "images" in ad_data and ad_data["images"]:
                for image_url in ad_data["images"]:
                    cursor.execute("""
                        INSERT OR IGNORE INTO images (ad_id, url)
                        VALUES (?, ?)
                    """, (ad_data.get("id"), image_url))

            self.connection.commit()
            logger.debug(f"Inserted ad: {ad_data.get('id')}")
            return True

        except Exception as e:
            logger.error(f"Error inserting ad: {e}")
            self.connection.rollback()
            return False

    def get_ad(self, ad_id: str) -> Optional[Dict]:
        """
        Retrieve an ad by ID.

        Args:
            ad_id: Ad ID

        Returns:
            Ad dictionary or None
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM ads WHERE id = ?", (ad_id,))
            row = cursor.fetchone()

            if row:
                ad = dict(row)
                # Deserialize features
                if ad.get("features"):
                    ad["features"] = json.loads(ad["features"])

                # Get images
                cursor.execute("SELECT url FROM images WHERE ad_id = ?", (ad_id,))
                ad["images"] = [img[0] for img in cursor.fetchall()]

                return ad

            return None

        except Exception as e:
            logger.error(f"Error getting ad: {e}")
            return None

    def search_ads(self, filters: Dict, limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Search ads with filters.

        Args:
            filters: Search filters dictionary
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of ad dictionaries
        """
        try:
            query = "SELECT * FROM ads WHERE status = 'active'"
            params = []

            # Category filter
            if "categories" in filters and filters["categories"]:
                placeholders = ",".join(["?"] * len(filters["categories"]))
                query += f" AND category IN ({placeholders})"
                params.extend(filters["categories"])

            # City filter
            if "city" in filters:
                query += " AND city = ?"
                params.append(filters["city"])

            # District filter
            if "district" in filters:
                query += " AND district = ?"
                params.append(filters["district"])

            # Keyword search (full-text search)
            if "keywords" in filters and filters["keywords"]:
                query += " AND id IN (SELECT rowid FROM ads_fts WHERE ads_fts MATCH ?)"
                params.append(" OR ".join(filters["keywords"]))

            # Date range
            if "posted_after" in filters:
                query += " AND posted_date >= ?"
                params.append(filters["posted_after"])

            # Order by date
            query += " ORDER BY posted_date DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = self.connection.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            ads = []
            for row in rows:
                ad = dict(row)
                # Deserialize features
                if ad.get("features"):
                    ad["features"] = json.loads(ad["features"])
                ads.append(ad)

            return ads

        except Exception as e:
            logger.error(f"Error searching ads: {e}")
            return []

    def update_crawler_state(self, source: str, status: str, stats: Dict):
        """
        Update crawler state.

        Args:
            source: Crawler source name
            status: Status (idle, running, error)
            stats: Statistics dictionary
        """
        try:
            cursor = self.connection.cursor()

            # Update state
            cursor.execute("""
                INSERT OR REPLACE INTO crawler_state (
                    source, last_run_date, last_successful_run, status,
                    total_ads_collected, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                source,
                datetime.now(),
                datetime.now() if status == "completed" else None,
                status,
                stats.get("total_ads", 0),
                stats.get("error_message")
            ))

            # Log run
            cursor.execute("""
                INSERT INTO crawler_logs (
                    source, duration_seconds, ads_collected, new_ads, errors, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                source,
                (stats.get("end_time", datetime.now()) - stats.get("start_time", datetime.now())).total_seconds(),
                stats.get("total_ads", 0),
                stats.get("new_ads", 0),
                stats.get("errors", 0),
                status
            ))

            self.connection.commit()

        except Exception as e:
            logger.error(f"Error updating crawler state: {e}")
            self.connection.rollback()

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Statistics dictionary
        """
        try:
            cursor = self.connection.cursor()

            stats = {}

            # Total ads
            cursor.execute("SELECT COUNT(*) FROM ads WHERE status = 'active'")
            stats["total_ads"] = cursor.fetchone()[0]

            # Ads by category
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM ads
                WHERE status = 'active'
                GROUP BY category
                ORDER BY count DESC
            """)
            stats["by_category"] = dict(cursor.fetchall())

            # Ads by city
            cursor.execute("""
                SELECT city, COUNT(*) as count
                FROM ads
                WHERE status = 'active' AND city IS NOT NULL
                GROUP BY city
                ORDER BY count DESC
                LIMIT 10
            """)
            stats["top_cities"] = dict(cursor.fetchall())

            # Recent ads (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*)
                FROM ads
                WHERE status = 'active'
                  AND crawled_date >= datetime('now', '-1 day')
            """)
            stats["recent_24h"] = cursor.fetchone()[0]

            return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
