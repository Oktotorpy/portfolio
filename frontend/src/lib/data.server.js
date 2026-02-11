import { env } from '$env/dynamic/private';

const API = env.INTERNAL_API_URL || 'http://localhost:8000';

export async function loadPortfolioData(fetch) {
  try {
    const [contact, lookups, jobs, roles, projects] = await Promise.all([
      fetch(`${API}/api/contact`).then(r => r.json()),
      fetch(`${API}/api/lookups`).then(r => r.json()),
      fetch(`${API}/api/jobs`).then(r => r.json()),
      fetch(`${API}/api/roles`).then(r => r.json()),
      fetch(`${API}/api/projects`).then(r => r.json()),
    ]);

    const jobMap = Object.fromEntries(jobs.map(j => [j.id, j]));
    const enrichedProjects = projects.map(p => ({
      ...p,
      role: { ...(roles.find(r => r.id === p.role_id) || {}), job: jobMap[(roles.find(r => r.id === p.role_id) || {}).job_id] || null },
    }));

    return {
      contact,
      lookups,
      jobs,
      roles: roles.map(r => ({ ...r, job: jobMap[r.job_id] || null })),
      projects: enrichedProjects,
      workTypes: lookups.work_types || [],
    };
  } catch (err) {
    console.error('Failed to load portfolio data:', err);
    return {
      contact: {},
      lookups: { work_types: [], skills: [], countries: [], proficiencies: [], tools: [], weights: [] },
      jobs: [],
      roles: [],
      projects: [],
      workTypes: [],
    };
  }
}
