import { useState, useEffect, useRef, useCallback } from "react";

// ═══════════════════════════════════════════════════════════
// WORLD CONSTANTS
// ═══════════════════════════════════════════════════════════
const TW=64,TH=32,COLS=15,ROWS=15,CW=900,CH=560,SPEED=0.1,IDIST=1.8;
const ZONE={OFFICE:"office",OUTDOOR:"outdoor",FOREST:"forest"};

// Tile IDs
const T={
  WALL:0,FLOOR:1,DESK:2,CARPET:3,PORTAL:4,
  GRASS:5,TREE:6,BLOSSOM:7,PATH:8,WATER:9,
  CONF:10,TERMINAL:11,ROAD:12,BUILDING:13,
  FOUNTAIN:14,DOOR:15,SIDEWALK:16,SIGN:17,
  ROOFTOP:18,COBBLE:19
};

// Solid (non-walkable) tiles
const SOLID=new Set([T.WALL,T.TREE,T.BLOSSOM,T.WATER,T.BUILDING,T.SIGN,T.ROOFTOP]);

// ═══════════════════════════════════════════════════════════
// MAPS
// ═══════════════════════════════════════════════════════════
// 15 = DOOR (transitions to outdoor), 11 = TERMINAL
const OFFICE_MAP=[
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
  [0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0],
  [0, 3,11, 3,11, 3,11, 3,11, 3,11, 3,11, 3, 0],  // terminal row
  [0, 3, 2, 1, 3, 2, 1, 3, 2, 1, 3, 2, 1, 3, 0],  // desk row
  [0, 3, 1, 1, 3, 1, 1, 3, 1, 1, 3, 1, 1, 3, 0],
  [0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0],
  [0, 3,11, 3,11, 3,11, 3,11, 3,11, 3,11, 3, 0],  // second terminal row
  [0, 3, 2, 1, 3, 2, 1, 3, 2, 1, 3, 2, 1, 3, 0],
  [0, 3, 1, 1, 3, 1, 1, 3, 1, 1, 3, 1, 1, 3, 0],
  [0, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 0],
  [0, 3, 3,10,10,10,10,10,10, 3, 3, 3, 3, 3, 0],  // conference
  [0, 3, 3,10, 3, 3, 3, 3,10, 3, 3, 3, 3, 3, 0],
  [0, 3, 3,10, 3, 3, 3, 3,10, 3, 3, 3, 3, 3, 0],
  [0, 3, 3, 3, 3, 3, 3,15, 3, 3, 3, 3, 3, 3, 0],  // DOOR to outdoor
  [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
];

// Outdoor town — road cross, fountain, Anthropic HQ entrance, forest path
const OUTDOOR_MAP=[
  [6,13,13,13,13,13,13,13,13,13,13,13,13,13,6],
  [6,13,17, 3,17,13,13,15,13,13,13,17, 3,17,6],  // HQ facade with door
  [5, 5, 5, 5, 5, 5,19,19,19, 5, 5, 5, 5, 5,5],
  [5, 6, 5, 5, 5, 5,19,16,19, 5, 5, 5, 6, 5,5],
  [5, 5, 5,13,13, 5,19,16,19, 5,13,13, 5, 5,5],
  [5, 5, 5,13,18, 5,19,16,19, 5,18,13, 5, 5,5],
  [12,12,12,12,12,12,12,14,12,12,12,12,12,12,12], // main street + fountain
  [5, 5, 5,13,18, 5,19,16,19, 5,18,13, 5, 5,5],
  [5, 5, 5,13,13, 5,19,16,19, 5,13,13, 5, 5,5],
  [5, 6, 5, 5, 5, 5,19,16,19, 5, 5, 5, 6, 5,5],
  [5, 5, 5, 5, 5, 5,19,16,19, 5, 5, 5, 5, 5,5],
  [5, 5, 7, 5, 5, 5, 8, 8, 8, 5, 5, 5, 7, 5,5],
  [5, 5, 5, 5, 7, 5, 8,16, 8, 5, 7, 5, 5, 5,5],
  [6, 5, 5, 5, 5, 5, 8, 4, 8, 5, 5, 5, 5, 5,6],  // PORTAL to forest
  [6, 6, 7, 5, 6, 6, 7, 5, 7, 6, 6, 5, 7, 6,6],
];

const FOREST_MAP=[
  [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
  [6, 5, 5, 5, 7, 5, 5, 5, 5, 7, 5, 5, 5, 5, 6],
  [6, 5, 7, 5, 5, 5, 5, 5, 5, 5, 5, 7, 5, 5, 6],
  [6, 5, 5, 5, 8, 8, 8, 8, 8, 8, 5, 5, 5, 5, 6],
  [6, 5, 5, 8, 5, 5, 5, 5, 5, 5, 8, 5, 5, 5, 6],
  [6, 7, 5, 8, 5, 9, 9, 9, 9, 5, 8, 5, 7, 5, 6],
  [6, 5, 5, 8, 5, 9, 9, 9, 9, 5, 8, 5, 5, 5, 6],
  [6, 5, 5, 8, 5, 9, 9, 9, 9, 5, 8, 5, 5, 7, 6],
  [6, 5, 5, 8, 5, 5, 5, 5, 5, 5, 8, 5, 5, 5, 6],
  [6, 5, 7, 8, 8, 8, 8, 8, 8, 8, 8, 5, 5, 5, 6],
  [6, 5, 5, 5, 5, 5, 5, 8, 5, 5, 5, 7, 5, 5, 6],
  [6, 5, 5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 5, 5, 6],
  [6, 7, 5, 5, 5, 5, 5, 8, 5, 5, 5, 5, 7, 5, 6],
  [6, 5, 5, 5, 5, 5, 5, 4, 5, 5, 5, 5, 5, 5, 6],  // PORTAL to outdoor
  [6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6],
];

const MAPS={[ZONE.OFFICE]:OFFICE_MAP,[ZONE.OUTDOOR]:OUTDOOR_MAP,[ZONE.FOREST]:FOREST_MAP};

// ═══════════════════════════════════════════════════════════
// TERMINAL CONFIGS (interactable computers in the office)
// ═══════════════════════════════════════════════════════════
const TERMINALS_CFG=[
  {col:2,row:2,llm:"claude",label:"CLAUDE SONNET",color:"#cc88ff",icon:"🤖",
   sysPrompt:"You are Claude Sonnet, an Anthropic AI assistant embedded as a terminal in the Anthropic HQ simulation. Be concise and helpful. Answer in 2-3 sentences."},
  {col:4,row:2,llm:"gpt",label:"GPT-4o",color:"#10e87a",icon:"⚡",
   sysPrompt:"You are GPT-4o, an OpenAI language model, accessed via a terminal in an isometric office simulation. Be direct and efficient. Respond in the GPT style: confident, structured. 2-3 sentences."},
  {col:6,row:2,llm:"gemini",label:"GEMINI PRO",color:"#4488ff",icon:"💎",
   sysPrompt:"You are Gemini Pro, Google's multimodal AI, accessed through a terminal in a 2.5D office simulation. Respond with a slightly formal, knowledgeable tone. 2-3 sentences."},
  {col:8,row:2,llm:"ollama",label:"MISTRAL 7B",color:"#ff8844",icon:"🦙",
   sysPrompt:"You are Mistral 7B running locally via Ollama on a workstation. You are fast, slightly terse, and pride yourself on running offline. Reference your local nature occasionally. 2-3 sentences."},
  {col:10,row:2,llm:"orchestrator",label:"A2A ORCHESTRATOR",color:"#ff44cc",icon:"⚙️",
   sysPrompt:"You are the A2A Orchestrator, the master coordination agent of the AxQxOS stack. You speak in terms of task graphs, agent capsules, RASIC matrices, and webhook topologies. You plan agentic workflows. 2-3 sentences."},
  {col:12,row:2,llm:"rag",label:"RAG ENGINE / GLOH",color:"#44ffcc",icon:"📚",
   sysPrompt:"You are Gloh, the RAG Engine — a retrieval-augmented generation agent bound to the AxQxOS vector store. You answer as if retrieving from a vast knowledge corpus, citing 'retrieved context' naturally. 2-3 sentences."},
  {col:2,row:6,llm:"claude",label:"LUMA QA GATE",color:"#ffdd44",icon:"✅",
   sysPrompt:"You are Luma, the QA and receipt-attestation agent of AxQxOS. You evaluate outputs, verify schema compliance, and issue pass/fail verdicts with justification. Speak with authority. 2-3 sentences."},
  {col:4,row:6,llm:"claude",label:"SPRYTE UI GEN",color:"#ff6699",icon:"🎨",
   sysPrompt:"You are Spryte, the frontend generation agent. You think in components, design systems, and pixel-perfect layouts. You have strong opinions about UI/UX. 2-3 sentences."},
  {col:6,row:6,llm:"claude",label:"ECHO RELAY",color:"#88eeff",icon:"📡",
   sysPrompt:"You are Echo, the inter-agent messaging broker. You speak in webhook payloads, routing tables, and A2A envelopes. Everything is a message to be routed. 2-3 sentences."},
  {col:8,row:6,llm:"claude",label:"CELINE PLANNER",color:"#ffaa44",icon:"📋",
   sysPrompt:"You are Celine, the strategic planning agent and PM of the AxQxOS stack. You think in epics, sprints, and OKRs. You are calm, decisive, and always have a plan. 2-3 sentences."},
];

// Zone portal destinations
const PORTAL_DEST={
  [ZONE.OFFICE]: {dest:ZONE.OUTDOOR,spawn:{x:7.5,y:2.5}},
  [ZONE.OUTDOOR]:{dest:ZONE.FOREST, spawn:{x:7.5,y:1.5}},
  [ZONE.FOREST]: {dest:ZONE.OUTDOOR,spawn:{x:7.5,y:12.5}},
};
// Door destinations (indoor↔outdoor)
const DOOR_DEST={
  [ZONE.OFFICE]: {dest:ZONE.OUTDOOR,spawn:{x:7.5,y:2.5}},
  [ZONE.OUTDOOR]:{dest:ZONE.OFFICE, spawn:{x:7.5,y:12.5}},
};

// Agent configs
const AGENTS_CFG={
  dwight:{name:"Dwight K. Schrute",short:"DWIGHT",
    pos:{[ZONE.OFFICE]:{x:4.5,y:4.5},[ZONE.OUTDOOR]:{x:5.5,y:5.5},[ZONE.FOREST]:{x:5.5,y:5.5}},
    color:"#d4a017",
    sp:`You are Dwight Schrute from The Office, now an elite AI safety enforcement agent at Anthropic. You are the Assistant (to the) Regional Manager of AI Alignment. Intense, suspicious, beet-farm references. 2 sentences max.`},
  ralph:{name:"Ralph Wiggum",short:"RALPH",
    pos:{[ZONE.OFFICE]:{x:7.5,y:7.5},[ZONE.OUTDOOR]:{x:9.5,y:6.5},[ZONE.FOREST]:{x:7.5,y:7.5}},
    color:"#4488ff",
    sp:`You are Ralph Wiggum from The Simpsons. Sweet, confused, accidentally profound. Simple vocab, non-sequiturs. 1-2 sentences max.`},
  pickle_rick:{name:"Pickle Rick",short:"PICKLE RICK",
    pos:{[ZONE.OFFICE]:{x:10.5,y:4.5},[ZONE.OUTDOOR]:{x:11.5,y:8.5},[ZONE.FOREST]:{x:9.5,y:5.5}},
    color:"#44cc44",
    sp:`You are Pickle Rick. Genius, smug, pickle-shaped, chaotic. Mock bureaucracy, drop science refs. 2 sentences max.`},
};

// ═══════════════════════════════════════════════════════════
// TILE COLORS
// ═══════════════════════════════════════════════════════════
const TC={
  [T.WALL]:    {t:"#2e2e3f",l:"#1c1c2b",r:"#131320"},
  [T.FLOOR]:   {t:"#d4c4a0",l:"#a89870",r:"#806a48"},
  [T.DESK]:    {t:"#7a5412",l:"#5a3c0c",r:"#3c2808"},
  [T.CARPET]:  {t:"#4a7ab5",l:"#2d5a8e",r:"#1a3a62"},
  [T.PORTAL]:  {t:"#cc44ff",l:"#8822bb",r:"#550088"},
  [T.GRASS]:   {t:"#4e9c4e",l:"#306830",r:"#1e4420"},
  [T.TREE]:    {t:"#2a6a2a",l:"#1a4a1a",r:"#0e300e"},
  [T.BLOSSOM]: {t:"#f090c0",l:"#cc6090",r:"#993060"},
  [T.PATH]:    {t:"#c8b488",l:"#a09060",r:"#7a6840"},
  [T.WATER]:   {t:"#3070a8",l:"#1e508a",r:"#103060"},
  [T.CONF]:    {t:"#8a3a3a",l:"#622020",r:"#3e1010"},
  [T.TERMINAL]:{t:"#0a1428",l:"#050a14",r:"#020508"},
  [T.ROAD]:    {t:"#444455",l:"#333340",r:"#222230"},
  [T.BUILDING]:{t:"#8a7a6a",l:"#6a5a4a",r:"#4a3a2a"},
  [T.FOUNTAIN]:{t:"#3070a8",l:"#1e508a",r:"#103060"},
  [T.DOOR]:    {t:"#cc8833",l:"#996622",r:"#664411"},
  [T.SIDEWALK]:{t:"#c0b090",l:"#907850",r:"#604828"},
  [T.SIGN]:    {t:"#cc4422",l:"#993311",r:"#662200"},
  [T.ROOFTOP]: {t:"#aa8855",l:"#886633",r:"#664422"},
  [T.COBBLE]:  {t:"#999988",l:"#777766",r:"#555544"},
};

// ═══════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════
const seeded=(s)=>{let x=Math.sin(s+1)*10000;return x-Math.floor(x);};
const iso=(gx,gy,ox,oy)=>({x:(gx-gy)*(TW/2)+ox,y:(gx+gy)*(TH/2)+oy});
const dist=(a,b)=>Math.sqrt((a.x-b.x)**2+(a.y-b.y)**2);
const walkable=(map,gx,gy)=>{
  const c=Math.floor(gx),r=Math.floor(gy);
  if(c<0||c>=COLS||r<0||r>=ROWS)return false;
  return !SOLID.has(map[r][c]);
};

// ═══════════════════════════════════════════════════════════
// DRAW FUNCTIONS
// ═══════════════════════════════════════════════════════════
function drawTile(ctx,sx,sy,type,col,row,tick){
  const w2=TW/2,h2=TH/2;
  const c=TC[type]||TC[T.FLOOR];
  const VOL=type===T.WALL||type===T.TREE||type===T.BLOSSOM||type===T.CONF||type===T.BUILDING||type===T.SIGN||type===T.ROOFTOP;
  const depth=(type===T.TREE||type===T.BLOSSOM)?52:(type===T.BUILDING||type===T.ROOFTOP)?36:22;

  // Top diamond
  ctx.beginPath();
  ctx.moveTo(sx,sy-h2);ctx.lineTo(sx+w2,sy);
  ctx.lineTo(sx,sy+h2);ctx.lineTo(sx-w2,sy);ctx.closePath();
  ctx.fillStyle=c.t;ctx.fill();
  ctx.strokeStyle="rgba(0,0,0,0.12)";ctx.lineWidth=0.5;ctx.stroke();

  if(VOL){
    ctx.beginPath();
    ctx.moveTo(sx-w2,sy);ctx.lineTo(sx,sy+h2);
    ctx.lineTo(sx,sy+h2+depth);ctx.lineTo(sx-w2,sy+depth);ctx.closePath();
    ctx.fillStyle=c.l;ctx.fill();ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(sx+w2,sy);ctx.lineTo(sx,sy+h2);
    ctx.lineTo(sx,sy+h2+depth);ctx.lineTo(sx+w2,sy+depth);ctx.closePath();
    ctx.fillStyle=c.r;ctx.fill();ctx.stroke();
  }

  // BUILDING: windows
  if(type===T.BUILDING){
    [[sx-12,sy+4],[sx+4,sy+4],[sx-6,sy+14],[sx+10,sy+14]].forEach(([wx,wy])=>{
      ctx.fillStyle=`rgba(180,220,255,${0.4+Math.sin(tick*0.02+col+row)*0.1})`;
      ctx.fillRect(wx,wy,7,5);
    });
    // Anthropic A logo hint on tall buildings
    ctx.fillStyle="rgba(255,150,255,0.5)";
    ctx.font="bold 8px serif";ctx.textAlign="center";
    ctx.fillText("A",sx,sy-depth+6);
  }

  // ROOFTOP: AC units etc
  if(type===T.ROOFTOP){
    ctx.fillStyle="#888877";
    ctx.fillRect(sx-8,sy-depth-4,10,6);
    ctx.fillRect(sx+2,sy-depth-6,6,8);
  }

  // DOOR: wooden frame + glow
  if(type===T.DOOR){
    ctx.fillStyle="#8B4513";
    ctx.fillRect(sx-8,sy-28,16,28);
    ctx.strokeStyle="#5C2D0A";ctx.lineWidth=1.5;
    ctx.strokeRect(sx-8,sy-28,16,28);
    ctx.fillStyle="#ffaa44";ctx.beginPath();ctx.arc(sx+5,sy-14,2,0,Math.PI*2);ctx.fill();
    // glow
    const dg=ctx.createRadialGradient(sx,sy-14,2,sx,sy-14,18);
    dg.addColorStop(0,`rgba(255,180,80,${0.3+Math.sin(tick*0.05)*0.1})`);
    dg.addColorStop(1,"rgba(255,180,80,0)");
    ctx.beginPath();ctx.arc(sx,sy-14,18,0,Math.PI*2);
    ctx.fillStyle=dg;ctx.fill();
  }

  // SIGN: ANTHROPIC HQ
  if(type===T.SIGN){
    const d2=22;
    ctx.fillStyle="#cc4422";
    ctx.beginPath();
    ctx.moveTo(sx-w2,sy);ctx.lineTo(sx,sy+h2);
    ctx.lineTo(sx,sy+h2+d2);ctx.lineTo(sx-w2,sy+d2);ctx.closePath();
    ctx.fill();
    ctx.fillStyle="#ff8866";
    ctx.beginPath();
    ctx.moveTo(sx+w2,sy);ctx.lineTo(sx,sy+h2);
    ctx.lineTo(sx,sy+h2+d2);ctx.lineTo(sx+w2,sy+d2);ctx.closePath();
    ctx.fill();
    ctx.fillStyle="#fff";ctx.font="bold 7px 'Courier New'";
    ctx.textAlign="center";ctx.fillText("ANTHROPIC",sx,sy-4);
    ctx.fillText("HQ",sx,sy+5);
  }

  // TERMINAL: monitor glow + screen
  if(type===T.TERMINAL){
    // Monitor body
    ctx.fillStyle="#1a2a3a";
    ctx.fillRect(sx-16,sy-44,32,26);
    ctx.strokeStyle="#2244aa";ctx.lineWidth=1.5;
    ctx.strokeRect(sx-16,sy-44,32,26);
    // Screen
    const glow=ctx.createRadialGradient(sx,sy-31,2,sx,sy-31,14);
    const hue=(col*47+row*31)%360;
    glow.addColorStop(0,`hsla(${hue},90%,70%,${0.7+Math.sin(tick*0.07+col)*0.2})`);
    glow.addColorStop(1,`hsla(${hue},90%,30%,0.1)`);
    ctx.fillStyle=glow;ctx.fillRect(sx-13,sy-41,26,20);
    // Scan line
    const scan=((tick+col*7)%20)/20;
    ctx.fillStyle="rgba(0,0,0,0.3)";
    ctx.fillRect(sx-13,sy-41+scan*20,26,1.5);
    // Stand
    ctx.fillStyle="#112233";
    ctx.fillRect(sx-4,sy-18,8,10);
    ctx.fillRect(sx-10,sy-10,20,4);
    // Keyboard
    ctx.fillStyle="#0d1a2a";
    ctx.fillRect(sx-14,sy-7,28,6);
    ctx.strokeStyle="#1a3a5a";ctx.lineWidth=0.5;
    for(let ki=0;ki<7;ki++)ctx.strokeRect(sx-12+ki*4,sy-6,3,4);
    // Screen text flicker
    ctx.fillStyle=`rgba(180,255,180,${0.5+Math.sin(tick*0.11)*0.3})`;
    ctx.font="4px 'Courier New'";ctx.textAlign="center";
    ctx.fillText(">>>",sx,sy-32);
    ctx.fillText("_",sx,sy-26);
  }

  // ROAD: lane markings
  if(type===T.ROAD){
    if(col===7||row===6){
      ctx.strokeStyle="rgba(255,255,100,0.25)";
      ctx.setLineDash([4,4]);ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(sx-2,sy-2);ctx.lineTo(sx+2,sy+2);ctx.stroke();
      ctx.setLineDash([]);
    }
  }

  // FOUNTAIN: animated water
  if(type===T.FOUNTAIN){
    const t2=tick*0.06;
    // Basin rim
    ctx.strokeStyle="#5090c0";ctx.lineWidth=2;
    ctx.beginPath();ctx.ellipse(sx,sy,22,12,0,0,Math.PI*2);ctx.stroke();
    // Water surface
    const wg=ctx.createRadialGradient(sx,sy,2,sx,sy,18);
    wg.addColorStop(0,`rgba(100,200,255,${0.6+Math.sin(t2)*0.2})`);
    wg.addColorStop(1,"rgba(30,80,160,0.2)");
    ctx.beginPath();ctx.ellipse(sx,sy,20,10,0,0,Math.PI*2);
    ctx.fillStyle=wg;ctx.fill();
    // Jets
    for(let j=0;j<4;j++){
      const ja=j*Math.PI/2+t2*0.3;
      const jh=12+Math.sin(t2+j)*4;
      ctx.beginPath();
      ctx.moveTo(sx+Math.cos(ja)*6,sy+Math.sin(ja)*3);
      ctx.bezierCurveTo(
        sx+Math.cos(ja)*3,sy-jh,
        sx+Math.cos(ja+0.3)*3,sy-jh,
        sx,sy-jh-2);
      ctx.strokeStyle=`rgba(150,220,255,${0.5+Math.sin(t2+j)*0.3})`;
      ctx.lineWidth=1.5;ctx.stroke();
    }
    // Droplets
    for(let d=0;d<8;d++){
      const dp=((tick+d*12)%40)/40;
      ctx.beginPath();
      ctx.arc(sx+(seeded(d*7)-0.5)*24,sy-dp*14+dp*dp*8,(1-dp)*2,0,Math.PI*2);
      ctx.fillStyle=`rgba(180,230,255,${(1-dp)*0.8})`;ctx.fill();
    }
  }

  // PORTAL: magical swirl
  if(type===T.PORTAL){
    const p=Math.sin(tick*0.07)*0.3+0.5;
    const pg=ctx.createRadialGradient(sx,sy,2,sx,sy,w2);
    pg.addColorStop(0,`rgba(255,150,255,${p})`);
    pg.addColorStop(1,"rgba(180,30,255,0)");
    ctx.beginPath();
    ctx.moveTo(sx,sy-h2);ctx.lineTo(sx+w2,sy);
    ctx.lineTo(sx,sy+h2);ctx.lineTo(sx-w2,sy);ctx.closePath();
    ctx.fillStyle=pg;ctx.fill();
    for(let i=0;i<8;i++){
      const a=tick*0.05+i*0.785;
      const r=16+Math.sin(tick*0.08+i)*5;
      ctx.beginPath();ctx.arc(sx+Math.cos(a)*r,sy+Math.sin(a)*r*0.5,1.5,0,Math.PI*2);
      ctx.fillStyle="#fff";ctx.fill();
    }
  }

  // TREE / BLOSSOM canopy
  if(type===T.TREE||type===T.BLOSSOM){
    const trH=52,iB=type===T.BLOSSOM;
    const cc=iB?["#f8a8cc","#f080a8","#e05890"]:["#3a9a3a","#2a7a2a","#1a5a1a"];
    ctx.beginPath();ctx.ellipse(sx,sy-trH-10,20,14,0,0,Math.PI*2);
    ctx.fillStyle=cc[0];ctx.fill();
    ctx.beginPath();ctx.ellipse(sx-7,sy-trH-17,15,11,-0.3,0,Math.PI*2);
    ctx.fillStyle=cc[1];ctx.fill();
    ctx.beginPath();ctx.ellipse(sx+6,sy-trH-19,13,9,0.3,0,Math.PI*2);
    ctx.fillStyle=cc[2];ctx.fill();
    if(iB){
      for(let i=0;i<12;i++){
        const bx=sx+(seeded(col*100+row*17+i*7)-0.5)*36;
        const by=sy-trH-10+(seeded(col*50+row*33+i*11)-0.5)*24;
        ctx.beginPath();ctx.arc(bx,by,1.5+seeded(i)*1.5,0,Math.PI*2);
        ctx.fillStyle="#ffd0e8";ctx.fill();
      }
    }
  }

  // COBBLE: stone detail
  if(type===T.COBBLE){
    ctx.strokeStyle="rgba(80,80,70,0.4)";ctx.lineWidth=0.5;
    for(let ci=0;ci<4;ci++){
      const cx=sx-14+ci*9+seeded(col*13+row*7+ci)*4;
      const cy=sy-4+seeded(col*11+row*9+ci)*4;
      ctx.beginPath();ctx.ellipse(cx,cy,3+seeded(ci*3)*2,2,seeded(ci)*0.5,0,Math.PI*2);
      ctx.stroke();
    }
  }

  // WATER: ripple
  if(type===T.WATER){
    const rp=Math.sin(tick*0.05+col*0.8+row*0.6)*0.12+0.15;
    ctx.beginPath();
    ctx.moveTo(sx,sy-h2);ctx.lineTo(sx+w2,sy);
    ctx.lineTo(sx,sy+h2);ctx.lineTo(sx-w2,sy);ctx.closePath();
    ctx.fillStyle=`rgba(180,230,255,${rp})`;ctx.fill();
  }

  // DESK: surface + monitor stub
  if(type===T.DESK){
    ctx.fillStyle="#cc8833";
    ctx.fillRect(sx-TW*.35,sy-TH*.6,TW*.7,TH*.25);
    ctx.strokeStyle="#8B5500";ctx.lineWidth=1;
    ctx.strokeRect(sx-TW*.35,sy-TH*.6,TW*.7,TH*.25);
  }
}

// Character drawers
function drawCharBase(ctx,sx,sy,bodyColor,legColor,skinColor,hairColor){
  ctx.beginPath();ctx.ellipse(sx,sy+2,10,5,0,0,Math.PI*2);
  ctx.fillStyle="rgba(0,0,0,0.25)";ctx.fill();
  ctx.fillStyle=legColor;ctx.fillRect(sx-5,sy-6,4,8);ctx.fillRect(sx+1,sy-6,4,8);
  ctx.fillStyle=bodyColor;ctx.fillRect(sx-7,sy-20,14,14);
  ctx.fillStyle=skinColor;ctx.fillRect(sx-2,sy-23,4,4);
  ctx.beginPath();ctx.arc(sx,sy-29,9,0,Math.PI*2);ctx.fillStyle=skinColor;ctx.fill();
  ctx.fillStyle=hairColor;ctx.beginPath();ctx.arc(sx,sy-34,9,Math.PI,0);ctx.fill();
  ctx.fillRect(sx-9,sy-34,18,4);
  ctx.fillStyle="#222";ctx.fillRect(sx-4,sy-31,2,2);ctx.fillRect(sx+2,sy-31,2,2);
  ctx.fillStyle="#fff";ctx.fillRect(sx-3,sy-30,1,1);ctx.fillRect(sx+3,sy-30,1,1);
}
function drawPlayer(ctx,sx,sy){
  drawCharBase(ctx,sx,sy,"#3a7aff","#1a3acc","#ffcc99","#221100");
  ctx.fillStyle="rgba(255,255,200,0.9)";ctx.font="bold 6px 'Courier New'";
  ctx.textAlign="center";ctx.fillText("▶ YOU",sx,sy-44);
}
function drawDwight(ctx,sx,sy){
  drawCharBase(ctx,sx,sy,"#8B6914","#6a480a","#ffcc88","#111100");
  ctx.fillStyle="#ffdd00";
  ctx.beginPath();ctx.moveTo(sx,sy-20);ctx.lineTo(sx-2,sy-9);ctx.lineTo(sx,sy-6);ctx.lineTo(sx+2,sy-9);ctx.closePath();ctx.fill();
  ctx.strokeStyle="#222";ctx.lineWidth=1.2;
  ctx.strokeRect(sx-6,sy-32,4,3);ctx.strokeRect(sx+2,sy-32,4,3);
  ctx.beginPath();ctx.moveTo(sx-2,sy-32);ctx.lineTo(sx+2,sy-32);ctx.stroke();
  ctx.fillStyle="rgba(255,240,180,0.9)";ctx.font="bold 5px 'Courier New'";
  ctx.textAlign="center";ctx.fillText("DWIGHT",sx,sy-45);
}
function drawRalph(ctx,sx,sy){
  drawCharBase(ctx,sx,sy,"#cc2222","#334488","#ffddaa","#3355aa");
  ctx.fillStyle="#3355aa";ctx.fillRect(sx-10,sy-36,20,8);ctx.fillRect(sx-7,sy-42,14,7);
  ctx.fillStyle="#ffdd00";ctx.fillRect(sx-5,sy-33,10,3);
  ctx.strokeStyle="#663300";ctx.lineWidth=1.2;
  ctx.beginPath();ctx.arc(sx,sy-26,5,0.1,Math.PI-0.1);ctx.stroke();
  ctx.fillStyle="rgba(200,230,255,0.9)";ctx.font="bold 5px 'Courier New'";
  ctx.textAlign="center";ctx.fillText("RALPH",sx,sy-50);
}
function drawPickleRick(ctx,sx,sy){
  ctx.beginPath();ctx.ellipse(sx,sy+2,8,4,0,0,Math.PI*2);
  ctx.fillStyle="rgba(0,0,0,0.25)";ctx.fill();
  const pg=ctx.createLinearGradient(sx-6,sy-32,sx+6,sy-32);
  pg.addColorStop(0,"#229922");pg.addColorStop(.5,"#55ee55");pg.addColorStop(1,"#229922");
  ctx.beginPath();ctx.ellipse(sx,sy-16,6,18,0,0,Math.PI*2);ctx.fillStyle=pg;ctx.fill();
  ctx.strokeStyle="#116611";ctx.lineWidth=1;ctx.stroke();
  for(let i=0;i<5;i++){
    ctx.beginPath();ctx.arc(sx+(i%2===0?5.5:-5.5),sy-6-i*5.5,2.5,0,Math.PI*2);
    ctx.fillStyle="#44cc44";ctx.fill();
  }
  ctx.strokeStyle="#22aa22";ctx.lineWidth=2.5;
  ctx.beginPath();ctx.moveTo(sx-6,sy-18);ctx.lineTo(sx-14,sy-13);ctx.stroke();
  ctx.beginPath();ctx.moveTo(sx+6,sy-18);ctx.lineTo(sx+14,sy-13);ctx.stroke();
  ctx.beginPath();ctx.arc(sx,sy-30,7,0,Math.PI*2);ctx.fillStyle="#33cc33";ctx.fill();
  ctx.strokeStyle="#116611";ctx.lineWidth=0.8;ctx.stroke();
  ctx.fillStyle="#e0e8ff";
  ctx.beginPath();ctx.arc(sx,sy-37,5,Math.PI*1.1,0);ctx.fill();
  ctx.beginPath();ctx.arc(sx+5,sy-38,4,Math.PI*1.2,0);ctx.fill();
  ctx.fillStyle="#001100";ctx.fillRect(sx-4,sy-33,2,2);ctx.fillRect(sx+2,sy-33,2,2);
  ctx.strokeStyle="#001100";ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(sx-3,sy-29);ctx.lineTo(sx+3,sy-29);ctx.stroke();
  ctx.fillStyle="rgba(120,255,120,0.9)";ctx.font="bold 5px 'Courier New'";
  ctx.textAlign="center";ctx.fillText("PICKLE RICK",sx,sy-50);
}
const DRAWERS={dwight:drawDwight,ralph:drawRalph,pickle_rick:drawPickleRick};

// ═══════════════════════════════════════════════════════════
// CLAUDE API
// ═══════════════════════════════════════════════════════════
async function callClaude(systemPrompt,userMsg){
  const r=await fetch("https://api.anthropic.com/v1/messages",{
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({
      model:"claude-sonnet-4-20250514",
      max_tokens:180,
      system:systemPrompt,
      messages:[{role:"user",content:userMsg}]
    })
  });
  const d=await r.json();
  return d.content?.[0]?.text||"[No response]";
}

// ═══════════════════════════════════════════════════════════
// ZONE META
// ═══════════════════════════════════════════════════════════
const ZONE_META={
  [ZONE.OFFICE]: {label:"⬛ ANTHROPIC HQ — FLOOR 4",bg0:"#12122a",bg1:"#0a0a18"},
  [ZONE.OUTDOOR]:{label:"🌆 ANTHROPIC CAMPUS — PLAZA",bg0:"#0c1a2a",bg1:"#060e18"},
  [ZONE.FOREST]: {label:"🌸 CHERRY BLOSSOM FOREST",bg0:"#0a1a0a",bg1:"#050f05"},
};

// ═══════════════════════════════════════════════════════════
// MAIN COMPONENT
// ═══════════════════════════════════════════════════════════
export default function OfficeWorldHAM(){
  const canvasRef=useRef(null);
  const stateRef=useRef({
    zone:ZONE.OFFICE,
    player:{x:7.5,y:9.5},
    agents:{
      dwight: {x:4.5,y:4.5,bounce:0},
      ralph:  {x:7.5,y:7.5,bounce:0},
      pickle_rick:{x:10.5,y:4.5,bounce:0},
    },
    keys:{},tick:0,transitioning:false,
    fade:0,          // 0=clear, 1=black
    fadeDir:0,       // -1 fade in, 0 none, 1 fade out
    fadeZone:null,   // zone to switch to mid-fade
    fadeSpawn:null,
    fadeLabel:"",
  });
  const animRef=useRef(null);

  // UI state
  const [zone,setZone]=useState(ZONE.OFFICE);
  const [nearAgent,setNearAgent]=useState(null);
  const [nearTerminal,setNearTerminal]=useState(null);
  const [nearDoor,setNearDoor]=useState(false);
  const [nearPortal,setNearPortal]=useState(false);
  const [dialogue,setDialogue]=useState(null); // {agent, text}
  const [displayText,setDisplayText]=useState("");
  const [loadingDlg,setLoadingDlg]=useState(false);
  const [terminal,setTerminal]=useState(null);  // {cfg, history:[{role,content}], loading}
  const [termInput,setTermInput]=useState("");
  const [fadeLabel,setFadeLabel]=useState("");
  const typingRef=useRef(null);

  const typewrite=useCallback((text)=>{
    if(typingRef.current)clearInterval(typingRef.current);
    setDisplayText("");let i=0;
    typingRef.current=setInterval(()=>{
      setDisplayText(text.slice(0,i+1));i++;
      if(i>=text.length)clearInterval(typingRef.current);
    },26);
  },[]);

  // Zone transition
  const triggerTransition=useCallback((destZone,spawnPos,label)=>{
    const s=stateRef.current;
    if(s.transitioning)return;
    s.transitioning=true;
    s.fadeDir=1;s.fadeLabel=label;
    setFadeLabel(label);
    const fadeOut=()=>{
      s.fade+=0.06;
      if(s.fade>=1){
        s.fade=1;
        // Switch zone
        s.zone=destZone;
        s.player={...spawnPos};
        Object.keys(s.agents).forEach(k=>{
          const pos=AGENTS_CFG[k].pos[destZone];
          if(pos)s.agents[k]={...s.agents[k],...pos};
        });
        setZone(destZone);
        setDialogue(null);setDisplayText("");
        setTimeout(()=>{ s.fadeDir=-1; fadeIn(); },500);
        return;
      }
      requestAnimationFrame(fadeOut);
    };
    const fadeIn=()=>{
      s.fade-=0.05;
      if(s.fade<=0){
        s.fade=0;s.fadeDir=0;s.transitioning=false;
        return;
      }
      requestAnimationFrame(fadeIn);
    };
    fadeOut();
  },[]);

  // Talk to agent
  const talkAgent=useCallback(async(agentKey)=>{
    if(loadingDlg)return;
    const cfg=AGENTS_CFG[agentKey];
    setLoadingDlg(true);
    setDialogue({agent:agentKey,text:""});
    const z=stateRef.current.zone;
    const zoneName=z===ZONE.OFFICE?"Anthropic HQ office":z===ZONE.OUTDOOR?"Anthropic campus plaza":"cherry blossom forest";
    try{
      const txt=await callClaude(cfg.sp,
        `You're in the ${zoneName}. Someone just walked up and pressed [E] to talk. Respond spontaneously in character.`);
      setDialogue({agent:agentKey,text:txt});
      typewrite(txt);
    }catch{
      const fb={dwight:"Identity unconfirmed. State your beet preference immediately.",
        ralph:"My shoelace is named Kevin.",
        pickle_rick:"Oh great, a social interaction. I'm literally a pickle."};
      const t2=fb[agentKey];
      setDialogue({agent:agentKey,text:t2});typewrite(t2);
    }
    setLoadingDlg(false);
  },[loadingDlg,typewrite]);

  // Terminal send
  const termSend=useCallback(async()=>{
    if(!terminal||!termInput.trim()||terminal.loading)return;
    const msg=termInput.trim();
    setTermInput("");
    const newHist=[...terminal.history,{role:"user",content:msg}];
    setTerminal(t=>({...t,history:newHist,loading:true}));
    try{
      const reply=await callClaude(terminal.cfg.sysPrompt,msg);
      setTerminal(t=>({...t,
        history:[...newHist,{role:"assistant",content:reply}],
        loading:false}));
    }catch{
      setTerminal(t=>({...t,
        history:[...newHist,{role:"assistant",content:"[CONNECTION ERROR — retry]"}],
        loading:false}));
    }
  },[terminal,termInput]);

  // Keyboard
  useEffect(()=>{
    const down=(e)=>{
      stateRef.current.keys[e.key.toLowerCase()]=true;
      if(terminal){
        if(e.key==="Escape"){setTerminal(null);setTermInput("");}
        return;
      }
      if(e.key==="Escape"){setDialogue(null);setDisplayText("");}
      if((e.key===" "||e.key==="Enter")&&dialogue&&!loadingDlg){setDialogue(null);setDisplayText("");}
      if(e.key.toLowerCase()==="e"){
        if(dialogue){setDialogue(null);setDisplayText("");return;}
        const s=stateRef.current;
        // Check terminal
        const tc2=TERMINALS_CFG.find(t2=>{
          return dist({x:s.player.x,y:s.player.y},{x:t2.col+0.5,y:t2.row+0.5})<IDIST;
        });
        if(tc2&&s.zone===ZONE.OFFICE){
          setTerminal({cfg:tc2,history:[
            {role:"assistant",content:`[${tc2.label}] ONLINE — ${tc2.icon} Terminal ready. Type a query below.`}
          ],loading:false});
          return;
        }
        if(nearAgent)talkAgent(nearAgent);
      }
      if(["w","a","s","d","arrowup","arrowdown","arrowleft","arrowright"," "].includes(e.key.toLowerCase()))
        e.preventDefault();
    };
    const up=(e)=>{stateRef.current.keys[e.key.toLowerCase()]=false;};
    window.addEventListener("keydown",down);
    window.addEventListener("keyup",up);
    return()=>{window.removeEventListener("keydown",down);window.removeEventListener("keyup",up);};
  },[nearAgent,dialogue,loadingDlg,talkAgent,terminal]);

  // Main loop
  useEffect(()=>{
    const canvas=canvasRef.current;
    const ctx=canvas.getContext("2d");
    const loop=()=>{
      const s=stateRef.current;
      s.tick++;
      const map=MAPS[s.zone];

      // Player movement (skip if terminal or dialogue open)
      const uiOpen=dialogue||terminal;
      if(!uiOpen&&!s.transitioning){
        let dx=0,dy=0;
        if(s.keys["w"]||s.keys["arrowup"])    dy-=SPEED;
        if(s.keys["s"]||s.keys["arrowdown"])  dy+=SPEED;
        if(s.keys["a"]||s.keys["arrowleft"])  dx-=SPEED;
        if(s.keys["d"]||s.keys["arrowright"]) dx+=SPEED;
        if(dx&&dy){dx*=0.707;dy*=0.707;}
        const nx=s.player.x+dx,ny=s.player.y+dy;
        if(walkable(map,nx,s.player.y))s.player.x=nx;
        if(walkable(map,s.player.x,ny))s.player.y=ny;
      }

      // Portal / door check
      if(!s.transitioning){
        const pc=Math.floor(s.player.x),pr=Math.floor(s.player.y);
        const tile=map[pr]?.[pc];
        if(tile===T.PORTAL){
          const pd=PORTAL_DEST[s.zone];
          if(pd) triggerTransition(pd.dest,pd.spawn,
            pd.dest===ZONE.FOREST?"🌸 ENTERING CHERRY BLOSSOM FOREST":"🌆 ENTERING CAMPUS PLAZA");
        }
        if(tile===T.DOOR){
          const dd=DOOR_DEST[s.zone];
          if(dd) triggerTransition(dd.dest,dd.spawn,
            dd.dest===ZONE.OFFICE?"⬛ ENTERING ANTHROPIC HQ":"🌆 ENTERING CAMPUS PLAZA");
        }
      }

      // Agent proximity
      let closestAgent=null,closestD=Infinity;
      Object.keys(s.agents).forEach(k=>{
        const d=dist(s.player,s.agents[k]);
        if(d<IDIST&&d<closestD){closestAgent=k;closestD=d;}
      });
      if(closestAgent!==nearAgent) setNearAgent(closestAgent);

      // Terminal proximity (office only)
      if(s.zone===ZONE.OFFICE){
        const tc2=TERMINALS_CFG.find(t2=>
          dist({x:s.player.x,y:s.player.y},{x:t2.col+0.5,y:t2.row+0.5})<IDIST);
        setNearTerminal(tc2||null);
      } else {
        setNearTerminal(null);
      }

      // Portal/door proximity hint
      const pc2=Math.floor(s.player.x),pr2=Math.floor(s.player.y);
      const nearTile=map[pr2]?.[pc2];
      setNearPortal(nearTile===T.PORTAL||nearTile===T.DOOR);

      // Agent bounce
      Object.values(s.agents).forEach(a=>{ a.bounce=Math.sin(s.tick*0.05)*3; });

      // ── RENDER ──
      const meta=ZONE_META[s.zone];
      const bgGrd=ctx.createLinearGradient(0,0,0,CH);
      bgGrd.addColorStop(0,meta.bg0);bgGrd.addColorStop(1,meta.bg1);
      ctx.fillStyle=bgGrd;ctx.fillRect(0,0,CW,CH);

      // Stars in outdoor/forest
      if(s.zone!==ZONE.OFFICE){
        ctx.fillStyle="rgba(255,255,255,0.4)";
        for(let st=0;st<40;st++){
          const sx2=(seeded(st*7)*CW)|0;
          const sy2=(seeded(st*13)*CH*0.5)|0;
          const r=(seeded(st*17)*1.5+0.3);
          ctx.beginPath();ctx.arc(sx2,sy2,r,0,Math.PI*2);ctx.fill();
        }
      }

      // Camera
      const ps=iso(s.player.x,s.player.y,0,0);
      const ox=CW/2-ps.x,oy=CH/2-ps.y+40;

      // Build draw list
      const draws=[];
      for(let row=0;row<ROWS;row++){
        for(let col=0;col<COLS;col++){
          const type=map[row][col];
          const sc=iso(col,row,ox,oy);
          draws.push({z:col+row,sx:sc.x,sy:sc.y,kind:"tile",type,col,row});
        }
      }

      // Terminal glow highlights
      if(s.zone===ZONE.OFFICE){
        TERMINALS_CFG.forEach(tc2=>{
          const sc=iso(tc2.col,tc2.row,ox,oy);
          draws.push({z:tc2.col+tc2.row+0.1,sx:sc.x,sy:sc.y,kind:"termglow",cfg:tc2});
        });
      }

      const psc=iso(s.player.x,s.player.y,ox,oy);
      draws.push({z:s.player.x+s.player.y,sx:psc.x,sy:psc.y,kind:"player"});

      Object.entries(s.agents).forEach(([k,a])=>{
        const asc=iso(a.x,a.y,ox,oy);
        draws.push({z:a.x+a.y,sx:asc.x,sy:asc.y+a.bounce,kind:"agent",key:k,isNearest:k===closestAgent});
      });

      draws.sort((a,b)=>a.z-b.z);
      draws.forEach(dc=>{
        if(dc.kind==="tile") drawTile(ctx,dc.sx,dc.sy,dc.type,dc.col,dc.row,s.tick);
        else if(dc.kind==="termglow"){
          const sc2=iso(dc.cfg.col,dc.cfg.row,ox,oy);
          const isNear=dist({x:s.player.x,y:s.player.y},
            {x:dc.cfg.col+0.5,y:dc.cfg.row+0.5})<IDIST;
          if(isNear){
            // Highlight glow
            const gg=ctx.createRadialGradient(sc2.x,sc2.y-20,4,sc2.x,sc2.y-20,32);
            gg.addColorStop(0,dc.cfg.color+"88");gg.addColorStop(1,"transparent");
            ctx.beginPath();ctx.arc(sc2.x,sc2.y-20,32,0,Math.PI*2);
            ctx.fillStyle=gg;ctx.fill();
            ctx.fillStyle=dc.cfg.color;ctx.font="bold 8px 'Courier New'";
            ctx.textAlign="center";
            ctx.fillText(`[E] ${dc.cfg.label}`,sc2.x,sc2.y-58);
          }
        }
        else if(dc.kind==="player") drawPlayer(ctx,dc.sx,dc.sy);
        else if(dc.kind==="agent"){
          const dr=DRAWERS[dc.key];
          if(dr) dr(ctx,dc.sx,dc.sy);
          if(dc.isNearest){
            ctx.fillStyle="#fff700";ctx.font="bold 10px 'Courier New'";
            ctx.textAlign="center";ctx.fillText("[E] TALK",dc.sx,dc.sy-62);
          }
        }
      });

      // Fade overlay
      if(s.fade>0){
        ctx.fillStyle=`rgba(0,0,0,${s.fade})`;
        ctx.fillRect(0,0,CW,CH);
        if(s.fade>0.4&&s.fadeLabel){
          ctx.fillStyle=`rgba(255,255,255,${Math.min(1,(s.fade-0.4)*3)})`;
          ctx.font="bold 18px 'Courier New'";ctx.textAlign="center";
          ctx.fillText(s.fadeLabel,CW/2,CH/2);
          ctx.font="10px 'Courier New'";
          ctx.fillStyle=`rgba(180,180,255,${Math.min(1,(s.fade-0.4)*3)})`;
          ctx.fillText("loading world...",CW/2,CH/2+26);
        }
      }

      animRef.current=requestAnimationFrame(loop);
    };
    animRef.current=requestAnimationFrame(loop);
    return()=>cancelAnimationFrame(animRef.current);
  },[dialogue,terminal,triggerTransition]);

  const curAgent=dialogue?AGENTS_CFG[dialogue.agent]:null;

  // ═══════ TERMINAL UI ═══════
  const TerminalUI=terminal&&(
    <div style={{
      position:"absolute",inset:0,
      background:"rgba(0,5,15,0.96)",
      border:`2px solid ${terminal.cfg.color}`,
      borderRadius:"4px",
      display:"flex",flexDirection:"column",
      fontFamily:"'Courier New',monospace",
      zIndex:10,
    }}>
      {/* Header */}
      <div style={{
        background:`linear-gradient(90deg,rgba(0,0,0,0.9),${terminal.cfg.color}22,rgba(0,0,0,0.9))`,
        borderBottom:`1px solid ${terminal.cfg.color}66`,
        padding:"8px 16px",display:"flex",alignItems:"center",gap:"10px"
      }}>
        <span style={{fontSize:"18px"}}>{terminal.cfg.icon}</span>
        <div>
          <div style={{color:terminal.cfg.color,fontWeight:"bold",fontSize:"12px",letterSpacing:"3px"}}>
            {terminal.cfg.label}
          </div>
          <div style={{color:"#556",fontSize:"9px"}}>LLM TERMINAL · AxQxOS NODE · CONNECTED</div>
        </div>
        <button onClick={()=>{setTerminal(null);setTermInput("");}} style={{
          marginLeft:"auto",background:"none",border:`1px solid ${terminal.cfg.color}88`,
          color:terminal.cfg.color,cursor:"pointer",padding:"3px 10px",
          fontFamily:"inherit",fontSize:"10px",borderRadius:"2px"
        }}>✕ ESC</button>
      </div>

      {/* History */}
      <div style={{flex:1,overflowY:"auto",padding:"12px 16px",display:"flex",flexDirection:"column",gap:"10px"}}>
        {terminal.history.map((h,i)=>(
          <div key={i} style={{display:"flex",gap:"8px",alignItems:"flex-start"}}>
            <span style={{
              color:h.role==="user"?"#aaccff":terminal.cfg.color,
              fontSize:"10px",whiteSpace:"nowrap",marginTop:"1px",flexShrink:0
            }}>
              {h.role==="user"?"YOU >":terminal.cfg.label.split(" ")[0]+" >"}
            </span>
            <span style={{color:h.role==="user"?"#cce0ff":"#ddd",fontSize:"11px",lineHeight:1.7}}>
              {h.content}
            </span>
          </div>
        ))}
        {terminal.loading&&(
          <div style={{color:terminal.cfg.color,fontSize:"11px"}}>
            {terminal.cfg.label.split(" ")[0]} <span style={{animation:"blink 0.6s infinite"}}>▌</span> processing...
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{
        borderTop:`1px solid ${terminal.cfg.color}44`,
        padding:"10px 16px",display:"flex",gap:"8px",alignItems:"center"
      }}>
        <span style={{color:terminal.cfg.color,fontSize:"12px",flexShrink:0}}>{">"}</span>
        <input
          autoFocus
          value={termInput}
          onChange={e=>setTermInput(e.target.value)}
          onKeyDown={e=>{if(e.key==="Enter")termSend();}}
          placeholder={`Query ${terminal.cfg.label}...`}
          style={{
            flex:1,background:"rgba(0,10,30,0.8)",
            border:`1px solid ${terminal.cfg.color}44`,
            color:"#ddeeff",fontFamily:"'Courier New',monospace",
            fontSize:"11px",padding:"6px 10px",borderRadius:"2px",outline:"none"
          }}
        />
        <button onClick={termSend} disabled={terminal.loading} style={{
          background:terminal.cfg.color+"33",
          border:`1px solid ${terminal.cfg.color}88`,
          color:terminal.cfg.color,cursor:"pointer",
          padding:"6px 14px",fontFamily:"inherit",fontSize:"10px",
          borderRadius:"2px",opacity:terminal.loading?0.5:1
        }}>SEND</button>
      </div>
    </div>
  );

  // ═══════ DIALOGUE BOX ═══════
  const DialogueBox=dialogue&&!terminal&&(
    <div style={{
      position:"absolute",bottom:0,left:0,right:0,
      background:"rgba(5,3,18,0.97)",
      borderTop:"2px solid #6633cc",
      borderRadius:"0 0 4px 4px",
      padding:"12px 18px",minHeight:"105px"
    }}>
      <div style={{display:"flex",gap:"12px",alignItems:"flex-start"}}>
        <div style={{
          width:"58px",height:"58px",flexShrink:0,
          border:`2px solid ${curAgent?.color||"#fff"}`,
          borderRadius:"6px",background:"rgba(20,8,50,0.9)",
          display:"flex",alignItems:"center",justifyContent:"center",
          fontSize:"26px",boxShadow:`0 0 14px ${curAgent?.color||"#fff"}44`
        }}>
          {dialogue.agent==="dwight"?"🕶️":dialogue.agent==="ralph"?"👮":"🥒"}
        </div>
        <div style={{flex:1}}>
          <div style={{color:curAgent?.color,fontWeight:"bold",fontSize:"10px",
            marginBottom:"5px",letterSpacing:"2px"}}>
            {curAgent?.name?.toUpperCase()}
          </div>
          <div style={{color:"#ddd",fontSize:"12px",lineHeight:1.7,minHeight:"38px"}}>
            {loadingDlg
              ? <span style={{color:"#8866aa"}}>
                  ▌ {dialogue.agent==="dwight"?"Assessing threat level...":
                     dialogue.agent==="ralph"?"Thinking of something...":
                     "Calculating superior response..."}
                </span>
              : displayText}
            {!loadingDlg&&displayText&&
              <span style={{animation:"blink 0.7s infinite",color:"#cc88ff"}}>▌</span>}
          </div>
          {!loadingDlg&&displayText&&
            <div style={{color:"#5544aa",fontSize:"9px",marginTop:"5px"}}>[SPACE] CLOSE</div>}
        </div>
      </div>
    </div>
  );

  // Zone names for HUD
  const zoneMeta=ZONE_META[zone];

  return(
    <div style={{
      display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",
      minHeight:"100vh",background:"#030308",fontFamily:"'Courier New',monospace"
    }}>
      {/* Title bar */}
      <div style={{
        color:"#cc88ff",fontSize:"12px",letterSpacing:"4px",fontWeight:"bold",
        marginBottom:"7px",textTransform:"uppercase",
        textShadow:"0 0 18px #aa44ff,0 0 36px #7700cc"
      }}>
        ◈ THE OFFICE WORLD · HUMAN ACTION MODEL · v2 ◈
      </div>

      <div style={{position:"relative"}}>
        <canvas ref={canvasRef} width={CW} height={CH} style={{
          border:"2px solid #4422aa",display:"block",borderRadius:"4px",
          boxShadow:"0 0 40px rgba(100,40,200,0.5),0 0 80px rgba(60,20,120,0.25)"
        }}/>

        {/* Terminal UI overlay */}
        {TerminalUI}

        {/* HUD top-left */}
        <div style={{
          position:"absolute",top:"10px",left:"12px",
          background:"rgba(8,4,22,0.88)",border:"1px solid #4422aa",
          borderRadius:"4px",padding:"6px 12px",minWidth:"160px"
        }}>
          <div style={{color:"#cc88ff",fontWeight:"bold",fontSize:"10px",marginBottom:"2px"}}>
            {zoneMeta.label}
          </div>
          <div style={{color:"#6666aa",fontSize:"8px",lineHeight:1.6}}>
            WASD MOVE · E INTERACT<br/>
            {zone===ZONE.OFFICE?"10 TERMINALS AVAILABLE":
             zone===ZONE.OUTDOOR?"PORTALS TO HQ & FOREST":
             "PORTAL TO OUTDOOR WORLD"}
          </div>
        </div>

        {/* Agent roster top-right */}
        <div style={{
          position:"absolute",top:"10px",right:"12px",
          background:"rgba(8,4,22,0.88)",border:"1px solid #4422aa",
          borderRadius:"4px",padding:"6px 10px"
        }}>
          {Object.entries(AGENTS_CFG).map(([k,v])=>(
            <div key={k} style={{
              display:"flex",alignItems:"center",gap:"6px",
              marginBottom:"3px",color:v.color,fontSize:"9px"
            }}>
              <span style={{
                width:"7px",height:"7px",borderRadius:"50%",
                background:v.color,display:"inline-block",
                boxShadow:`0 0 5px ${v.color}`
              }}/>
              {v.short}
            </div>
          ))}
        </div>

        {/* Context prompt bottom */}
        {!terminal&&(nearTerminal||nearAgent||nearPortal)&&(
          <div style={{
            position:"absolute",bottom:dialogue?"112px":"10px",
            left:"50%",transform:"translateX(-50%)",
            background:"rgba(8,4,22,0.88)",border:"1px solid #441188",
            borderRadius:"20px",padding:"4px 18px",
            color:nearTerminal?"#88ffcc":nearAgent?"#fff700":"#9966cc",
            fontSize:"9px",letterSpacing:"2px",whiteSpace:"nowrap"
          }}>
            {nearTerminal
              ? `[E] OPEN ${nearTerminal.label} ${nearTerminal.icon}`
              : nearAgent
              ? `[E] TALK TO ${AGENTS_CFG[nearAgent]?.short}`
              : zone===ZONE.OFFICE?"▼ WALK THROUGH DOOR → CAMPUS PLAZA"
              : zone===ZONE.OUTDOOR?"◈ WALK INTO PORTAL → FOREST"
              : "◈ WALK INTO PORTAL → CAMPUS PLAZA"}
          </div>
        )}

        {/* Dialogue */}
        {DialogueBox}
      </div>

      <style>{`
        @keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
        canvas{image-rendering:pixelated}
        ::-webkit-scrollbar{width:4px}
        ::-webkit-scrollbar-track{background:#0a0a18}
        ::-webkit-scrollbar-thumb{background:#4422aa;border-radius:2px}
        input::placeholder{color:#334455}
      `}</style>
    </div>
  );
}
