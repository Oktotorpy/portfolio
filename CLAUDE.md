# Portfolio CMS

Personal portfolio website with a self-hosted CMS. Dark-themed, timeline-based design showing career progression (Jobs → Roles → Projects).

## Tech Stack

- **Backend**: Python Flask + SQLite, served via Gunicorn
- **Frontend**: SvelteKit (Svelte 4 syntax with some Svelte 5 compilation), Node.js adapter
- **Reverse proxy**: Caddy (auto-HTTPS)
- **Server**: Ubuntu 24.04 VPS at `/opt/portfolio/`
- **Deployment**: GitHub → `deploy.sh pull` on server

## Repo Structure

```
portfolio/
├── backend/
│   ├── main.py              # Flask app factory, CORS, static files
│   ├── database.py          # SQLite connection, init_db(), auto-migrations
│   ├── schema.sql           # Full DDL + seed data
│   ├── auth.py              # Session-based auth, require_auth decorator
│   ├── requirements.txt     # flask, gunicorn
│   └── routes/
│       ├── jobs.py          # CRUD + countries junction
│       ├── roles.py         # CRUD + proficiencies junction
│       ├── projects.py      # CRUD + skills/work_types/tools junctions + multi-media
│       ├── lookups.py       # countries, proficiencies, skills, work_types, tools, weights
│       ├── uploads.py       # File upload/delete/list
│       └── contact.py       # Singleton contact record
├── frontend/
│   ├── package.json
│   ├── svelte.config.js     # Node adapter
│   ├── vite.config.js
│   └── src/
│       ├── app.css           # Global dark theme CSS variables
│       ├── params/
│       │   └── notadmin.js   # Param matcher: blocks [slug] from matching "admin"
│       ├── lib/
│       │   ├── api.js        # fetch wrapper for admin API calls
│       │   ├── stores.js     # currentRoleId writable store
│       │   ├── utils.js      # formatDate, formatDateRange helpers
│       │   ├── data.server.js # Shared SSR data fetcher for public pages
│       │   └── components/
│       │       ├── PublicShell.svelte   # Public site shell (sidebar + nav + mobile header)
│       │       ├── Sidebar.svelte      # Role display, job logo, accolades, colored divider
│       │       ├── ProjectCard.svelte  # Media presentation (mosaic, click-to-play, shorts)
│       │       ├── Lightbox.svelte     # Fullscreen image viewer
│       │       ├── MultiSelect.svelte  # Tag picker with inline creation
│       │       └── MediaManager.svelte # Multi-media CRUD for admin
│       └── routes/
│           ├── +layout.svelte          # Neutral: just CSS + <slot/>
│           ├── +page.svelte            # Timeline (public homepage)
│           ├── +page.server.js         # SSR data for timeline
│           ├── [slug=notadmin]/
│           │   ├── +page.svelte        # Work type pages (e.g. /youtube)
│           │   └── +page.server.js
│           └── admin/
│               ├── +layout.svelte      # Admin chrome, auth gate, sidebar nav
│               ├── +layout.server.js   # Server-side auth check
│               ├── +page.server.js     # Redirects /admin → /admin/contact
│               ├── contact/+page.svelte
│               ├── jobs/+page.svelte
│               ├── roles/+page.svelte
│               ├── projects/+page.svelte
│               ├── settings/+page.svelte  # Tools, weights, work types, skills, proficiencies
│               └── files/+page.svelte     # Upload manager
└── deploy/
    ├── deploy.sh              # setup, git-init, pull, restart, status, logs, stop
    ├── Caddyfile              # Reverse proxy template (envsubst)
    ├── portfolio-backend.service
    ├── portfolio-frontend.service
    ├── backup.sh
    └── generate_hash.py       # bcrypt password hash generator
```

## Data Model

Hierarchy: **Job → Role(s) → Project(s)**

### Core Tables
- `jobs` — company/org (name, logo, color, website, description, date_start, date_end)
- `roles` — position within a job (name, job_id FK, department, description, accolades, date_start, date_end)
- `projects` — work done within a role (name, role_id FK, description, date_of_creation, link, weight_id FK, content_type, content_value)
- `contact` — singleton (id=1), name, email, linkedin

### Lookup Tables
- `countries`, `proficiencies`, `skills`, `work_types`, `tools`, `weights`

### Junction Tables
- `job_countries`, `role_proficiencies`, `project_skills`, `project_work_types`, `project_tools`

### Multi-Media
- `project_media` — (project_id, media_type ['image'|'video'|'youtube'], media_value, sort_order)
- Legacy: `projects.content_type` + `projects.content_value` (single media, still supported)

### Weights
Projects have a `weight_id` linking to `weights` table. Standard weights: Small, Medium, Big, Landmark, Continuous. These affect timeline dot sizes and icons.

## Key Architectural Decisions

### Svelte Version
The project uses **SvelteKit with Svelte 4 syntax** (`$:` reactives, `export let`, `on:click`). However, the Svelte compiler is version 5, which means:
- `{@const}` can ONLY appear inside `{#if}`, `{#each}`, `{:else}`, `{:then}`, `{:catch}`, `<Component>`, or `<svelte:fragment>` — NOT inside `<div>` or other HTML elements
- When you need `{@const}` inside a block, wrap in `{#each [item] as item}` to create a valid scope

### Route Architecture
- Public pages wrap themselves in `<PublicShell>` component (NOT a layout)
- Root `+layout.svelte` is neutral (just CSS + slot) — does NOT fetch data
- Each public page has its own `+page.server.js` using shared `data.server.js`
- `[slug=notadmin]` param matcher prevents dynamic route from catching `/admin`
- Admin has completely separate layout with auth gating

### Database Migrations
- `database.py` has `run_migrations()` that runs on every app start
- Migrations use `PRAGMA table_info()` to check if columns exist before adding
- New tables use `CREATE TABLE IF NOT EXISTS`
- Safe to add migrations — they're idempotent

### Authentication
- Single-user, session-based (bcrypt password hash in `.env`)
- Gunicorn must use `--preload` flag to share session state across workers
- `require_auth` decorator on all admin API routes

## Server Deployment

```
/opt/portfolio/
├── repo/          # git clone (read-only)
├── backend/       # deployed Flask app (rsynced from repo)
├── frontend/      # deployed SvelteKit (rsynced + built)
├── uploads/       # user-uploaded media (NOT in git)
├── data/          # portfolio.db (NOT in git)
├── venv/          # Python virtualenv
├── .env           # server config (NOT in git)
└── deploy.sh      # deployment script
```

**Deploy workflow:**
```bash
# Local
git add . && git commit -m "changes" && git push

# Server
ssh root@SERVER "/opt/portfolio/deploy.sh pull"
```

The `pull` command: fetches git → rsyncs backend/frontend → npm install → npm run build → restarts systemd services.

## Timeline (Public Homepage)

The timeline is a horizontal layout showing career progression right-to-left (newest at top-left).

### Visual Elements
- **Horizontal line**: 4px tall, colored per job's `color` field. Overlapping jobs stack vertically (older job bottom, newer top)
- **Job markers**: Vertical 2px tick connecting line down to job name + country
- **Role markers**: Diamond ◆ icon (medium size), with role name + underline above. Tags: "New role" (dark green) for first role in a job, "Promotion" (gold) for subsequent roles
- **Project dots**: Size based on weight — Small (8px), Medium (12px), Big (16px), Landmark (★ star with gold glow, 22px), Continuous (∞ in a square box, 22px)
- **"Currently" markers**: Roles without `date_end` get a "Currently" tag (blue) in the most recent row, stacked vertically if multiple

### Same-Date Snapping
When a role's `date_start` matches its parent job's `date_start`, the role marker snaps to the same horizontal position as the job marker.

### Sidebar Interaction
- **Scroll**: IntersectionObserver sets `$currentRoleId` based on which row is most visible
- **Hover (desktop)**: Mouse over role markers OR project dots temporarily switches sidebar to that role
- Sidebar shows: job logo (max 240×80px), colored divider, role name, description, accolade cards (split by newline)

### Project Popup
Fixed on mobile (bottom), absolute on desktop (scrolls with page). Shows full media like ProjectCard: image mosaic → video carousel → YouTube Shorts pairs.

## ProjectCard (Work Type Pages)

Media presentation rules:
1. **Images**: Mosaic grid (1→full, 2/4→2col, 3+→3col), each clickable for lightbox
2. **Regular videos + landscape YouTube**: Click-to-play with first-frame thumbnail. Carousel with arrows if multiple
3. **YouTube Shorts** (`/shorts/` URL): Portrait 9:16, displayed in pairs, carousel if >2
4. **Order**: Images top → regular videos middle → Shorts bottom

Anchor scrolling: URL hash `#project-123` scrolls to card with brief highlight animation.

## Admin CMS

All admin pages at `/admin/*`. Dark theme with CSS variables. Features:
- **CRUD** for jobs, roles, projects with inline tag creation on multi-selects
- **MediaManager**: drag-to-reorder, type selector (image/video/youtube), file upload or URL input
- **Settings page**: manage all lookup tables (tools, weights, work types, skills, proficiencies)
- **Files page**: upload manager with preview grid and delete

## Common Pitfalls

1. **Svelte `{@const}` errors**: Must be inside control flow blocks, not plain HTML elements
2. **Auth "Not authenticated"**: Gunicorn needs `--preload` in systemd service
3. **`[slug]` matching `/admin`**: The `notadmin.js` param matcher prevents this
4. **File truncation**: When generating long files, verify the closing `</style>` tag is present
5. **CSS `select option`**: Must explicitly style with dark background, otherwise invisible on some OS
6. **Reactive ordering in Svelte**: Don't rely on `$:` reactive statements running in a specific order — compute dependent values inside the same function
