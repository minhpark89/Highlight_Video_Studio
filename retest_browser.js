const fs = require('fs');
const http = require('http');

http.get('http://127.0.0.1:5080/', (res) => {
  let html = '';
  res.on('data', chunk => html += chunk);
  res.on('end', () => {
    console.log('Fetched HTML length:', html.length);
    const m = html.match(/<script[\s\S]*?>([\s\S]*?)<\/script>/i);
    if (!m) {
      console.log('No script tag found!');
      return;
    }
    const script = m[1];
    try {
      new Function(script);
      console.log('SUCCESS: Script parsed with ZERO syntax errors!');
    } catch (e) {
      console.error('STILL SYNTAX ERROR:', e);
    }
  });
});
