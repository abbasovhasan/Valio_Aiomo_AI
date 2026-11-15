// Actual component handlers with isolated hooks and authored API replies.
// This verifies edits/transfer control, not browser layout or supplier accuracy.
const fs = require('fs'), path = require('path'), vm = require('vm');
const root = path.resolve(__dirname, '../..');
const req = require('module').createRequire(path.join(root, 'frontend/package.json'));
const React = req('react'), ts = req('typescript');
const assert = (value, message) => { if (!value) throw Error(message); };
const slots = []; let cursor = 0, uid = 0;
const hooks = { ...React, useState(initial) {
  const index = cursor++;
  if (!(index in slots)) slots[index] = typeof initial === 'function' ? initial() : initial;
  return [slots[index], value => { slots[index] = typeof value === 'function' ? value(slots[index]) : value; }];
} };
function compile(file, modules = {}) {
  const code = ts.transpileModule(fs.readFileSync(path.join(root, 'frontend/src', file), 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, require: id => modules[id] || (id.endsWith('.css') ? {} : req(id)), Intl, Date, Blob, URL, crypto: { randomUUID: () => `authored-${++uid}` } });
  return module.exports;
}
const presentation = compile('productPresentation.ts');
const { MealPlanner } = compile('MealPlanner.tsx', { react: hooks, './productPresentation': presentation, './api': { sessionInterrupted: error => error.name === 'AbortError' } });
const requests = [], handoffs = [], checks = []; let accepted = false, planSequence = 0, dietaryConflict = false;
function response(body) {
  return { id: `authored-meal-${++planSequence}`, dish: body.meal_name, ingredients: body.ingredients,
    verified_recipe: false, recipe_provenance: 'customer_entered_unverified', recipe_note: 'Customer-entered quantities; not a verified recipe.',
    cohorts: { meat_standard: body.servings, meat_gluten_free: 0, vegetarian_standard: 0, vegetarian_gluten_free: 0 }, dietary_restrictions: body.dietary_restrictions,
    lines: body.ingredients.map(item => ({ id: item.id + '-shared', ingredient_id: item.id, ingredient: item.label,
      search_query: item.query, grams_per_serving: item.grams_per_serving, required_kg: '5', servings: body.servings, dietary: body.dietary_restrictions,
      candidates: [{ product_id: `sku-${item.query}`, name: `Authored ${item.query}`, sales_unit: 'ST', kg_per_sales_unit: '2', quantity_sales_units: '3', effective_kg: '6', issues: dietaryConflict ? ['Gluten-free evidence is missing.'] : [] }] })),
  };
}
const props = { role: 'buyer', onSignIn() {}, onBeforeQuote: async () => accepted, onQuoteSession: id => handoffs.push(id), api: async (url, options) => {
  const body = JSON.parse(options.body); requests.push({ url, body });
  return url === '/meal-plans' ? response(body) : { id: 'authored-cart' };
} };
function nodes(node, result = []) {
  if (Array.isArray(node)) { node.forEach(child => nodes(child, result)); return result; }
  if (node && typeof node === 'object' && node.props) { result.push(node); nodes(node.props.children, result); }
  return result;
}
function render() { cursor = 0; return nodes(MealPlanner(props)); }
const text = node => typeof node === 'string' || typeof node === 'number' ? String(node) : Array.isArray(node) ? node.map(text).join('') : node?.props ? text(node.props.children) : '';
function get(predicate) { const node = render().find(predicate); assert(node, 'Expected component control not found'); return node; }
const input = name => get(node => node.type === 'input' && node.props['aria-label'] === name);
const button = name => get(node => node.type === 'button' && text(node) === name);
const flush = () => new Promise(resolve => setImmediate(resolve));
async function calculate() { get(node => node.type === 'form' && node.props.className === 'paper meal-config').props.onSubmit({ preventDefault() {} }); await flush(); }

(async () => {
  let tree = render();
  assert(input('Meal name').props.value === 'Spaghetti bolognese' && input('Number of servings').props.value === '50', 'Basic inputs missing');
  assert(tree.filter(node => node.type === 'details' && node.props.className === 'meal-settings').every(node => !node.props.open), 'Optional fields overwhelm initial form');
  assert(!tree.some(node => node.props.className === 'paper meal-editor'), 'Ingredient editor should appear progressively');
  checks.push('Initial meal and servings with optional settings collapsed');
  input('Meal name').props.onChange({ target: { value: 'Vegetable soup' } }); await calculate();
  assert(requests.length === 0 && render().some(node => text(node).includes('No recipe is supplied for this dish.')), 'Unknown meal invented a template');
  button('Add ingredient').props.onClick();
  input('Ingredient name').props.onChange({ target: { value: 'carrot' } });
  input('Grams per serving for carrot').props.onChange({ target: { value: '125' } });
  await calculate();
  assert(requests[0].body.template === 'custom' && requests[0].body.recipe_source === 'customer', 'Custom source lost');
  assert(requests[0].body.ingredients[0].grams_per_serving === '125' && requests[0].body.meal_name === 'Vegetable soup', 'Kitchen quantities changed');
  checks.push('Another meal requires explicit ingredients and sends exact user quantities');
  get(node => node.type === 'input' && node.props.type === 'radio').props.onChange();
  input('Number of servings').props.onChange({ target: { value: '60' } });
  assert(button('Add ingredients to cart').props.disabled, 'Changed servings permit a stale transfer');
  assert(!get(node => node.type === 'input' && node.props.type === 'radio').props.checked && render().some(node => node.type === 'summary' && text(node).includes('Recalculate to check product suitability')), 'Dirty requirements still present a compliant selected product');
  await calculate();
  assert(requests.at(-1).body.servings === 60 && get(node => node.type === 'input' && node.props.type === 'radio').props.checked, 'Recalculation discarded valid exact selection');
  checks.push('Serving changes require recalculation and preserve matching selected SKU by stable line ID');
  button('Add ingredient').props.onClick();
  input('Ingredient name').props.onChange({ target: { value: 'onion' } });
  input('Grams per serving for onion').props.onChange({ target: { value: '30' } });
  await calculate();
  assert(requests.at(-1).body.ingredients.length === 2, 'Ingredient addition lost');
  get(node => node.type === 'button' && node.props['aria-label'] === 'Remove onion').props.onClick();
  input('Ingredient carrot').props.onChange({ target: { value: 'potato' } });
  input('Grams per serving for potato').props.onChange({ target: { value: '150.25' } });
  await calculate();
  assert(requests.at(-1).body.ingredients.length === 1 && requests.at(-1).body.ingredients[0].query === 'potato', 'Remove/replace was overwritten by old template');
  assert(!get(node => node.type === 'input' && node.props.type === 'radio').props.checked, 'Replaced ingredient inherited unrelated SKU');
  checks.push('Add/remove/replace edits survive recalculation and unrelated choice is cleared');
  get(node => node.type === 'input' && node.props.type === 'radio').props.onChange();
  input('Meal plan delivery date').props.onChange({ target: { value: '2026-11-17' } });
  input('Meal plan maximum budget').props.onChange({ target: { value: '200.10' } });
  let transfer = get(node => node.type === 'form' && node.props.className === 'paper meal-transfer');
  const before = requests.length;
  await transfer.props.onSubmit({ preventDefault() {} });
  assert(requests.length === before && handoffs.length === 0, 'Declined existing-cart confirmation still wrote a cart');
  accepted = true; transfer = get(node => node.type === 'form' && node.props.className === 'paper meal-transfer');
  await transfer.props.onSubmit({ preventDefault() {} });
  const quote = requests.at(-1);
  assert(quote.url === '/procurement/sessions/from-meal-plan' && quote.body.date === '2026-11-17' && quote.body.budget === '200.10', 'Transfer lost exact constraints');
  assert(quote.body.selections['0'] === 'sku-potato' && handoffs[0] === 'authored-cart', 'Transfer lost explicit current selection');
  checks.push('Existing-cart guard runs before POST; accepted transfer keeps exact selections/date/budget');
  assert(!input('Meal plan delivery date').props.required, 'Optional planner deadline became mandatory');
  assert(!render().some(node => node.props.className?.includes('compare')), 'Comparison leaked into Meal Planner');
  checks.push('Optional deadline and planning-only UI preserve intended scope');
  dietaryConflict = true;
  await calculate();
  let conflicted = get(node => node.type === 'input' && node.props.type === 'radio');
  assert(conflicted.props.disabled && !conflicted.props.checked, 'A retained SKU with missing mandatory evidence still appears selected');
  conflicted.props.onChange();
  assert(!get(node => node.type === 'input' && node.props.type === 'radio').props.checked, 'Calling a blocked choice handler bypassed evidence checks');
  assert(render().some(node => node.type === 'summary' && text(node).includes('No verified suitable product selected')), 'Unresolved dietary selection is not explicit');
  await get(node => node.type === 'form' && node.props.className === 'paper meal-transfer').props.onSubmit({ preventDefault() {} });
  assert(Object.keys(requests.at(-1).body.selections).length === 0, 'Unsafe retained selection was sent into the basket');
  checks.push('Missing gluten-free evidence clears an existing choice, blocks its radio and transfer, and remains visibly unresolved');
  const report = { scope: 'Actual MealPlanner handlers with isolated React hooks and authored API replies; no browser/layout/provider proof', checks_passed: checks.length, checks };
  fs.mkdirSync(path.join(root, '.local'), { recursive: true });
  fs.writeFileSync(path.join(root, '.local/meal-planner-report.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
