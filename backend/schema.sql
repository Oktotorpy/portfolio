-- Portfolio CMS Database Schema

PRAGMA foreign_keys = ON;

-- Contact (singleton)
CREATE TABLE IF NOT EXISTS contact (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    linkedin TEXT NOT NULL DEFAULT ''
);

INSERT INTO contact (id, name, email, linkedin) VALUES (1, '', '', '');

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
