import { writable } from 'svelte/store';

export const authenticated = writable(false);

export const lookups = writable({
  countries: [],
  proficiencies: [],
  skills: [],
  work_types: []
});

// Tracks which role should show in the sidebar (based on scroll position)
export const currentRoleId = writable(null);
