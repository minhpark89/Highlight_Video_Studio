const fs = require('fs');

const scriptContent = fs.readFileSync('D:/Highlight_Video_Studio/extracted_script.js', 'utf8');

// Mock browser environment
const dom = {};
const listeners = {};

global.window = global;
global.document = {
  getElementById: (id) => {
    if (!dom[id]) {
      dom[id] = {
        id: id,
        innerHTML: '',
        textContent: '',
        value: '',
        style: { display: '', setProperty: () => {} },
        classList: { add: () => {}, remove: () => {} },
        addEventListener: (ev, fn) => {
          if (!listeners[ev]) listeners[ev] = [];
          listeners[ev].push(fn);
        },
        querySelectorAll: () => []
      };
    }
    return dom[id];
  },
  querySelectorAll: (selector) => {
    return [];
  },
  querySelector: (selector) => null,
  addEventListener: (ev, fn) => {
    if (!listeners[ev]) listeners[ev] = [];
    listeners[ev].push(fn);
  }
};

global.fetch = async (url) => {
  console.log('[Mock Fetch] Request to:', url);
  if (url === '/api/tokens') {
    const data = JSON.parse(fs.readFileSync('D:/Highlight_Video_Studio/tokens_vault.json', 'utf8'));
    return {
      json: async () => ({ success: true, tokens: Object.values(data.tokens || {}) })
    };
  }
  if (url === '/api/pages') {
    const data = JSON.parse(fs.readFileSync('D:/Highlight_Video_Studio/pages.json', 'utf8'));
    return {
      json: async () => ({ success: true, pages: data.pages || [] })
    };
  }
  if (url === '/api/groups') {
    return {
      json: async () => ({ success: true, groups: [] })
    };
  }
  return {
    json: async () => ({})
  };
};

try {
  // Execute the script
  eval(scriptContent);
  console.log('[Success] Script parsed and executed without top-level errors!');

  // Trigger DOMContentLoaded
  if (listeners['DOMContentLoaded']) {
    console.log('[Testing DOMContentLoaded] count:', listeners['DOMContentLoaded'].length);
    for (const fn of listeners['DOMContentLoaded']) {
      fn();
    }
  }

  // Also call loadTokensAndPages explicitly
  if (typeof loadTokensAndPages === 'function') {
    console.log('[Testing loadTokensAndPages] invoking...');
    loadTokensAndPages().then(() => {
      console.log('--- RESULT AFTER loadTokensAndPages ---');
      console.log('stat-total-tokens:', dom['stat-total-tokens']?.textContent);
      console.log('stat-total-pages:', dom['stat-total-pages']?.textContent);
      console.log('tokens-list-container length:', dom['tokens-list-container']?.innerHTML?.length);
      console.log('pages-tbody length:', dom['pages-tbody']?.innerHTML?.length);
      if (dom['pages-tbody']?.innerHTML?.length < 100) {
        console.log('pages-tbody content:', dom['pages-tbody']?.innerHTML);
      } else {
        console.log('pages-tbody snippet:', dom['pages-tbody']?.innerHTML?.slice(0, 300));
      }
    }).catch(err => {
      console.error('[loadTokensAndPages error catch]:', err);
    });
  } else {
    console.error('loadTokensAndPages is NOT defined!');
  }
} catch (e) {
  console.error('[Execution Exception]:', e);
}
