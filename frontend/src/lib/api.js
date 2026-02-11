const BASE = '';

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: {},
    credentials: 'include'
  };

  if (body && !(body instanceof FormData)) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  } else if (body instanceof FormData) {
    opts.body = body;
  }

  const res = await fetch(`${BASE}${path}`, opts);
  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`);
  }

  return data;
}

export const api = {
  // Auth
  login: (username, password) => request('POST', '/api/auth/login', { username, password }),
  logout: () => request('POST', '/api/auth/logout'),
  me: () => request('GET', '/api/auth/me'),

  // Contact
  getContact: () => request('GET', '/api/contact'),
  updateContact: (data) => request('PUT', '/api/contact', data),

  // Jobs
  getJobs: () => request('GET', '/api/jobs'),
  getJob: (id) => request('GET', `/api/jobs/${id}`),
  createJob: (data) => request('POST', '/api/jobs', data),
  updateJob: (id, data) => request('PUT', `/api/jobs/${id}`, data),
  deleteJob: (id) => request('DELETE', `/api/jobs/${id}`),
  updateJobLogo: (id, logoPath) => request('PUT', `/api/jobs/${id}/logo`, { logo: logoPath }),

  // Roles
  getRoles: (jobId = null) => request('GET', jobId ? `/api/roles?job_id=${jobId}` : '/api/roles'),
  getRole: (id) => request('GET', `/api/roles/${id}`),
  createRole: (data) => request('POST', '/api/roles', data),
  updateRole: (id, data) => request('PUT', `/api/roles/${id}`, data),
  deleteRole: (id) => request('DELETE', `/api/roles/${id}`),

  // Projects
  getProjects: (roleId = null) => request('GET', roleId ? `/api/projects?role_id=${roleId}` : '/api/projects'),
  getProject: (id) => request('GET', `/api/projects/${id}`),
  createProject: (data) => request('POST', '/api/projects', data),
  updateProject: (id, data) => request('PUT', `/api/projects/${id}`, data),
  deleteProject: (id) => request('DELETE', `/api/projects/${id}`),

  // Lookups
  getLookups: () => request('GET', '/api/lookups'),
  addLookup: (table, name) => request('POST', `/api/lookups/${table}`, { name }),
  updateLookup: (table, id, name) => request('PUT', `/api/lookups/${table}/${id}`, { name }),
  deleteLookup: (table, id) => request('DELETE', `/api/lookups/${table}/${id}`),

  // Uploads
  upload: async (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('POST', '/api/uploads', form);
  }
};
