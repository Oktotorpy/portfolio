<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api } from '$lib/api.js';
  import { authenticated, lookups } from '$lib/stores.js';

  export let data;

  // Start with server-side auth state to prevent content flash
  let loading = true;
  let loginError = '';
  let username = '';
  let password = '';

  // Use server auth to set initial state
  $: if (data.serverAuthenticated !== undefined) {
    $authenticated = data.serverAuthenticated;
  }

  onMount(async () => {
    try {
      const res = await api.me();
      $authenticated = res.authenticated;
      if (res.authenticated) {
        await loadLookups();
      }
    } catch {
      $authenticated = false;
    } finally {
      loading = false;
    }
  });

  async function loadLookups() {
    try {
      $lookups = await api.getLookups();
    } catch {}
  }

  async function handleLogin() {
    loginError = '';
    try {
      await api.login(username, password);
      $authenticated = true;
      await loadLookups();
    } catch (err) {
      loginError = err.message;
    }
  }

  async function handleLogout() {
    await api.logout();
    $authenticated = false;
  }

  const navItems = [
    { href: '/admin/contact', label: 'Contact', icon: '👤' },
    { href: '/admin/jobs', label: 'Jobs', icon: '🏢' },
    { href: '/admin/roles', label: 'Roles', icon: '💼' },
    { href: '/admin/projects', label: 'Projects', icon: '📁' },
    { href: '/admin/files', label: 'Files', icon: '🖼️' },
    { href: '/admin/election', label: 'Election', icon: '🗳️' },
    { href: '/admin/settings', label: 'Settings', icon: '⚙️' }
  ];

  $: currentPath = $page.url.pathname;
</script>

{#if loading && !$authenticated}
  <div class="login-page">
    <p style="color: var(--text-dim);">Loading...</p>
  </div>
{:else if !$authenticated}
  <div class="login-page">
    <div class="login-card">
      <h1>Portfolio CMS</h1>

      {#if loginError}
        <div class="msg msg-error">{loginError}</div>
      {/if}

      <form on:submit|preventDefault={handleLogin}>
        <div class="form-group">
          <label>Username</label>
          <input type="text" bind:value={username} autocomplete="username" />
        </div>
        <div class="form-group">
          <label>Password</label>
          <input type="password" bind:value={password} autocomplete="current-password" />
        </div>
        <button type="submit" class="btn btn-primary" style="width: 100%;">Log in</button>
      </form>
    </div>
  </div>
{:else}
  <div class="admin-layout">
    <aside class="sidebar">
      <div class="sidebar-title">Portfolio CMS</div>
      <nav>
        {#each navItems as item}
          <a href={item.href} class:active={currentPath.startsWith(item.href)}>
            <span>{item.icon}</span>
            {item.label}
          </a>
        {/each}
      </nav>
      <div class="sidebar-footer">
        <button class="btn btn-ghost btn-sm" style="width: 100%;" on:click={handleLogout}>
          Log out
        </button>
      </div>
    </aside>
    <main class="main-content">
      <slot />
    </main>
  </div>
{/if}
