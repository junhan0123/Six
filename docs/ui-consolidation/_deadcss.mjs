import fs from 'node:fs';
const dir = 'G:/xiao6/xiao6-ui';
const files = fs.readdirSync(dir);
const consumers = files.filter(f => /\.(js|html)$/.test(f))
  .map(f => fs.readFileSync(dir + '/' + f, 'utf8')).join('\n');
const cssFiles = files.filter(f => /\.css$/.test(f));
const report = {};
for (const cf of cssFiles) {
  const css = fs.readFileSync(dir + '/' + cf, 'utf8');
  const cls = new Set();
  for (const m of css.matchAll(/\.([a-zA-Z][a-zA-Z0-9_-]*)/g)) cls.add(m[1]);
  const dead = [];
  for (const c of cls) {
    if (!consumers.includes(c)) dead.push(c);
  }
  report[cf] = { total: cls.size, dead: dead.length, list: dead };
}
for (const [f, r] of Object.entries(report)) {
  console.log(`${f}: 定义 ${r.total} class / 无字面消费者 ${r.dead}`);
}
console.log('\n=== styles.css 无消费者 ===');
console.log((report['styles.css']?.list || []).join(', '));
console.log('\n=== premium.css 无消费者 ===');
console.log((report['premium.css']?.list || []).join(', '));
console.log('\n=== ui2.css 无消费者 ===');
console.log((report['ui2.css']?.list || []).join(', '));
