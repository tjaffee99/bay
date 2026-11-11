// SOURCES.md -> public/sources.html: the page behind the "Sources" link of the attribution
// line, shipped with the site (the link used to point at a GitHub branch that does not
// exist). Run by `npm run dev` and `npm run build`.
import {readFileSync, writeFileSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {marked} from 'marked';

const here = dirname(fileURLToPath(import.meta.url));
const md = readFileSync(join(here, '..', '..', 'SOURCES.md'), 'utf8');
const slug = s =>
  s
    .toLowerCase()
    .replace(/<[^>]+>/g, '')
    .replace(/&[a-z]+;/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
const seen = new Map();
const renderer = new marked.Renderer();
renderer.heading = function ({tokens, depth}) {
  const html = this.parser.parseInline(tokens);
  let id = slug(html) || 'section';
  const n = seen.get(id) ?? 0;
  seen.set(id, n + 1);
  if (n) id += '-' + n;
  return `<h${depth} id="${id}">${html}</h${depth}>\n`;
};
renderer.link = function ({href, title, tokens}) {
  const text = this.parser.parseInline(tokens);
  const ext = /^https?:/.test(href);
  return `<a href="${href}"${title ? ` title="${title}"` : ''}${ext ? ' target="_blank" rel="noopener"' : ''}>${text}</a>`;
};
const body = marked.parse(md, {gfm: true, renderer});
const html = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sources — Bay Area Through Time</title>
<style>
  :root { color-scheme: light; }
  body { margin: 0; background: #f3ecdd; color: #2b2620; font: 17px/1.55 'EB Garamond', Georgia, 'Times New Roman', serif; }
  main { max-width: 860px; margin: 0 auto; padding: 28px 16px 80px; overflow-wrap: anywhere; }
  .back { font-size: 15px; }
  h1 { font: 600 38px/1.15 'Cormorant Garamond', Georgia, serif; margin: 18px 0 14px; }
  h2 { font: 600 27px/1.2 'Cormorant Garamond', Georgia, serif; margin: 40px 0 10px; padding-top: 14px; border-top: 1px solid #d5c9b0; }
  h3 { font-size: 19px; margin: 26px 0 6px; }
  a { color: #7a3b1d; }
  code { font: 13.5px/1.4 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; background: #e9dfc9; padding: 1px 4px; border-radius: 3px; }
  pre { background: #e9dfc9; padding: 10px 12px; border-radius: 4px; overflow-x: auto; }
  pre code { background: none; padding: 0; }
  ul, ol { padding-left: 22px; }
  li { margin: 3px 0; }
  .tablewrap { overflow-x: auto; }
  table { border-collapse: collapse; font-size: 15px; margin: 12px 0; }
  th, td { border: 1px solid #d5c9b0; padding: 4px 8px; vertical-align: top; text-align: left; }
  th { background: #e9dfc9; }
  blockquote { margin: 12px 0; padding: 2px 14px; border-left: 3px solid #cbbd9f; color: #55493a; }
</style>
</head>
<body>
<main>
<p class="back"><a href="./">&larr; Bay Area Through Time</a></p>
${body.replace(/<table>/g, '<div class="tablewrap"><table>').replace(/<\/table>/g, '</table></div>')}
</main>
</body>
</html>
`;
const out = join(here, '..', 'public', 'sources.html');
writeFileSync(out, html);
console.log(`sources.html: ${(html.length / 1024).toFixed(0)} kB from SOURCES.md (${md.split('\n').length} lines)`);
