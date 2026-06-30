-- Portfolio CMS Database Schema

PRAGMA foreign_keys = ON;

-- Contact (singleton)
CREATE TABLE IF NOT EXISTS contact (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    linkedin TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT ''
);

INSERT INTO contact (id, name, email, linkedin, description) VALUES (1, '', '', '', '');

-- Lookup tables
CREATE TABLE IF NOT EXISTS countries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS proficiencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS work_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS tools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS weights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

-- Seed lookup data
INSERT INTO countries (name) VALUES ('Czechia'), ('Ukraine'), ('USA');

INSERT INTO proficiencies (name) VALUES
    ('Project management'),
    ('Video editing'),
    ('Graphic design'),
    ('Product management'),
    ('Team work'),
    ('Strategy'),
    ('Automation');

INSERT INTO skills (name) VALUES
    ('Video editing'),
    ('Thumbnail creation'),
    ('Team management'),
    ('Social media work'),
    ('SEO');

INSERT INTO work_types (name) VALUES
    ('Social media'),
    ('TV'),
    ('YouTube'),
    ('Trailer'),
    ('Graphics'),
    ('Management');

INSERT INTO tools (name) VALUES
    ('Claude'),
    ('Premiere'),
    ('Photoshop');

INSERT INTO weights (name) VALUES
    ('Small'),
    ('Medium'),
    ('Big'),
    ('Landmark'),
    ('Continuous');

-- Jobs
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    logo TEXT DEFAULT NULL,
    website TEXT DEFAULT NULL,
    description TEXT DEFAULT '',
    date_start DATE DEFAULT NULL,
    date_end DATE DEFAULT NULL,
    color TEXT DEFAULT '#3a3d48',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_countries (
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    country_id INTEGER NOT NULL REFERENCES countries(id) ON DELETE CASCADE,
    PRIMARY KEY (job_id, country_id)
);

-- Roles
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    department TEXT DEFAULT '',
    description TEXT DEFAULT '',
    accolades TEXT DEFAULT '',
    date_start DATE DEFAULT NULL,
    date_end DATE DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS role_proficiencies (
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    proficiency_id INTEGER NOT NULL REFERENCES proficiencies(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, proficiency_id)
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    description TEXT DEFAULT '',
    date_of_creation DATE DEFAULT NULL,
    link TEXT DEFAULT NULL,
    weight_id INTEGER DEFAULT NULL REFERENCES weights(id) ON DELETE SET NULL,
    -- Legacy single-content columns (kept for migration, use project_media instead)
    content_type TEXT DEFAULT NULL CHECK (content_type IN ('image', 'video', 'youtube')),
    content_value TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video', 'youtube')),
    media_value TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS project_skills (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, skill_id)
);

CREATE TABLE IF NOT EXISTS project_work_types (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    work_type_id INTEGER NOT NULL REFERENCES work_types(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, work_type_id)
);

CREATE TABLE IF NOT EXISTS project_tools (
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    tool_id INTEGER NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    PRIMARY KEY (project_id, tool_id)
);

-- Election snapshots (history of polled election results)
CREATE TABLE IF NOT EXISTS election_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fetched_at   TEXT NOT NULL,                -- UTC ISO8601, when we stored it
    source       TEXT NOT NULL DEFAULT 'api',  -- 'api' | 'placeholder' | 'manual'
    payload      TEXT NOT NULL,                -- canonical JSON array of parties
    content_hash TEXT NOT NULL,                -- sha256 of payload, for change-detection
    http_status  INTEGER                       -- upstream HTTP status, nullable
);
CREATE INDEX IF NOT EXISTS idx_election_snapshots_fetched_at
    ON election_snapshots (fetched_at DESC);

-- Election data-source config (singleton id=1), editable from the admin CMS
CREATE TABLE IF NOT EXISTS election_config (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    source_mode TEXT    NOT NULL DEFAULT 'manual',  -- 'manual' | 'api'
    api_url     TEXT    NOT NULL DEFAULT '',
    api_proxy   TEXT    NOT NULL DEFAULT '',         -- SOCKS/HTTP proxy (Armenia egress)
    api_headers TEXT    NOT NULL DEFAULT '',         -- JSON object string, e.g. auth header
    api_timeout INTEGER NOT NULL DEFAULT 30,
    updated_at  TEXT
);
INSERT OR IGNORE INTO election_config (id, source_mode) VALUES (1, 'manual');

-- ============================================================
-- CineVote: group movie-night voting (vitz.pro/cinevote)
-- ============================================================
CREATE TABLE IF NOT EXISTS cinevote_users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cinevote_sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES cinevote_users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cinevote_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL DEFAULT '',
    event_date     TEXT NOT NULL,                    -- ISO date of the movie night
    status         TEXT NOT NULL DEFAULT 'picking',  -- picking | voting | runoff | concluded
    winner_pick_id INTEGER,                          -- set when concluded
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cinevote_picks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   INTEGER NOT NULL REFERENCES cinevote_events(id) ON DELETE CASCADE,
    user_id    INTEGER NOT NULL REFERENCES cinevote_users(id) ON DELETE CASCADE,
    tmdb_id    INTEGER NOT NULL,
    imdb_id    TEXT,                                 -- for imdb.com click-through
    title      TEXT NOT NULL,
    year       TEXT,
    poster_url TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(event_id, user_id),                       -- one pick per user per event
    UNIQUE(event_id, tmdb_id)                        -- a movie only once per event
);

CREATE TABLE IF NOT EXISTS cinevote_watched (
    user_id INTEGER NOT NULL REFERENCES cinevote_users(id) ON DELETE CASCADE,
    pick_id INTEGER NOT NULL REFERENCES cinevote_picks(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, pick_id)
);

CREATE TABLE IF NOT EXISTS cinevote_votes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   INTEGER NOT NULL REFERENCES cinevote_events(id) ON DELETE CASCADE,
    voter_id   INTEGER NOT NULL REFERENCES cinevote_users(id) ON DELETE CASCADE,
    pick_id    INTEGER NOT NULL REFERENCES cinevote_picks(id) ON DELETE CASCADE,
    points     INTEGER NOT NULL,                     -- 1 (seen) or 2 (unseen), frozen at cast
    round      INTEGER NOT NULL DEFAULT 1,           -- 1 = main (up to 2 votes), 2 = runoff (1 vote)
    created_at TEXT NOT NULL,
    UNIQUE(event_id, voter_id, pick_id, round)       -- distinct picks; up to 2/voter in round 1
);
