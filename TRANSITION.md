# Transition to Claude Code — Session Context

This document captures critical context from the claude.ai chat sessions (Feb 10–12, 2026) that built this project from scratch. Read this alongside `CLAUDE.md` to understand decisions, patterns, and current state.

## How This Project Was Built

The entire project was built across ~8 claude.ai sessions. Files were generated in the chat, downloaded by the user, and placed into the repo manually (or via a PowerShell helper script). The user then pushed to GitHub and deployed via `deploy.sh pull` on the server.

**With Claude Code, you now have direct repo access.** You can edit files in-place, run the dev server, and test changes locally. No more file downloads or manual placement.

## Current State (as of Feb 12, 2026)

### What's Working
- Full CMS: CRUD for jobs, roles, projects, contact
- All lookup tables manageable in Settings page
- Multi-media support on projects (images, videos, YouTube, YouTube Shorts)
- File upload manager
- Public timeline homepage with scroll-driven sidebar
- Work type pages with ProjectCard media presentation
- GitHub → server deployment pipeline

### Recent Changes (Last Session)
These were the final changes made in the chat session. Verify they're deployed:

1. **Timeline visual overhaul** (PAGE-timeline-home.svelte → `src/routes/+page.svelte`):
   - 4px job-colored lines with overlap stacking
   - Weight-based project dots (Small/Medium/Big/Landmark★/Continuous∞)
   - Role tags: "New role" (dark green #2a5a3a), "Promotion" (gold #b8a46c), "Currently" (blue #3a5a8a)
   - Same-date snapping for job+role markers
   - Role name underline using border-bottom (matches text width)
   - Desktop popups use `position: absolute` (scroll with page)
   - Currently roles stack vertically when multiple (margin-top offset)

2. **Sidebar** (Sidebar.svelte → `src/lib/components/Sidebar.svelte`):
   - Job logo: max 240×80px
   - Colored divider using job color
   - Accolade cards (split by newline, left border colored)

3. **ProjectCard** (ProjectCard.svelte → `src/lib/components/ProjectCard.svelte`):
   - Click-to-play videos with first-frame thumbnails
   - Image mosaic grid
   - YouTube Shorts in portrait pairs with carousel
   - Content ordering: images → videos → shorts

## File Naming Convention from Chat

During the chat sessions, files were named with descriptive prefixes because they needed to be renamed when placed in the SvelteKit directory structure:

| Chat Name | Actual Path |
|-----------|-------------|
| `PAGE-timeline-home.svelte` | `frontend/src/routes/+page.svelte` |
| `PAGE-slug-worktype.svelte` | `frontend/src/routes/[slug=notadmin]/+page.svelte` |
| `PAGE-admin-*.svelte` | `frontend/src/routes/admin/*/+page.svelte` |
| `ADMIN-LAYOUT.svelte` | `frontend/src/routes/admin/+layout.svelte` |
| Everything else | Same filename, placed in appropriate directory |

**With Claude Code, you don't need this convention.** Edit files at their real paths.

## Key Patterns to Follow

### Adding a New Field to an Existing Table

1. Add migration in `backend/database.py` → `run_migrations()`:
   ```python
   try:
       db.execute("ALTER TABLE tablename ADD COLUMN colname TYPE DEFAULT value")
   except: pass
   ```
2. Update the route's `_row_to_*` function and CRUD handlers in `backend/routes/*.py`
3. Update the admin page form in `frontend/src/routes/admin/*/+page.svelte`
4. Update `data.server.js` if the field should appear on public pages
5. Update relevant public components (Sidebar, ProjectCard, timeline)

### Adding a New Lookup Table

1. Add `CREATE TABLE IF NOT EXISTS` in `schema.sql`
2. Add seed data insert
3. Add CRUD routes in `lookups.py` (follow existing pattern)
4. Register blueprint in `main.py`
5. Add management UI in Settings admin page
6. Add junction table if needed

### Svelte Component Patterns

- Admin pages: standalone, import `api.js` for fetch calls
- Public pages: wrap in `<PublicShell>`, get data from `+page.server.js`
- Multi-selects: use `<MultiSelect>` component with `createEndpoint` prop for inline creation
- Media: use `<MediaManager>` for admin, classification helpers in ProjectCard for display

## Gotchas Learned the Hard Way

### Svelte 5 Compilation
The project uses Svelte 4 syntax but compiles with Svelte 5. The `{@const}` directive is stricter:
```svelte
<!-- WRONG: @const directly in a div -->
<div>
  {@const x = computeSomething()}
  {x}
</div>

<!-- RIGHT: wrap in each to create valid scope -->
{#each [computeSomething()] as x}
  <div>{x}</div>
{/each}
```

### Reactive Statement Ordering
Don't depend on `$:` statements running in a specific order. If function A reads a value computed by reactive B, compute it inside A instead:
```javascript
// BAD: roleIndexMap might not be ready when buildRows runs
$: roleIndexMap = buildMap(data.roles);
$: rows = buildRows(data); // reads roleIndexMap

// GOOD: compute inside the function
$: rows = buildRows(data);
function buildRows(data) {
  const roleIndexMap = buildMap(data.roles); // computed here
  // ... use roleIndexMap
}
```

### Gunicorn Auth
The backend uses session-based auth. Gunicorn workers don't share memory by default, so `--preload` is required in the systemd service file. Without it, login works but subsequent requests fail with "Not authenticated".

### CSS Select Dropdowns
Browser renders `<select>` options with OS default backgrounds. In dark themes, add:
```css
select option { background: var(--bg-input); color: var(--text); }
```

### File Truncation
When generating long Svelte files (500+ lines), verify the `</style>` closing tag exists. Multiple times during development, files were silently truncated.

## Environment Variables (.env)

```
DOMAIN=your-domain.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<bcrypt hash>
SECRET_KEY=<random hex>
DB_PATH=/opt/portfolio/data/portfolio.db
UPLOAD_DIR=/opt/portfolio/uploads
CORS_ORIGIN=https://your-domain.com
BACKEND_PORT=8000
FRONTEND_PORT=3000
INTERNAL_API_URL=http://localhost:8000
```

## Quick Reference: API Endpoints

### Public (no auth)
- `GET /api/jobs` — all jobs with countries
- `GET /api/roles` — all roles with proficiencies (optional `?job_id=`)
- `GET /api/projects` — all projects with skills/tools/media (optional `?role_id=`, `?work_type=`)
- `GET /api/contact` — singleton contact
- `GET /api/work-types` — list
- `GET /api/weights` — list
- `GET /uploads/<filename>` — static file serving

### Admin (require_auth)
- `POST/PUT/DELETE /api/jobs/<id>`
- `POST/PUT/DELETE /api/roles/<id>`
- `POST/PUT/DELETE /api/projects/<id>`
- `PUT /api/contact`
- `POST/DELETE /api/lookups/<table>/<id>` — CRUD for all lookup tables
- `POST /api/upload` — file upload
- `GET /api/files` — list uploaded files
- `DELETE /api/files/<filename>`
- `POST /api/auth/login` / `POST /api/auth/logout` / `GET /api/auth/check`

## GitHub Repo

- **Repo**: `github.com/Oktotorpy/portfolio` (private)
- **Branch**: `main`
- **Deploy**: `ssh root@SERVER "/opt/portfolio/deploy.sh pull"`
