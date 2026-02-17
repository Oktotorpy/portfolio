import { loadPortfolioData } from '$lib/data.server.js';

export async function load({ fetch }) {
  return await loadPortfolioData(fetch);
}
