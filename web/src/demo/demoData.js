/** Demo mode uses a fixed project id — never sent to the real backend. */

export const DEMO_PROJECT_ID = '__demo__';

export const DEMO_TICKETS = [
  {
    id: 'demo-1',
    ticket_key: 'FTSWB-5641',
    title: '[FE][SEO] Reduce layout shift (CLS) on article pages',
    description: 'Reserve vertical space for nav, App Store banner, and top ad on mobile articles.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-2',
    ticket_key: 'FTSWB-5602',
    title: '[FE] Fix broken thumbnail aspect ratio on video cards',
    description: 'Video cards render 16:9 placeholders before images load.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-3',
    ticket_key: 'FTSWB-5588',
    title: '[FE] Add lazy-load for below-the-fold images',
    description: 'Improve LCP by deferring non-critical article images.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-4',
    ticket_key: 'FTSWB-5510',
    title: '[FE] Update breaking news banner z-index stacking',
    description: 'Banner overlaps site nav on small viewports.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-5',
    ticket_key: 'FTSWB-5499',
    title: '[FE] RSS feed validator error on category pages',
    description: 'Invalid XML entity in category RSS output.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-6',
    ticket_key: 'FTSWB-5472',
    title: '[FE] Hero image preload hint for homepage LCP',
    description: 'Add fetchpriority and preload link for hero asset.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-7',
    ticket_key: 'FTSWB-5440',
    title: '[FE] Skip link focus trap on article templates',
    description: 'Keyboard users cannot reach main content skip target.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-8',
    ticket_key: 'FTSWB-5418',
    title: '[FE] Sticky nav jitter on iOS Safari scroll',
    description: 'Position sticky recalculates when address bar collapses.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-9',
    ticket_key: 'FTSWB-5395',
    title: '[FE] AMP canonical URL mismatch on section pages',
    description: 'Canonical tag points to wrong path on paginated sections.',
    status: 'pending',
    board_lane: 'todo',
  },
  {
    id: 'demo-10',
    ticket_key: 'FTSWB-5371',
    title: '[FE] Reduce unused JavaScript on article bundle',
    description: 'Split chartbeat and social widgets from critical path.',
    status: 'pending',
    board_lane: 'todo',
  },
];

export function createDemoProject() {
  const now = new Date().toISOString();
  return {
    id: DEMO_PROJECT_ID,
    name: 'Demo batch — 10 tickets',
    brief: 'Sample data only · no backend calls',
    status: 'ready',
    mode: 'jira',
    provider: 'ollama',
    model: 'codestral',
    repo_context_path: '/Sites/fts-foxnews.com',
    created_at: now,
    updated_at: now,
  };
}

export function isDemoProjectId(id) {
  return id === DEMO_PROJECT_ID;
}

export function demoTicketNumber(ticketId) {
  return parseInt(String(ticketId).replace('demo-', ''), 10) || 1;
}

/** Scripted status lines under each ticket progress bar. */
export const DEMO_THOUGHTS = {
  'demo-1': [
    'Reading CLS acceptance criteria for mobile articles…',
    'Scanning ArticleLayout and header components…',
    'Planning reserved-height slots for nav + banners…',
    'Writing CSS custom properties for chrome heights…',
    'Patching ArticleLayout.vue and SiteHeader.vue…',
    'Running apply step in worktree…',
    'Committing branch codex/FTSWB-5641…',
  ],
  'demo-2': [
    'Inspecting VideoCard thumbnail markup…',
    'Checking aspect-ratio in shared media components…',
    'Drafting placeholder dimensions fix…',
    'Updating VideoCard.vue styles…',
  ],
  'demo-3': [
    'Finding below-the-fold image components…',
    'Adding loading="lazy" and srcset…',
    'Patching ArticleImage.vue…',
  ],
  'demo-4': [
    'Reviewing z-index stack for breaking banner…',
    'Adjusting header stacking context…',
    'Editing BreakingBanner.scss…',
  ],
  'demo-5': [
    'Locating category RSS template…',
    'Escaping XML entities in feed builder…',
    'Patching rss/category.xml.js…',
  ],
  'demo-6': [
    'Auditing homepage hero LCP waterfall…',
    'Adding preload link in nuxt head config…',
  ],
  'demo-7': [
    'Testing skip link tab order on article…',
    'Fixing focus target in ArticleTemplate…',
  ],
  'demo-8': [
    'Reproducing iOS Safari sticky jitter…',
    'Adding transform workaround to SiteNav…',
  ],
  'demo-9': [
    'Comparing canonical on paginated sections…',
    'Fixing amp link helper…',
  ],
  'demo-10': [
    'Profiling article bundle chunks…',
    'Dynamic-importing social widget module…',
  ],
};

export const DEMO_TASKS = {
  'demo-1': [
    { id: 't1', label: 'Identify layout-shifting chrome on mobile article template', status: 'pending' },
    { id: 't2', label: 'Measure nav, App Store banner, and top ad heights', status: 'pending' },
    { id: 't3', label: 'Reserve vertical space in ArticleLayout before paint', status: 'pending' },
    { id: 't4', label: 'Verify headline does not jump when banners load', status: 'pending' },
  ],
};

/** Plan markdown shown in modal during analyze phase. */
export const DEMO_PLAN = {
  'demo-1': `## Understanding
FTSWB-5641 asks us to reduce Cumulative Layout Shift (CLS) on mobile FTS article pages. The main culprits are the site nav header, FOX Local / App Store banner, and top ad slot settling in after first paint.

## Task List
- [ ] Identify layout-shifting chrome on mobile article template
- [ ] Measure nav, App Store banner, and top ad heights
- [ ] Reserve vertical space in ArticleLayout before paint
- [ ] Verify headline does not jump when banners load

## Approach
- \`components/layouts/ArticleLayout.vue\` — reserve chrome slot heights via CSS variables
- \`components/chrome/SiteHeader.vue\` — expose measured banner height
- \`assets/styles/article-chrome.scss\` — shared min-height rules for mobile`,
};

/** Code blocks streamed during implement phase (appended in chunks). */
export const DEMO_CODE = {
  'demo-1': `### \`components/layouts/ArticleLayout.vue\`
\`\`\`vue
<template>
  <div class="article-layout" :style="chromeStyle">
    <SiteHeader @banner-height="onBannerHeight" />
    <div class="article-chrome-spacer" aria-hidden="true" />
    <slot name="top-ad" />
    <main class="article-main">
      <slot />
    </main>
  </div>
</template>

<script>
const DEFAULT_BANNER_H = 52;
const DEFAULT_TOP_AD_H = 90;

export default {
  data: () => ({
    bannerHeight: DEFAULT_BANNER_H,
    topAdHeight: DEFAULT_TOP_AD_H,
  }),
  computed: {
    chromeStyle() {
      return {
        '--banner-reserved-h': \`\${this.bannerHeight}px\`,
        '--top-ad-reserved-h': \`\${this.topAdHeight}px\`,
      };
    },
  },
  methods: {
    onBannerHeight(h) {
      this.bannerHeight = h || DEFAULT_BANNER_H;
    },
  },
};
</script>

<style scoped>
.article-chrome-spacer {
  min-height: calc(var(--banner-reserved-h) + var(--top-ad-reserved-h));
}
.article-main {
  contain: layout;
}
</style>
\`\`\`

### \`components/chrome/SiteHeader.vue\`
\`\`\`vue
<template>
  <header class="site-header">
    <AppStoreBanner ref="banner" @resize="emitHeight" />
    <nav class="site-nav">...</nav>
  </header>
</template>

<script>
export default {
  mounted() {
    this.emitHeight();
  },
  methods: {
    emitHeight() {
      const h = this.$refs.banner?.$el?.offsetHeight ?? 52;
      this.$emit('banner-height', h);
    },
  },
};
</script>
\`\`\`

## Implementation Notes
Reserved heights use production measurements with safe defaults so late-loading chrome does not push article content.

## Verification
- Load mobile article page; confirm CLS < 0.1 in DebugBear
- Verify headline position stable when App Store banner appears`,
};

/** Fallback plan/code for tickets without bespoke content. */
export function getDemoPlan(ticket) {
  if (DEMO_PLAN[ticket.id]) return DEMO_PLAN[ticket.id];
  return `## Understanding
${ticket.ticket_key}: ${ticket.title}

${ticket.description}

## Task List
- [ ] Reproduce issue on target template
- [ ] Locate owning components in repo tree
- [ ] Implement minimal fix with tests
- [ ] Verify acceptance criteria

## Approach
- Inspect \`components/\` and \`pages/\` for related templates
- Patch smallest surface area that satisfies AC`;
}

export function getDemoCode(ticket) {
  if (DEMO_CODE[ticket.id]) return DEMO_CODE[ticket.id];
  const slug = ticket.ticket_key.toLowerCase();
  return `### \`components/fixes/${slug}.vue\`
\`\`\`vue
<template>
  <div class="fix-${slug}">
    <!-- ${ticket.title} -->
  </div>
</template>

<script>
export default {
  name: 'Fix${ticket.ticket_key.replace(/-/g, '')}',
};
</script>
\`\`\`

## Implementation Notes
Automated fix scaffold for ${ticket.ticket_key}.

## Verification
- Manual QA on affected page
- No regressions on related templates`;
}

export function getDemoTasks(ticket) {
  if (DEMO_TASKS[ticket.id]) return DEMO_TASKS[ticket.id];
  return [
    { id: '1', label: `Reproduce ${ticket.ticket_key} locally`, status: 'pending' },
    { id: '2', label: 'Identify files to change', status: 'pending' },
    { id: '3', label: 'Implement and verify fix', status: 'pending' },
  ];
}
