<script>
  import { page } from '$app/stores';
  import { currentRoleId } from '$lib/stores.js';
  import { slugify } from '$lib/utils.js';
  import Sidebar from '$lib/components/Sidebar.svelte';

  export let contact = {};
  export let roles = [];
  export let workTypes = [];

  let mobileMenuOpen = false;

  $: navItems = workTypes.map(wt => ({
    name: wt.name,
    slug: slugify(wt.name),
    href: `/${slugify(wt.name)}`
  }));
  $: currentPath = $page.url.pathname;

  $: activeRole = roles.find(r => r.id === $currentRoleId) || null;
  $: activeJob = activeRole?.job || null;

  function closeMobileMenu() {
    mobileMenuOpen = false;
  }
</script>

<div class="public-layout">
  <!-- MOBILE HEADER -->
  <header class="mobile-header">
    <div class="mobile-header-left">
      {#if contact.name}
        <span class="mh-name">{contact.name}</span>
      {/if}
      {#if contact.email}
        <a href="mailto:{contact.email}" class="mh-email">{contact.email}</a>
      {/if}
    </div>
    <div class="mobile-header-right">
      {#if activeRole}
        <span class="mh-role">{activeRole.name}</span>
        {#if activeJob}
          <span class="mh-company">{activeJob.name}</span>
        {/if}
      {/if}
    </div>
  </header>

  <!-- DESKTOP LAYOUT -->
  <div class="layout-container">
    <div class="layout-sidebar">
      <Sidebar {contact} {roles} />
    </div>

    <div class="layout-main">
      <nav class="main-nav">
        <a href="/" class="nav-link" class:active={currentPath === '/'}>Timeline</a>
        {#each navItems as item}
          <a href={item.href} class="nav-link" class:active={currentPath === item.href}>{item.name}</a>
        {/each}
      </nav>

      <div class="main-content-public">
        <slot />
      </div>
    </div>
  </div>

  <!-- MOBILE BOTTOM NAV -->
  <nav class="mobile-nav">
    <a href="/" class="mobile-nav-link" class:active={currentPath === '/'}>Timeline</a>

    <div class="mobile-nav-burger-wrap">
      <button
        class="mobile-nav-burger"
        class:open={mobileMenuOpen}
        on:click={() => mobileMenuOpen = !mobileMenuOpen}
        aria-label="Menu"
      >
        <span></span>
        <span></span>
        <span></span>
      </button>

      {#if mobileMenuOpen}
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div class="mobile-dropdown-backdrop" on:click={closeMobileMenu}></div>
        <div class="mobile-dropdown">
          {#each navItems as item}
            <a
              href={item.href}
              class="mobile-dropdown-link"
              class:active={currentPath === item.href}
              on:click={closeMobileMenu}
            >{item.name}</a>
          {/each}
        </div>
      {/if}
    </div>
  </nav>
</div>

<style>
  .public-layout {
    font-family: 'Geist', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
    color: var(--text);
    min-height: 100vh;
    background: var(--bg-page);
  }

  .layout-container {
    width: 65%;
    max-width: 1100px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 0;
    padding-top: 48px;
    min-height: 100vh;
  }

  .layout-main {
    padding-left: 40px;
    min-width: 0;
  }

  .main-nav {
    display: flex;
    gap: 0;
    border-bottom: 1px solid var(--border-subtle);
    margin-bottom: 32px;
    position: sticky;
    top: 0;
    background: var(--bg-page);
    z-index: 10;
    padding-top: 4px;
  }

  .nav-link {
    padding: 12px 16px;
    font-size: 14px;
    font-weight: 500;
    color: var(--text-muted);
    text-decoration: none;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .nav-link:hover { color: var(--text-dim); }

  .nav-link.active {
    color: var(--text);
    border-bottom-color: var(--text);
  }

  .main-content-public { padding-bottom: 80px; }

  .mobile-header { display: none; }
  .mobile-nav { display: none; }

  @media (max-width: 1200px) {
    .layout-container { width: 80%; }
  }

  @media (max-width: 900px) {
    .layout-container { width: 90%; grid-template-columns: 200px 1fr; }
  }

  @media (max-width: 768px) {
    .layout-sidebar { display: none; }
    .main-nav { display: none; }

    .layout-container {
      width: 100%;
      grid-template-columns: 1fr;
      padding: 56px 16px 80px;
    }

    .layout-main { padding-left: 0; }

    .mobile-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      padding: 12px 16px;
      position: fixed;
      top: 0; left: 0; right: 0;
      background: var(--bg-page);
      border-bottom: 1px solid var(--border-subtle);
      z-index: 50;
    }

    .mh-name { font-size: 13px; font-weight: 600; color: var(--text); display: block; }
    .mh-email { font-size: 11px; color: var(--text-muted); text-decoration: none; }
    .mobile-header-right { text-align: right; }
    .mh-role { font-size: 12px; font-weight: 500; color: var(--text-dim); display: block; }
    .mh-company { font-size: 11px; color: var(--text-muted); display: block; }

    .mobile-nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      position: fixed;
      bottom: 0; left: 0; right: 0;
      background: var(--bg-elevated);
      border-top: 1px solid var(--border-subtle);
      padding: 0 16px;
      height: 52px;
      z-index: 50;
    }

    .mobile-nav-link {
      font-size: 14px; font-weight: 500; color: var(--text-muted);
      text-decoration: none; padding: 14px 0;
    }
    .mobile-nav-link.active { color: var(--text); }

    .mobile-nav-burger-wrap { position: relative; }

    .mobile-nav-burger {
      background: none; border: none;
      width: 36px; height: 36px;
      display: flex; flex-direction: column;
      justify-content: center; align-items: center;
      gap: 5px; cursor: pointer; padding: 6px;
    }

    .mobile-nav-burger span {
      display: block; width: 20px; height: 1.5px;
      background: var(--text-faint); border-radius: 1px; transition: all 0.2s;
    }

    .mobile-nav-burger.open span:nth-child(1) { transform: translateY(6.5px) rotate(45deg); }
    .mobile-nav-burger.open span:nth-child(2) { opacity: 0; }
    .mobile-nav-burger.open span:nth-child(3) { transform: translateY(-6.5px) rotate(-45deg); }

    .mobile-dropdown-backdrop { position: fixed; inset: 0; z-index: 40; }

    .mobile-dropdown {
      position: absolute;
      bottom: 48px; right: 0;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 0;
      min-width: 180px;
      z-index: 45;
    }

    .mobile-dropdown-link {
      display: block; padding: 10px 16px;
      font-size: 14px; color: var(--text-faint);
      text-decoration: none; transition: all 0.15s;
    }

    .mobile-dropdown-link:hover,
    .mobile-dropdown-link.active {
      color: var(--text);
      background: var(--highlight);
    }

    .main-content-public { padding-bottom: 16px; }
  }
</style>
