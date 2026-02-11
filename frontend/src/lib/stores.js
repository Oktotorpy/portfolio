import { writable } from 'svelte/store';

export const authenticated = writable(false);

export const lookups = writable({
  countries: [],
  proficiencies: [],
  skills: [],
  work_types: [],
  tools: [],
  weights: []
});

export const currentRoleId = writable(null);
