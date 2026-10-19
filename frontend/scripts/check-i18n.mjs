// Dictionary check: every English key in src/i18n.ts must exist in Arabic (same shape), no Arabic value
// may be empty, and text functions must take the same arguments. Run: npm run check:i18n
// Node 22.18+ strips TypeScript types natively (older Node: run with --experimental-strip-types).
const target = process.argv[2] ? new URL(`file://${process.argv[2]}`).href : "../src/i18n.ts";
const { dict } = await import(target);

const problems = [];
let keys = 0;
function walk(en, ar, path) {
  for (const [k, v] of Object.entries(en)) {
    const p = path ? `${path}.${k}` : k;
    keys++;
    if (!(k in Object(ar))) {
      problems.push(`missing in ar: ${p}`);
      continue;
    }
    const a = ar[k];
    if (typeof v === "function") {
      if (typeof a !== "function") problems.push(`not a function in ar: ${p}`);
      else if (a.length !== v.length) problems.push(`argument count differs: ${p} (en ${v.length}, ar ${a.length})`);
    } else if (v && typeof v === "object") {
      if (!a || typeof a !== "object") problems.push(`not an object in ar: ${p}`);
      else walk(v, a, p);
    } else if (typeof v === "string" && v.trim() && typeof a === "string" && !a.trim()) {
      problems.push(`empty in ar: ${p}`);
    }
  }
  for (const k of Object.keys(Object(ar))) if (!(k in Object(en))) problems.push(`extra key only in ar: ${path ? `${path}.` : ""}${k}`);
}
walk(dict.en, dict.ar, "");
if (problems.length) {
  console.error(`i18n check FAILED (${problems.length}):\n  ${problems.join("\n  ")}`);
  process.exit(1);
}
console.log(`i18n check OK: ${keys} keys, English and Arabic match.`);
