# Portfolio CMS — Knowledge Base

## Architecture

```
Frontend:  SvelteKit (SSR + client)  → port 3000
Backend:   Flask (REST API)          → port 8000
Database:  SQLite (WAL mode)
Proxy:     Caddy (HTTPS, reverse proxy)
```

Server paths:
- Code repo: `/opt/portfolio/repo`
- Backend deployed: `/opt/portfolio/backend`
- Frontend deployed: `/opt/portfolio/frontend`
- Uploads: `/opt/portfolio/uploads`
- Database: `/opt/portfolio/data/portfolio.db`
- Config: `/opt/portfolio/.env`

---

## Data Model

### Lookup Tables (editable in Settings)
| Table | Used By | Relation | Examples |
|-------|---------|----------|----------|
| `countries` | Job | Many-to-many via `job_countries` | Czechia, Ukraine, USA |
| `proficiencies` | Role | Many-to-many via `role_proficiencies` | Project management, Video editing, Graphic design |
| `skills` | Project | Many-to-many via `project_skills` | Video editing, Thumbnail creation, SEO |
| `tools` | Project | Many-to-many via `project_tools` | Claude, Premiere, Photoshop |
| `weights` | Project | Foreign key `weight_id` | Small, Medium, Big, Landmark, Continuous |
| `work_types` | Project | Many-to-many via `project_work_types` | Social media, TV, YouTube, Trailer, Graphics, Management |

All lookup tables have the same schema: `id INTEGER, name TEXT UNIQUE`.

### Main Entities

**Job** (`jobs` table)
| Field | Type | Notes |
|-------|------|-------|
| name | TEXT | Required |
| logo | TEXT | File path to uploaded image |
| website | TEXT | URL |
| description | TEXT | |
| date_start | DATE | |
| date_end | DATE | NULL = ongoing |
| color | TEXT | Hex color, default `#3a3d48`, used on timeline |
| countries | relation | via `job_countries` junction |

**Role** (`roles` table)
| Field | Type | Notes |
|-------|------|-------|
| name | TEXT | Required |
| job_id | FK → jobs | Required |
| department | TEXT | e.g. "Engineering", "Marketing" |
| description | TEXT | |
| accolades | TEXT | Awards, achievements |
| date_start | DATE | |
| date_end | DATE | NULL = ongoing |
| proficiencies | relation | via `role_proficiencies` junction |

**Project** (`projects` table)
| Field | Type | Notes |
|-------|------|-------|
| name | TEXT | Required |
| role_id | FK → roles | Required |
| description | TEXT | |
| date_of_creation | DATE | |
| link | TEXT | External URL |
| weight_id | FK → weights | NULL = no weight |
| media | relation | via `project_media` (ordered) |
| skills | relation | via `project_skills` |
| work_types | relation | via `project_work_types` |
| tools | relation | via `project_tools` |

**Project Media** (`project_media` table)
| Field | Type | Notes |
|-------|------|-------|
| project_id | FK → projects | |
| media_type | TEXT | `image`, `video`, or `youtube` |
| media_value | TEXT | File path or YouTube URL |
| sort_order | INTEGER | Display order |

---

## API Endpoints

### Auth
- `POST /api/auth/login` — `{username, password}`
- `POST /api/auth/logout`
- `GET /api/auth/me` — `{authenticated: bool}`

### Lookups
- `GET /api/lookups` — Returns all lookup tables: `{countries, proficiencies, skills, work_types, tools, weights}`
- `POST /api/lookups/<table>` — `{name}` → Create new entry (returns existing if duplicate)
- `PUT /api/lookups/<table>/<id>` — `{name}` → Rename
- `DELETE /api/lookups/<table>/<id>` — Delete (fails if in use)

### Jobs
- `GET /api/jobs` — List all
- `GET /api/jobs/<id>`
- `POST /api/jobs` — `{name, website?, description?, date_start?, date_end?, color?, country_ids?}`
- `PUT /api/jobs/<id>` — Same fields
- `DELETE /api/jobs/<id>` — Cascades to roles → projects
- `PUT /api/jobs/<id>/logo` — `{logo: "/uploads/filename"}`

### Roles
- `GET /api/roles?job_id=N` — List, optionally filtered
- `GET /api/roles/<id>`
- `POST /api/roles` — `{name, job_id, department?, description?, accolades?, date_start?, date_end?, proficiency_ids?}`
- `PUT /api/roles/<id>` — Same fields
- `DELETE /api/roles/<id>` — Cascades to projects

### Projects
- `GET /api/projects?role_id=N` — List, optionally filtered
- `GET /api/projects/<id>`
- `POST /api/projects` — `{name, role_id, description?, date_of_creation?, link?, weight_id?, skill_ids?, work_type_ids?, tool_ids?, media?}`
- `PUT /api/projects/<id>` — Same fields
- `DELETE /api/projects/<id>`

The `media` field is an array: `[{media_type: "image"|"video"|"youtube", media_value: "/uploads/..." or "https://youtube..."}]`

### Uploads
- `GET /api/uploads` — List all files with metadata (type, size, path)
- `POST /api/uploads` — FormData with `file` field → `{path, filename, type}`
- `DELETE /api/uploads/<filename>` — Delete file

---

## Frontend Routes

### Public
| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `+page.svelte` | Timeline (horizontal, year-based rows) |
| `/<slug>` | `[slug=notadmin]/+page.svelte` | Work type page (project cards) |

### Admin (all gated by auth)
| Route | Description |
|-------|-------------|
| `/admin` | Redirects to `/admin/contact` |
| `/admin/contact` | Edit name, email, LinkedIn |
| `/admin/jobs` | CRUD jobs with color picker |
| `/admin/roles` | CRUD roles with department, proficiencies |
| `/admin/projects` | CRUD projects with multi-media, tools, weight |
| `/admin/files` | Upload/delete files (images + videos tabs) |
| `/admin/settings` | Edit all lookup tables |

---

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `PublicShell` | `$lib/components/PublicShell.svelte` | Sidebar + nav wrapper for public pages |
| `Sidebar` | `$lib/components/Sidebar.svelte` | Contact info + active role display |
| `ProjectCard` | `$lib/components/ProjectCard.svelte` | Project display with mosaic images, video arrows, tools tags |
| `Lightbox` | `$lib/components/Lightbox.svelte` | Fullscreen image viewer with arrow navigation |
| `MultiSelect` | `$lib/components/MultiSelect.svelte` | Tag selector with inline "create new" |
| `MediaManager` | `$lib/components/MediaManager.svelte` | Multi-media editor with upload + server file picker |
| `Modal` | `$lib/components/Modal.svelte` | Generic modal wrapper |
| `FileUpload` | `$lib/components/FileUpload.svelte` | Single file upload (used for job logos) |

---

## Frontend Display Logic

### Timeline (`/`)
- Rows = year (desktop) or quarter (mobile)
- Job starts: vertical tick + name + country below timeline
- Role starts: square marker on timeline, name above, click → popup with department, proficiencies, accolades
- Project dots: on timeline by date, click → popup with first media, tools, skills
- Solid line where jobs active, dashed where no coverage
- Sidebar shows role corresponding to visible scroll position

### Project Cards (`/<slug>`)
- 2-column layout: media left, info right
- **Images**: Single → full display, clickable to lightbox. Multiple → 2×2 mosaic grid, each clickable
- **Videos**: Show active video with player controls. Multiple → arrow buttons to switch
- **YouTube**: Embedded in iframe with same arrow navigation as video
- Tags shown at bottom: skills (gray) and tools (purple/blue tint)
- Copy link button generates `/<work-type-slug>#project-<id>`

### Role Display (sidebar, popups)
- Name, company, department, date range, description, proficiencies (tags), accolades

---

## CSS Theme (Dark)
```
--bg: #0f1117          (page background)
--bg-card: #1a1d27     (card/panel)
--bg-input: #242735    (input fields)
--border: #2e3140      (borders)
--accent: #5b6abf      (primary actions)
--text: #e1e3ea        (body text)
--text-dim: #8b8fa3    (secondary text)
--danger: #d94f4f      (delete actions)
```

---

## Deployment Workflow
```bash
# Local: edit, commit, push
git add . && git commit -m "message" && git push

# Server: pull, build, restart
ssh root@SERVER "/opt/portfolio/deploy.sh pull"
```

The `deploy.sh pull` command: git pull → rsync backend/frontend → pip install → npm ci → npm build → restart services.

Database migrations run automatically on backend startup via `database.py _migrate()`.
