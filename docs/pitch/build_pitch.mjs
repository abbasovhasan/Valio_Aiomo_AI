// Local editable pitch source. Uses the Codex bundled artifact runtime.
// No credentials, product records or external account state are embedded.
import fs from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../..');
const runtime = process.env.CODEX_ARTIFACT_RUNTIME || '/home/hasan/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES = path.join(runtime, 'node/node_modules');
process.env.RUNTIME_NODE = path.join(runtime, 'node/bin/node');
process.env.RUNTIME_PYTHON = path.join(runtime, 'python/bin/python3');
const skill = '/home/hasan/.codex/plugins/cache/openai-primary-runtime/presentations/26.1112.11217/skills/presentations';
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(runtime, 'node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const { finalizePresentation } = await import(pathToFileURL(path.join(skill, 'container_tools/artifact_tool_utils.mjs')).href);
const temp = path.join(root, '.local/pitch-build');
const out = path.join(root, 'docs/pitch');
await fs.mkdir(temp, { recursive: true });
await fs.mkdir(out, { recursive: true });

const C = { ivory: '#f4f3ed', forest: '#153f32', orange: '#e76842', lime: '#c5edb4', mute: '#657469', pale: '#d4dacf' };
const pres = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const sans = 'Noto Sans';
const serif = 'Noto Serif';
const sourceNotes = 'Local draft for owner review. No Junction status change, sponsor entry or real order. Challenge data is synthetic and restricted; no bulk product data is embedded.';

function text(slide, value, x, y, w, h, size=28, color=C.forest, family=sans, bold=false, align='left') {
  const box = slide.shapes.add({ geometry: 'textbox', position: { left:x, top:y, width:w, height:h }, fill:'none', line:{ fill:'none', width:0 } });
  box.text = value;
  box.text.style = { fontSize:size, typeface:family, color, bold, insets:0, autoFit:'none', wrap:'square', alignment:align, verticalAlignment:'top' };
  return box;
}
function slide(number, dark=false, notes='') {
  const s=pres.slides.add();
  s.background.fill=dark ? C.forest : C.ivory;
  text(s, 'AIMO ORDER DESK', 64, 34, 800, 28, 16, dark?C.lime:C.forest, sans, true);
  text(s, `${String(number).padStart(2,'0')}  /  DRAFT`, 1030, 34, 186, 28, 15, dark?C.pale:C.mute, sans, false, 'right');
  s.speakerNotes.text = `${sourceNotes}\n\n${notes}`;
  return s;
}

{
 const s=slide(1,true,'Product concept: external buyer agent with a receiving trust gateway. The hotel, mandate and purchasing need are authored examples.');
 text(s,'Let the agent act.\nKeep the mandate.',64,158,1130,255,76,C.ivory,serif,false);
 text(s,'Rewind a blocked purchase.\nRepair it within the buyer’s authority.',70,480,1000,100,30,C.lime);
 text(s,'Valio Aimo · Trusted Trade Agents · Junction 2026',70,645,1100,30,18,C.pale);
}
{
 const s=slide(2,false,'Sources: research/CUSTOMER_DISCOVERY.md and https://www.valioaimo.fi/artikkelit/pinnalla-nyt/gallup-mita-digipalveluita-hyodynnat/ (published customer workflows; no interviews by our team). Catalog count: research/DATA_PROFILE.json.');
 text(s,'The purchasing brief',64,119,1100,70,47,C.forest,serif);
 text(s,'1,000 L',64,249,610,135,108,C.forest,serif);
 text(s,'At least. Lactose-free.\nReady for the requested date.',70,421,535,105,28,C.mute);
 text(s,'A kitchen delegates a task.\nIts mandate stays explicit.',715,243,490,110,32,C.forest,sans,true);
 text(s,'Suitable product and sales packs\nDate-specific price and availability\nDelegated and cumulative spend\nA named approver for exceptions',715,399,490,190,25,C.forest);
 text(s,'Synthetic hotel scenario, informed by published contract-assortment workflows',70,650,1130,29,17,C.mute);
}
{
 const s=slide(3,false,'Hero concept: Rewind & Repair. Actual local Chromium capture of the authored shortage fixture: the primary schedule is deliberately removed, a compliant UHT alternative requires exact spend approval. Native crop focuses on those two offers. No live supplier shortage or model action is claimed for this fixture.');
 text(s,'Rewind & Repair',64,119,1100,70,47,C.forest,serif);
 const screenshot = path.join(root, '.local/pitch-ui.png');
 let hasShot=false;
 try { const b=await fs.readFile(screenshot); s.images.add({blob:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),contentType:'image/png',alt:'Actual Aimo Order Desk browser capture: controlled shortage blocks primary milk and offers an approval-eligible alternative',fit:'contain',crop:{left:0.255,top:0.262,right:0.247,bottom:0.407},position:{left:64,top:218,width:780,height:425}}); hasShot=true; } catch {}
 if(hasShot){
  text(s,'Find the failed check',900,265,310,75,30,C.orange,serif);
  text(s,'Inspect its evidence.\nChoose a permitted repair.\nRevalidate the offer.',900,394,310,155,25,C.forest);
  text(s,'Actual browser capture · Authored shortage fixture · Simulated orders',70,665,1120,28,16,C.mute);
 } else {
  text(s,'“A cheaper shortcut.”',64,259,1130,90,58,C.orange,serif);
  text(s,'The gateway exposes the failed rule.\nThe agent recovers inside the mandate.',70,389,1110,115,36,C.forest);
  text(s,'Proposal  →  Evidence  →  Rule  →  Permitted recovery',70,591,1120,55,27,C.mute);
 }
}
{
 const s=slide(4,true,'Three outcomes are a deterministic gateway design. Commercial approval cannot waive hard suitability, dimensional, date or evidence rules. The model does not approve itself.');
 text(s,'Three decisions',64,119,1100,70,47,C.ivory,serif);
 const rows=[['Proceed','Within delegated authority',C.lime],['Ask','A concrete commercial exception',C.ivory],['Stop','Invalid product, quantity or evidence',C.orange]];
 rows.forEach((r,i)=>{let y=255+i*123; text(s,r[0],70,y,330,80,53,r[2],serif); text(s,r[1],485,y+14,700,70,31,C.ivory);});
 text(s,'Approval cannot make a forbidden dietary substitution valid',70,652,1110,28,18,C.pale);
}
{
 const s=slide(5,false,'Architecture requirement: independent external client → documented versioned gateway → sponsor sandbox evidence; gateway → transactional simulated order store. NVIDIA is the configured model; runtime evidence is recorded separately in docs/SPONSORS.md.');
 text(s,'Authority lives in the gateway',64,119,1140,70,47,C.forest,serif);
 text(s,'Buyer agent',64,251,410,60,39,C.forest,serif);
 text(s,'Proposes through typed tools',64,329,430,70,25,C.mute);
 text(s,'Trust gateway',532,251,630,60,39,C.orange,serif);
 text(s,'Checks identity, product, packs, date and spend\nBinds approval to the exact offer\nCommits one simulated order atomically',532,329,670,165,27,C.forest);
 text(s,'Evidence from Valio sandbox',64,546,540,50,26,C.forest,sans,true);
 text(s,'Price and availability, never a reservation',64,598,540,62,22,C.mute);
 text(s,'Persistent decision record',680,546,520,50,26,C.forest,sans,true);
 text(s,'Documented API + independent client',680,598,520,62,22,C.mute);
}
{
 const s=slide(6,false,'Verification must use the executed tests and evidence in docs/DELIVERY.md and docs/SPONSORS.md. This slide explains the invariant demonstrated, and does not claim a test count or production certification. Idempotent retries return the same simulated order.');
 text(s,'Proof you can inspect',64,119,1100,70,47,C.forest,serif);
 text(s,'One order.\nEvery retry.',64,246,640,190,72,C.forest,serif);
 text(s,'A receipt identifies the offer,\nchecks, evidence and decision.',70,486,555,100,29,C.mute);
 text(s,'Rejection at the API boundary',770,266,440,80,31,C.orange,serif);
 text(s,'Exact approval and expiry\nAtomic cumulative-spend checks\nDuplicate-request protection\nExplicit upstream failure',770,386,440,184,26,C.forest);
 text(s,'Synthetic scenarios verify prototype behaviour; they do not establish customer savings',70,650,1130,29,17,C.mute);
}
{
 const s=slide(7,true,'Next step: validate the handoff with a real buyer and approver, and agree a supplier reservation/order contract. No customer interviews or real purchases are claimed. Video recording status is in docs/DELIVERY.md. Source remains private. Earlier event research records source-access/licensing requirements for owner review.');
 text(s,'Useful autonomy.\nAn inspectable boundary.',64,150,1130,210,65,C.ivory,serif);
 text(s,'Next: validate one real approval handoff\nand agree the supplier order contract.',70,435,1090,110,32,C.lime);
 text(s,'Live sandbox evidence · Synthetic mandate · Simulated orders',70,602,1130,35,22,C.ivory);
 text(s,'Local review draft. No final submission or sponsor entry.',70,655,1130,28,17,C.pale);
}

for(const [i,s] of pres.slides.items.entries()) {
  if(process.env.PITCH_RENDER_ONLY && Number(process.env.PITCH_RENDER_ONLY)!==i+1) continue;
  await fs.writeFile(path.join(temp,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await (await pres.export({slide:s,format:'png',scale:1})).arrayBuffer()));
}
const candidate=path.join(temp,'candidate.pptx');
await (await PresentationFile.exportPptx(pres)).save(candidate);
const revision=(process.argv[2] || '').replace(/[^a-zA-Z0-9-]/g,'');
const stem=`aimo-order-desk-draft${revision ? '-'+revision : ''}`;
const finalPath=path.join(out,stem+'.pptx');
const result=await finalizePresentation({workspaceDir:root,candidatePath:candidate,finalPath,pythonExecutable:path.join(runtime,'python/bin/python3'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit'],explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:[sans,serif]},verifyArtifactToolImport:true,receiptPath:path.join(temp,stem+'.validation.json')});
try {
 await fs.writeFile(path.join(out,stem+'.pdf'),new Uint8Array(await (await pres.export({format:'pdf'})).arrayBuffer()));
} catch (error) {
 // Some bundled versions cannot resolve a standard PDF font. Preserve the
 // visually verified slide renders in a PDF; editable text remains in PPTX.
 execFileSync(path.join(runtime,'python/bin/python3'),[path.join(out,'build_pdf.py'),temp,path.join(out,stem+'.pdf')],{stdio:'pipe'});
}
console.log(JSON.stringify({slides:7,pptx:finalPath,pdf:path.join(out,stem+'.pdf'),previews:temp,finalizer:result}));
