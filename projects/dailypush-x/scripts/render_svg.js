#!/usr/bin/env node
// Render an SVG illustration to a PNG for X (1600x900, 16:9).
// Usage: node render_svg.js in.svg out.png [width] [height]
// Uses the Chromium + Playwright that the cloud container ships with.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

async function main() {
  const [input, output, w = '1600', h = '900'] = process.argv.slice(2);
  if (!input || !output) {
    console.error('usage: node render_svg.js in.svg out.png [width] [height]');
    process.exit(2);
  }
  const width = Number(w);
  const height = Number(h);
  const svg = fs.readFileSync(input, 'utf8');
  if (!/<svg[\s>]/.test(svg)) {
    console.error(`${input} is not an SVG`);
    process.exit(2);
  }
  if (/<text[\s>]/.test(svg)) {
    console.error(`${input} contains <text>; house style allows no text in images`);
    process.exit(1);
  }
  const html = `<!doctype html><html><head><style>
    html,body{margin:0;padding:0;background:#F5F1EA}
    svg{display:block;width:${width}px;height:${height}px}
  </style></head><body>${svg}</body></html>`;

  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width, height } });
    await page.setContent(html, { waitUntil: 'load' });
    fs.mkdirSync(path.dirname(path.resolve(output)), { recursive: true });
    await page.screenshot({ path: output, clip: { x: 0, y: 0, width, height } });
  } finally {
    await browser.close();
  }
  console.log(`saved ${output} (${width}x${height})`);
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
