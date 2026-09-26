const fs = require('fs');

const scriptContent = fs.readFileSync('D:/Highlight_Video_Studio/extracted_script.js', 'utf8');

const listeners = {};

// Mock complete browser window & document
global.window = {
  addEventListener: (ev, fn) => {
    if (!listeners[ev]) listeners[ev] = [];
    listeners[ev].push(fn);
  }
};
global.window.window = global.window;

const elements = {};
global.document = {
  getElementById: (id) => {
    if (!elements[id]) {
      elements[id] = {
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
    return elements[id];
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
  // console.log('[Fetch]', url);
  if (url === '/api/tokens') {
    const data = JSON.parse(fs.readFileSync('D:/Highlight_Video_Studio/tokens_vault.json', 'utf8'));
    return {
      ok: true,
      json: async () => ({ success: true, tokens: Object.values(data.tokens || {}) })
    };
  }
  if (url === '/api/pages') {
    const data = JSON.parse(fs.readFileSync('D:/Highlight_Video_Studio/pages.json', 'utf8'));
    return {
      ok: true,
      json: async () => ({ success: true, pages: data.pages || [] })
    };
  }
  if (url === '/api/groups') {
    return {
      ok: true,
      json: async () => ({ success: true, groups: [] })
    };
  }
  if (url === '/api/jobs') {
    return {
      ok: true,
      json: async () => []
    };
  }
  if (url === '/api/clips') {
    return {
      ok: true,
      json: async () => ({ clips: [] })
    };
  }
  if (url.includes('/api/system/')) {
    return {
      ok: true,
      json: async () => ({})
    };
  }
  return {
    ok: true,
    json: async () => ({})
  };
};

try {
  eval(scriptContent);
  console.log('Script loaded successfully without top-level errors.');
} catch (e) {
  console.error('TOP LEVEL EVAL ERROR:', e);
}

// Trigger DOMContentLoaded
if (listeners['DOMContentLoaded']) {
  console.log('Triggering DOMContentLoaded listeners:', listeners['DOMContentLoaded'].length);
  listeners['DOMContentLoaded'].forEach(fn => {
    try {
      fn();
    } catch (e) {
      console.error('DOMContentLoaded callback error:', e);
    }
  });
}

// Wait and check what happened to tokens and pages
setTimeout(() => {
  console.log('After timeout:');
  console.log('stat-total-tokens:', elements['stat-total-tokens']?.textContent);
  console.log('stat-total-pages:', elements['stat-total-pages']?.textContent);
  console.log('tokens-list-container length:', elements['tokens-list-container']?.innerHTML.length);
  console.log('pages-tbody length:', elements['pages-tbody']?.innerHTML.length);
}, 200);
