-- Database schema for Classified Ads Indexer
-- SQLite version

-- Main ads table
CREATE TABLE IF NOT EXISTS ads (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    category_confidence REAL,

    -- Location
    city TEXT,
    district TEXT,
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    location_raw TEXT,

    -- Dates
    posted_date DATETIME,
    crawled_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Status
    status TEXT DEFAULT 'active',  -- active, expired, deleted
    hash TEXT,  -- For deduplication

    -- Features (JSON or separate columns)
    features TEXT,  -- JSON string

    -- Raw data for reprocessing
    raw_html TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_ads_city ON ads(city);
CREATE INDEX IF NOT EXISTS idx_ads_category ON ads(category);
CREATE INDEX IF NOT EXISTS idx_ads_posted_date ON ads(posted_date DESC);
CREATE INDEX IF NOT EXISTS idx_ads_status ON ads(status);
CREATE INDEX IF NOT EXISTS idx_ads_location ON ads(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_ads_hash ON ads(hash);

-- Full-text search index (SQLite FTS5)
CREATE VIRTUAL TABLE IF NOT EXISTS ads_fts USING fts5(
    title,
    description,
    content=ads,
    content_rowid=rowid
);

-- Trigger to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS ads_fts_insert AFTER INSERT ON ads BEGIN
    INSERT INTO ads_fts(rowid, title, description)
    VALUES (new.rowid, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS ads_fts_update AFTER UPDATE ON ads BEGIN
    UPDATE ads_fts SET title = new.title, description = new.description
    WHERE rowid = new.rowid;
END;

CREATE TRIGGER IF NOT EXISTS ads_fts_delete AFTER DELETE ON ads BEGIN
    DELETE FROM ads_fts WHERE rowid = old.rowid;
END;

-- Images table
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id TEXT NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    local_path TEXT,
    downloaded BOOLEAN DEFAULT 0,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ad_id, url)
);

CREATE INDEX IF NOT EXISTS idx_images_ad_id ON images(ad_id);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    parent_id INTEGER REFERENCES categories(id),
    description TEXT,
    keywords TEXT  -- JSON array of keywords
);

-- Insert default categories
INSERT OR IGNORE INTO categories (name, description) VALUES
    ('computers', 'Computers and electronics'),
    ('furniture', 'Furniture and home decor'),
    ('clothing', 'Clothing and accessories'),
    ('books', 'Books and media'),
    ('sports', 'Sports and hobbies'),
    ('kids', 'Kids items and toys'),
    ('appliances', 'Home appliances'),
    ('construction', 'Tools and construction'),
    ('garden', 'Garden and plants'),
    ('other', 'Other items');

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    enabled BOOLEAN DEFAULT 1,

    -- Filters (stored as JSON for flexibility)
    filters TEXT NOT NULL,  -- JSON: {categories, location, keywords, etc.}

    -- Notification settings
    notification_type TEXT DEFAULT 'email',  -- email or rss
    notification_frequency TEXT DEFAULT 'daily',  -- immediate, daily, weekly
    notification_time TEXT,  -- HH:MM format
    max_ads_per_notification INTEGER DEFAULT 20,

    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_email ON subscriptions(email);
CREATE INDEX IF NOT EXISTS idx_subscriptions_enabled ON subscriptions(enabled);

-- Notifications log table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id TEXT NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    ad_id TEXT NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
    sent_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'sent',  -- sent, failed, pending
    error_message TEXT,
    UNIQUE(subscription_id, ad_id)  -- Prevent duplicate notifications
);

CREATE INDEX IF NOT EXISTS idx_notifications_subscription ON notifications(subscription_id);
CREATE INDEX IF NOT EXISTS idx_notifications_ad ON notifications(ad_id);
CREATE INDEX IF NOT EXISTS idx_notifications_sent_date ON notifications(sent_date DESC);

-- Crawler state table (for tracking progress)
CREATE TABLE IF NOT EXISTS crawler_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    last_run_date DATETIME,
    last_successful_run DATETIME,
    last_page_crawled INTEGER DEFAULT 0,
    total_ads_collected INTEGER DEFAULT 0,
    status TEXT DEFAULT 'idle',  -- idle, running, error
    error_message TEXT,
    UNIQUE(source)
);

-- Crawler logs table
CREATE TABLE IF NOT EXISTS crawler_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    run_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    duration_seconds REAL,
    ads_collected INTEGER DEFAULT 0,
    new_ads INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed',
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_crawler_logs_source ON crawler_logs(source);
CREATE INDEX IF NOT EXISTS idx_crawler_logs_run_date ON crawler_logs(run_date DESC);

-- Clusters table (for ad clustering)
CREATE TABLE IF NOT EXISTS clusters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    description TEXT,
    centroid TEXT,  -- JSON representation of cluster centroid
    ad_count INTEGER DEFAULT 0,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Ad-Cluster mapping
CREATE TABLE IF NOT EXISTS ad_clusters (
    ad_id TEXT NOT NULL REFERENCES ads(id) ON DELETE CASCADE,
    cluster_id INTEGER NOT NULL REFERENCES clusters(id) ON DELETE CASCADE,
    distance REAL,  -- Distance from cluster centroid
    PRIMARY KEY (ad_id, cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_ad_clusters_cluster ON ad_clusters(cluster_id);

-- Views for common queries

-- Active ads view
CREATE VIEW IF NOT EXISTS active_ads AS
SELECT * FROM ads
WHERE status = 'active'
ORDER BY posted_date DESC;

-- Ads with location view
CREATE VIEW IF NOT EXISTS ads_with_location AS
SELECT * FROM ads
WHERE city IS NOT NULL AND city != ''
ORDER BY posted_date DESC;

-- Recent ads view (last 7 days)
CREATE VIEW IF NOT EXISTS recent_ads AS
SELECT * FROM ads
WHERE status = 'active'
  AND posted_date >= datetime('now', '-7 days')
ORDER BY posted_date DESC;
