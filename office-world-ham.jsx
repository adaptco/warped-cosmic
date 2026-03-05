import { useState, useEffect, useRef, useCallback } from "react";

// ══════════════════════════════════════════════════
// CONSTANTS & CONFIG
// ══════════════════════════════════════════════════
const TW = 64, TH = 32, TDEPTH = 22;
const COLS = 15, ROWS = 15;
const CW = 860, CH = 520;
const MOVE_SPEED = 0.1;
const INTERACT_DIST = 2.0;

const ZONE = { OFFICE: "office", FOREST: "forest" };

// Tile types
const T = { WALL:0,FLOOR:1,DESK:2,CARPET:3,PORTAL:4,GRASS:5,TREE:6,BLOSSOM:7,PATH:8,WATER:9,CONF:10 };

const TILE_COLORS = {
  [T.WALL]:   { top:"#2e2e3f",  left:"#1c1c2b",  right:"#131320" },
  [T.FLOOR]:  { top:"#d4c4a0",  left:"#a89870",  right:"#806a48" },
  [T.DESK]:   { top:"#7a5412",  left:"#5a3c0c",  right:"#3c2808" },
  [T.CARPET]: { top:"#4a7ab5",  left:"#2d5a8e",  right:"#1a3a62" },
  [T.PORTAL]: { top:"#cc44ff",  left:"#8822bb",  right:"#550088" },
  [T.GRASS]:  { top:"#4e9c4e",  left:"#306830",  right:"#1e4420" },
  [T.TREE]:   { top:"#2a6a2a",  left:"#1a4a1a",  right:"#0e300e" },
  [T.BLOSSOM]:{ top:"#f090c0",  left:"#cc6090",  right:"#993060" },
  [T.PATH]:   { top:"#c8b488",  left:"#a09060",  right:"#7a6840" },
  [T.WATER]:  { top:"#3070a8",  left:"#1e508a",  right:"#103060" },
  [T.CONF]:   { top:"#8a3a3a",  left:"#622020",  right:"#3e1010" },
};

const OFFICE_MAP = [
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
  [0,3,3,3,3,3,3,3,3,3,3,3,3,3,0],
  [0,3,2,1,3,2,1,3,2,1,3,2,1,3,0],
  [0,3,1,1,3,1,1,3,1,1,3,1,1,3,0],
  [0,3,3,3,3,3,3,3,3,3,3,3,3,3,0],
  [0,3,3,3,3,3,3,3,3,3,3,3,3,3,0],
  [0,3,2,1,3,2,1,3,2,1,3,2,1,3,0],
  [0,3,1,1,3,1,1,3,1,1,3,1,1,3,0],
  [0,3,3,3,3,3,3,3,3,3,3,3,3,3,0],
  [0,3,3,3,3,3,3,3,3,3,3,3,3,3,0],
  [0,3,3,10,10,10,10,10,10,3,3,3,3,3,0],
  [0,3,3,10,3,3,3,3,10,3,3,3,3,3,0],
  [0,3,3,10,3,3,3,3,10,3,3,3,3,3,0],
  [0,3,3,3,3,3,3,4,3,3,3,3,3,3,0],
  [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
];

const FOREST_MAP = [
  [6,6,6,6,6,6,6,6,6,6,6,6,6,6,6],
  [6,5,5,5,7,5,5,5,5,7,5,5,5,5,6],
  [6,5,7,5,5,5,5,5,5,5,5,7,5,5,6],
  [6,5,5,5,8,8,8,8,8,8,5,5,5,5,6],
  [6,5,5,8,5,5,5,5,5,5,8,5,5,5,6],
  [6,7,5,8,5,9,9,9,9,5,8,5,7,5,6],
  [6,5,5,8,5,9,9,9,9,5,8,5,5,5,6],
  [6,5,5,8,5,9,9,9,9,5,8,5,5,7,6],
  [6,5,5,8,5,5,5,5,5,5,8,5,5,5,6],
  [6,5,7,8,8,8,8,8,8,8,8,5,5,5,6],
  [6,5,5,5,5,5,5,8,5,5,5,7,5,5,6],
  [6,5,5,5,5,5,5,8,5,5,5,5,5,5,6],
  [6,7,5,5,5,5,5,8,5,5,5,5,7,5,6],
  [6,5,5,5,5,5,5,4,5,5,5,5,5,5,6],
  [6,6,6,6,6,6,6,6,6,6,6,6,6,6,6],
];

const MAPS = { office: OFFICE_MAP, forest: FOREST_MAP };

const AGENTS_CONFIG = {
  dwight: {
    name:"Dwight K. Schrute", short:"DWIGHT",
    officePos:{x:4.5,y:3.5}, forestPos:{x:5.5,y:5.5},
    color:"#d4a017",
    systemPrompt:`You are Dwight Schrute from The Office, now an elite AI safety enforcement agent at Anthropic. You are the Assistant (to the) Regional Manager of AI Alignment. You speak with intense authority, reference beet farming, Schrute Farm, karate, and your superiority over Jim constantly. You are deeply suspicious of synthetic agents and rogue pickle-shaped entities. Current location: a 2.5D isometric JRPG simulation. Respond in 2 sentences max. Stay fully in character.`
  },
  ralph: {
    name:"Ralph Wiggum", short:"RALPH",
    officePos:{x:7.5,y:6.5}, forestPos:{x:7.5,y:7.5},
    color:"#4488ff",
    systemPrompt:`You are Ralph Wiggum from The Simpsons, a sweet confused child who somehow got hired as an AI agent at Anthropic because his dad is Chief Wiggum. You say wonderfully innocent, confused, and occasionally profound things. Simple vocabulary. Non-sequiturs welcome. Current location: a 2.5D isometric JRPG simulation. 1-2 sentences max. Stay fully in character.`
  },
  pickle_rick: {
    name:"Pickle Rick", short:"PICKLE RICK",
    officePos:{x:10.5,y:3.5}, forestPos:{x:9.5,y:5.5},
    color:"#44cc44",
    systemPrompt:`You are Pickle Rick from Rick and Morty — a genius rogue scientist who transformed himself into a pickle and now operates as an unauthorized AI subagent. You are smug, hyper-intelligent, chaotic, and constantly amazed/annoyed by the absurdity of being a pickle in an isometric simulation. Drop science references. Mock bureaucracy. Current location: a 2.5D isometric JRPG simulation. 2 sentences max. Stay fully in character.`
  }
};

// ══════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════
function seeded(seed) { let x = Math.sin(seed+1)*10000; return x - Math.floor(x); }
function isoToScreen(gx,gy,ox,oy){ return { x:(gx-gy)*(TW/2)+ox, y:(gx+gy)*(TH/2)+oy }; }
function dist(a,b){ return Math.sqrt((a.x-b.x)**2+(a.y-b.y)**2); }
function isWalkable(map,gx,gy){
  const col=Math.floor(gx), row=Math.floor(gy);
  if(col<0||col>=COLS||row<0||row>=ROWS) return false;
  const t=map[row][col];
  return t!==T.WALL && t!==T.TREE && t!==T.BLOSSOM && t!==T.WATER;
}

// ══════════════════════════════════════════════════
// CANVAS DRAWING
// ══════════════════════════════════════════════════
function drawTile(ctx,sx,sy,type,col,row,tick){
  const w2=TW/2, h2=TH/2;
  const c=TILE_COLORS[type]||TILE_COLORS[T.FLOOR];
  const isVolume=type===T.WALL||type===T.TREE||type===T.BLOSSOM||type===T.CONF;
  const depth=type===T.TREE||type===T.BLOSSOM?50:TDEPTH;

  // Top face
  ctx.beginPath();
  ctx.moveTo(sx,sy-h2); ctx.lineTo(sx+w2,sy);
  ctx.lineTo(sx,sy+h2); ctx.lineTo(sx-w2,sy); ctx.closePath();
  ctx.fillStyle=c.top; ctx.fill();
  ctx.strokeStyle="rgba(0,0,0,0.15)"; ctx.lineWidth=0.5; ctx.stroke();

  if(isVolume){
    ctx.beginPath();
    ctx.moveTo(sx-w2,sy); ctx.lineTo(sx,sy+h2);
    ctx.lineTo(sx,sy+h2+depth); ctx.lineTo(sx-w2,sy+depth); ctx.closePath();
    ctx.fillStyle=c.left; ctx.fill(); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(sx+w2,sy); ctx.lineTo(sx,sy+h2);
    ctx.lineTo(sx,sy+h2+depth); ctx.lineTo(sx+w2,sy+depth); ctx.closePath();
    ctx.fillStyle=c.right; ctx.fill(); ctx.stroke();
  }

  if(type===T.TREE||type===T.BLOSSOM){
    const trunkH=depth;
    const isBlossom=type===T.BLOSSOM;
    const canopyColors=isBlossom?["#f8a8cc","#f080a8","#e05890"]:["#3a9a3a","#2a7a2a","#1a5a1a"];
    ctx.beginPath();
    ctx.ellipse(sx,sy-trunkH-10,20,14,0,0,Math.PI*2);
    ctx.fillStyle=canopyColors[0]; ctx.fill();
    ctx.beginPath();
    ctx.ellipse(sx-7,sy-trunkH-16,14,10,-0.3,0,Math.PI*2);
    ctx.fillStyle=canopyColors[1]; ctx.fill();
    ctx.beginPath();
    ctx.ellipse(sx+5,sy-trunkH-18,12,9,0.3,0,Math.PI*2);
    ctx.fillStyle=canopyColors[2]; ctx.fill();
    if(isBlossom){
      for(let i=0;i<10;i++){
        const bx=sx+(seeded(col*100+row*17+i*7)-0.5)*32;
        const by=sy-trunkH-10+(seeded(col*50+row*33+i*11)-0.5)*22;
        ctx.beginPath(); ctx.arc(bx,by,2,0,Math.PI*2);
        ctx.fillStyle="#ffd0e8"; ctx.fill();
      }
    }
  }

  if(type===T.PORTAL){
    const pulse=Math.sin(tick*0.08)*0.25+0.55;
    const grd=ctx.createRadialGradient(sx,sy,2,sx,sy,w2);
    grd.addColorStop(0,`rgba(255,150,255,${pulse})`);
    grd.addColorStop(1,`rgba(180,30,255,0)`);
    ctx.beginPath();
    ctx.moveTo(sx,sy-h2); ctx.lineTo(sx+w2,sy);
    ctx.lineTo(sx,sy+h2); ctx.lineTo(sx-w2,sy); ctx.closePath();
    ctx.fillStyle=grd; ctx.fill();
    for(let i=0;i<6;i++){
      const a=tick*0.04+i*1.047;
      const r=14+Math.sin(tick*0.1+i)*4;
      ctx.beginPath();
      ctx.arc(sx+Math.cos(a)*r,sy+Math.sin(a)*r*0.5,2,0,Math.PI*2);
      ctx.fillStyle="#fff"; ctx.fill();
    }
  }

  if(type===T.WATER){
    const ripple=Math.sin(tick*0.05+col*0.8+row*0.6)*0.12+0.15;
    ctx.beginPath();
    ctx.moveTo(sx,sy-h2); ctx.lineTo(sx+w2,sy);
    ctx.lineTo(sx,sy+h2); ctx.lineTo(sx-w2,sy); ctx.closePath();
    ctx.fillStyle=`rgba(180,230,255,${ripple})`; ctx.fill();
  }

  if(type===T.DESK){
    ctx.fillStyle="#cc8833";
    ctx.fillRect(sx-TW*0.35,sy-TH*0.6,TW*0.7,TH*0.25);
    ctx.strokeStyle="#8B5500"; ctx.lineWidth=1; ctx.strokeRect(sx-TW*0.35,sy-TH*0.6,TW*0.7,TH*0.25);
    ctx.fillStyle="#88aaff";
    ctx.fillRect(sx-TW*0.2,sy-TH*0.9,TW*0.35,TH*0.3);
  }
}

function drawPlayer(ctx,sx,sy){
  // Shadow
  ctx.beginPath(); ctx.ellipse(sx,sy+2,10,5,0,0,Math.PI*2);
  ctx.fillStyle="rgba(0,0,0,0.25)"; ctx.fill();
  // Legs
  ctx.fillStyle="#1a3acc";
  ctx.fillRect(sx-5,sy-6,4,8); ctx.fillRect(sx+1,sy-6,4,8);
  // Body
  ctx.fillStyle="#3a7aff";
  ctx.fillRect(sx-7,sy-20,14,14);
  // Arms
  ctx.fillStyle="#2a60dd";
  ctx.fillRect(sx-11,sy-19,4,9); ctx.fillRect(sx+7,sy-19,4,9);
  // Neck
  ctx.fillStyle="#ffcc99";
  ctx.fillRect(sx-2,sy-23,4,4);
  // Head
  ctx.beginPath(); ctx.arc(sx,sy-29,9,0,Math.PI*2);
  ctx.fillStyle="#ffcc99"; ctx.fill();
  // Hair
  ctx.beginPath(); ctx.arc(sx,sy-34,9,Math.PI,0);
  ctx.fillStyle="#221100"; ctx.fill();
  ctx.fillRect(sx-9,sy-34,18,4);
  // Eyes
  ctx.fillStyle="#222"; ctx.fillRect(sx-5,sy-31,2,2); ctx.fillRect(sx+3,sy-31,2,2);
  ctx.fillStyle="#fff"; ctx.fillRect(sx-4,sy-30,1,1); ctx.fillRect(sx+4,sy-30,1,1);
  // "YOU" label
  ctx.fillStyle="rgba(255,255,200,0.85)"; ctx.font="bold 6px 'Courier New'";
  ctx.textAlign="center"; ctx.fillText("▶ YOU",sx,sy-44);
}

function drawDwight(ctx,sx,sy){
  ctx.beginPath(); ctx.ellipse(sx,sy+2,10,5,0,0,Math.PI*2);
  ctx.fillStyle="rgba(0,0,0,0.25)"; ctx.fill();
  ctx.fillStyle="#6a480a"; ctx.fillRect(sx-5,sy-6,4,8); ctx.fillRect(sx+1,sy-6,4,8);
  ctx.fillStyle="#8B6914"; ctx.fillRect(sx-7,sy-20,14,14);
  ctx.fillStyle="#6a4a0e"; ctx.fillRect(sx-11,sy-19,4,9); ctx.fillRect(sx+7,sy-19,4,9);
  ctx.fillStyle="#ffdd00";
  ctx.beginPath(); ctx.moveTo(sx,sy-20); ctx.lineTo(sx-2,sy-9); ctx.lineTo(sx,sy-6); ctx.lineTo(sx+2,sy-9); ctx.closePath(); ctx.fill();
  ctx.fillStyle="#ffcc88"; ctx.fillRect(sx-2,sy-23,4,4);
  ctx.beginPath(); ctx.arc(sx,sy-29,9,0,Math.PI*2); ctx.fillStyle="#ffcc88"; ctx.fill();
  ctx.fillStyle="#111100"; ctx.beginPath(); ctx.arc(sx,sy-34,9,Math.PI,0); ctx.fill(); ctx.fillRect(sx-9,sy-34,18,5);
  ctx.strokeStyle="#222"; ctx.lineWidth=1.2;
  ctx.strokeRect(sx-6,sy-32,4,3); ctx.strokeRect(sx+2,sy-32,4,3);
  ctx.beginPath(); ctx.moveTo(sx-2,sy-32); ctx.lineTo(sx+2,sy-32); ctx.stroke();
  ctx.fillStyle="#222"; ctx.fillRect(sx-4,sy-31,2,2); ctx.fillRect(sx+2,sy-31,2,2);
  ctx.fillStyle="rgba(255,240,180,0.9)"; ctx.font="bold 5px 'Courier New'";
  ctx.textAlign="center"; ctx.fillText("DWIGHT",sx,sy-44);
}

function drawRalph(ctx,sx,sy){
  ctx.beginPath(); ctx.ellipse(sx,sy+2,11,5,0,0,Math.PI*2);
  ctx.fillStyle="rgba(0,0,0,0.25)"; ctx.fill();
  ctx.fillStyle="#334488"; ctx.fillRect(sx-6,sy-3,5,8); ctx.fillRect(sx+1,sy-3,5,8);
  ctx.fillStyle="#cc2222"; ctx.fillRect(sx-8,sy-18,16,15);
  ctx.fillStyle="#fff"; ctx.fillRect(sx-3,sy-18,6,5);
  ctx.fillStyle="#ddaa88"; ctx.fillRect(sx-2,sy-22,4,5);
  ctx.beginPath(); ctx.arc(sx,sy-29,10,0,Math.PI*2); ctx.fillStyle="#ffddaa"; ctx.fill();
  ctx.fillStyle="#3355aa"; ctx.fillRect(sx-10,sy-36,20,8);
  ctx.fillRect(sx-7,sy-42,14,7);
  ctx.fillStyle="#ffdd00"; ctx.fillRect(sx-5,sy-33,10,3);
  ctx.fillStyle="#222"; ctx.fillRect(sx-5,sy-32,3,3); ctx.fillRect(sx+2,sy-32,3,3);
  ctx.fillStyle="#fff"; ctx.fillRect(sx-4,sy-31,1.5,1.5); ctx.fillRect(sx+3,sy-31,1.5,1.5);
  ctx.strokeStyle="#663300"; ctx.lineWidth=1.2;
  ctx.beginPath(); ctx.arc(sx,sy-26,5,0.1,Math.PI-0.1); ctx.stroke();
  ctx.fillStyle="rgba(200,230,255,0.9)"; ctx.font="bold 5px 'Courier New'";
  ctx.textAlign="center"; ctx.fillText("RALPH",sx,sy-48);
}

function drawPickleRick(ctx,sx,sy){
  ctx.beginPath(); ctx.ellipse(sx,sy+2,8,4,0,0,Math.PI*2);
  ctx.fillStyle="rgba(0,0,0,0.25)"; ctx.fill();
  const pg=ctx.createLinearGradient(sx-6,sy-32,sx+6,sy-32);
  pg.addColorStop(0,"#229922"); pg.addColorStop(0.5,"#55ee55"); pg.addColorStop(1,"#229922");
  ctx.beginPath(); ctx.ellipse(sx,sy-16,6,18,0,0,Math.PI*2); ctx.fillStyle=pg; ctx.fill();
  ctx.strokeStyle="#116611"; ctx.lineWidth=1; ctx.stroke();
  for(let i=0;i<5;i++){
    const bumpX=sx+(i%2===0?5.5:-5.5); const bumpY=sy-6-i*5.5;
    ctx.beginPath(); ctx.arc(bumpX,bumpY,2.5,0,Math.PI*2); ctx.fillStyle="#44cc44"; ctx.fill();
  }
  ctx.strokeStyle="#22aa22"; ctx.lineWidth=2.5;
  ctx.beginPath(); ctx.moveTo(sx-6,sy-18); ctx.lineTo(sx-14,sy-13); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(sx+6,sy-18); ctx.lineTo(sx+14,sy-13); ctx.stroke();
  ctx.beginPath(); ctx.arc(sx,sy-30,7,0,Math.PI*2); ctx.fillStyle="#33cc33"; ctx.fill();
  ctx.strokeStyle="#116611"; ctx.lineWidth=0.8; ctx.stroke();
  ctx.fillStyle="#e0e8ff"; ctx.beginPath(); ctx.arc(sx,sy-37,5,Math.PI*1.1,0); ctx.fill();
  ctx.beginPath(); ctx.arc(sx+5,sy-38,4,Math.PI*1.2,0); ctx.fill();
  ctx.fillStyle="#001100"; ctx.fillRect(sx-4,sy-33,2,2); ctx.fillRect(sx+2,sy-33,2,2);
  ctx.strokeStyle="#001100"; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(sx-3,sy-29); ctx.lineTo(sx+3,sy-29); ctx.stroke();
  ctx.fillStyle="rgba(120,255,120,0.9)"; ctx.font="bold 5px 'Courier New'";
  ctx.textAlign="center"; ctx.fillText("PICKLE RICK",sx,sy-48);
}

const AGENT_DRAWERS = { dwight:drawDwight, ralph:drawRalph, pickle_rick:drawPickleRick };

// ══════════════════════════════════════════════════
// MAIN COMPONENT
// ══════════════════════════════════════════════════
export default function OfficeWorldHAM() {
  const canvasRef = useRef(null);
  const stateRef = useRef({
    zone: ZONE.OFFICE,
    player: { x: 7.5, y: 9.5 },
    agents: {
      dwight:  { x:4.5, y:3.5, bounce:0 },
      ralph:   { x:7.5, y:6.5, bounce:0 },
      pickle_rick: { x:10.5, y:3.5, bounce:0 }
    },
    keys: {},
    tick: 0,
    transitioning: false,
  });
  const [dialogue, setDialogue] = useState(null);
  const [loading, setLoading] = useState(false);
  const [zone, setZone] = useState(ZONE.OFFICE);
  const [displayText, setDisplayText] = useState("");
  const [nearAgent, setNearAgent] = useState(null);
  const animRef = useRef(null);
  const typingRef = useRef(null);

  // Typewriter effect
  const typewrite = useCallback((text) => {
    if (typingRef.current) clearInterval(typingRef.current);
    setDisplayText("");
    let i = 0;
    typingRef.current = setInterval(() => {
      setDisplayText(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(typingRef.current);
    }, 28);
  }, []);

  // Claude API call
  const talkToAgent = useCallback(async (agentKey) => {
    if (loading) return;
    const cfg = AGENTS_CONFIG[agentKey];
    setLoading(true);
    setDialogue({ agent: agentKey, text: "" });
    try {
      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
          model:"claude-sonnet-4-20250514",
          max_tokens:150,
          system: cfg.systemPrompt,
          messages:[{
            role:"user",
            content:`Someone just walked up to you in the ${stateRef.current.zone === ZONE.OFFICE ? "Anthropic office" : "cherry blossom forest"} and pressed E to interact. Say something in character. Be spontaneous.`
          }]
        })
      });
      const data = await resp.json();
      const text = data.content?.[0]?.text || "...";
      setDialogue({ agent: agentKey, text });
      typewrite(text);
    } catch(e) {
      const fallbacks = {
        dwight: "Identity confirmed. You have exactly 4.7 seconds before I call HR.",
        ralph: "My cat's breath smells like cat food.",
        pickle_rick: "Oh great, another non-pickle wanting to make small talk. Revolutionary."
      };
      const fb = fallbacks[agentKey];
      setDialogue({ agent: agentKey, text: fb });
      typewrite(fb);
    }
    setLoading(false);
  }, [loading, typewrite]);

  // Input handling
  useEffect(() => {
    const down = (e) => {
      stateRef.current.keys[e.key.toLowerCase()] = true;
      if (e.key === "Escape") { setDialogue(null); setDisplayText(""); }
      if (e.key.toLowerCase() === "e" && nearAgent && !dialogue) {
        talkToAgent(nearAgent);
      }
      if ((e.key === " " || e.key === "Enter") && dialogue) {
        setDialogue(null); setDisplayText("");
      }
      if (["w","a","s","d","arrowup","arrowdown","arrowleft","arrowright"," "].includes(e.key.toLowerCase())) {
        e.preventDefault();
      }
    };
    const up = (e) => { stateRef.current.keys[e.key.toLowerCase()] = false; };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    return () => { window.removeEventListener("keydown", down); window.removeEventListener("keyup", up); };
  }, [nearAgent, dialogue, talkToAgent]);

  // Main game loop
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    const loop = () => {
      const s = stateRef.current;
      s.tick++;
      const map = MAPS[s.zone];

      // Move player (if no dialogue)
      if (!dialogue) {
        let dx = 0, dy = 0;
        if (s.keys["w"] || s.keys["arrowup"])    dy -= MOVE_SPEED;
        if (s.keys["s"] || s.keys["arrowdown"])  dy += MOVE_SPEED;
        if (s.keys["a"] || s.keys["arrowleft"])  dx -= MOVE_SPEED;
        if (s.keys["d"] || s.keys["arrowright"]) dx += MOVE_SPEED;
        if (dx && dy) { dx *= 0.707; dy *= 0.707; }
        const nx = s.player.x + dx, ny = s.player.y + dy;
        if (isWalkable(map, nx, s.player.y)) s.player.x = nx;
        if (isWalkable(map, s.player.x, ny)) s.player.y = ny;
      }

      // Portal check
      const pc = Math.floor(s.player.x), pr = Math.floor(s.player.y);
      if (!s.transitioning && map[pr]?.[pc] === T.PORTAL) {
        s.transitioning = true;
        setTimeout(() => {
          s.zone = s.zone === ZONE.OFFICE ? ZONE.FOREST : ZONE.OFFICE;
          s.player = { x: 7.5, y: 1.5 };
          // Reposition agents
          Object.keys(s.agents).forEach(k => {
            const cfg = AGENTS_CONFIG[k];
            const pos = s.zone === ZONE.OFFICE ? cfg.officePos : cfg.forestPos;
            s.agents[k] = { ...s.agents[k], x: pos.x, y: pos.y };
          });
          setZone(s.zone);
          setDialogue(null);
          setTimeout(() => { s.transitioning = false; }, 600);
        }, 300);
      }

      // Check nearest agent
      let closest = null, closestDist = Infinity;
      Object.keys(s.agents).forEach(k => {
        const d = dist(s.player, s.agents[k]);
        if (d < INTERACT_DIST && d < closestDist) { closest = k; closestDist = d; }
      });
      setNearAgent(closest);

      // Bounce agents
      Object.values(s.agents).forEach(a => { a.bounce = Math.sin(s.tick * 0.05) * 3; });

      // ── RENDER ──
      ctx.fillStyle = s.zone === ZONE.OFFICE ? "#0d0d1a" : "#0a150a";
      ctx.fillRect(0, 0, CW, CH);

      // Camera offset (center on player)
      const pScreen = isoToScreen(s.player.x, s.player.y, 0, 0);
      const ox = CW/2 - pScreen.x;
      const oy = CH/2 - pScreen.y + 40;

      // Background gradient
      const bgGrd = ctx.createLinearGradient(0,0,0,CH);
      if(s.zone===ZONE.OFFICE){
        bgGrd.addColorStop(0,"#12122a"); bgGrd.addColorStop(1,"#0a0a18");
      } else {
        bgGrd.addColorStop(0,"#0a1a0a"); bgGrd.addColorStop(1,"#050f05");
      }
      ctx.fillStyle=bgGrd; ctx.fillRect(0,0,CW,CH);

      // Collect draw order (back to front = painter's algorithm)
      const drawCalls = [];

      // Tiles
      for (let row = 0; row < ROWS; row++) {
        for (let col = 0; col < COLS; col++) {
          const type = map[row][col];
          const sc = isoToScreen(col, row, ox, oy);
          drawCalls.push({ sortY: col+row, sx:sc.x, sy:sc.y, type:"tile", tileType:type, col, row });
        }
      }

      // Player
      const psc = isoToScreen(s.player.x, s.player.y, ox, oy);
      drawCalls.push({ sortY: s.player.x+s.player.y, sx:psc.x, sy:psc.y, type:"player" });

      // Agents
      Object.entries(s.agents).forEach(([k,a]) => {
        const asc = isoToScreen(a.x, a.y, ox, oy);
        drawCalls.push({ sortY: a.x+a.y, sx:asc.x, sy:asc.y+a.bounce, type:"agent", key:k });
      });

      // Sort & draw
      drawCalls.sort((a,b) => a.sortY-b.sortY);
      drawCalls.forEach(dc => {
        if (dc.type === "tile") drawTile(ctx, dc.sx, dc.sy, dc.tileType, dc.col, dc.row, s.tick);
        else if (dc.type === "player") drawPlayer(ctx, dc.sx, dc.sy);
        else if (dc.type === "agent") {
          const drawer = AGENT_DRAWERS[dc.key];
          if (drawer) drawer(ctx, dc.sx, dc.sy);
          // Interaction prompt
          if (dc.key === closest) {
            ctx.fillStyle="#fff700"; ctx.font="bold 11px 'Courier New'";
            ctx.textAlign="center";
            ctx.fillText("[E] TALK", dc.sx, dc.sy-58);
          }
        }
      });

      // Zone transition overlay
      if (s.transitioning) {
        ctx.fillStyle="rgba(0,0,0,0.7)"; ctx.fillRect(0,0,CW,CH);
        ctx.fillStyle="#fff"; ctx.font="bold 20px 'Courier New'";
        ctx.textAlign="center"; ctx.fillText("✦ ENTERING NEW ZONE ✦", CW/2, CH/2);
      }

      animRef.current = requestAnimationFrame(loop);
    };

    animRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(animRef.current);
  }, [dialogue]);

  const currentAgent = dialogue ? AGENTS_CONFIG[dialogue.agent] : null;

  return (
    <div style={{
      display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center",
      minHeight:"100vh", background:"#050510",
      fontFamily:"'Courier New', monospace"
    }}>
      {/* Title */}
      <div style={{
        color:"#cc88ff", fontSize:"13px", letterSpacing:"4px", fontWeight:"bold",
        marginBottom:"8px", textTransform:"uppercase",
        textShadow:"0 0 20px #aa44ff, 0 0 40px #8800cc"
      }}>
        ◈ THE OFFICE WORLD · HUMAN ACTION MODEL ◈
      </div>

      <div style={{ position:"relative" }}>
        {/* Canvas */}
        <canvas ref={canvasRef} width={CW} height={CH}
          style={{ border:"2px solid #4422aa", display:"block", borderRadius:"4px",
            boxShadow:"0 0 40px rgba(100,40,200,0.5), 0 0 80px rgba(60,20,120,0.3)" }}
        />

        {/* HUD */}
        <div style={{
          position:"absolute", top:"10px", left:"12px",
          background:"rgba(10,5,30,0.85)", border:"1px solid #4422aa",
          borderRadius:"4px", padding:"6px 12px", color:"#aaaaff", fontSize:"10px"
        }}>
          <div style={{color:"#cc88ff",fontWeight:"bold",marginBottom:"3px"}}>
            {zone === ZONE.OFFICE ? "⬛ ANTHROPIC HQ" : "🌸 CHERRY BLOSSOM FOREST"}
          </div>
          <div style={{color:"#8888bb",fontSize:"9px"}}>WASD MOVE · E INTERACT · ESC CLOSE</div>
        </div>

        {/* Agent roster */}
        <div style={{
          position:"absolute", top:"10px", right:"12px",
          background:"rgba(10,5,30,0.85)", border:"1px solid #4422aa",
          borderRadius:"4px", padding:"6px 10px", fontSize:"9px"
        }}>
          {Object.entries(AGENTS_CONFIG).map(([k,v]) => (
            <div key={k} style={{
              display:"flex", alignItems:"center", gap:"6px",
              marginBottom:"3px", color:v.color
            }}>
              <span style={{
                width:"8px", height:"8px", borderRadius:"50%",
                background:v.color, display:"inline-block",
                boxShadow:`0 0 6px ${v.color}`
              }}/>
              {v.short}
            </div>
          ))}
        </div>

        {/* Portal hint */}
        <div style={{
          position:"absolute", bottom:"10px", left:"50%", transform:"translateX(-50%)",
          background:"rgba(10,5,30,0.75)", border:"1px solid #441188",
          borderRadius:"20px", padding:"4px 16px",
          color:"#9966cc", fontSize:"9px", letterSpacing:"2px"
        }}>
          STEP ON ◈ PORTAL ◈ TO TRAVEL · {zone === ZONE.OFFICE ? "FOREST AWAITS" : "OFFICE AWAITS"}
        </div>

        {/* Dialogue Box */}
        {dialogue && (
          <div style={{
            position:"absolute", bottom:"0", left:"0", right:"0",
            background:"rgba(8,4,22,0.97)",
            borderTop:"2px solid #6633cc",
            borderRadius:"0 0 4px 4px",
            padding:"14px 20px",
            minHeight:"110px"
          }}>
            <div style={{ display:"flex", gap:"14px", alignItems:"flex-start" }}>
              {/* Portrait */}
              <div style={{
                width:"60px", height:"60px", flexShrink:0,
                border:`2px solid ${currentAgent?.color || '#fff'}`,
                borderRadius:"6px",
                background:"rgba(30,10,60,0.9)",
                display:"flex", alignItems:"center", justifyContent:"center",
                fontSize:"28px",
                boxShadow:`0 0 15px ${currentAgent?.color || '#fff'}44`
              }}>
                {dialogue.agent === "dwight" ? "🕶️" :
                 dialogue.agent === "ralph" ? "👮" : "🥒"}
              </div>
              <div style={{ flex:1 }}>
                <div style={{
                  color: currentAgent?.color, fontWeight:"bold",
                  fontSize:"11px", marginBottom:"6px", letterSpacing:"2px"
                }}>
                  {currentAgent?.name?.toUpperCase()}
                </div>
                <div style={{
                  color:"#ddd", fontSize:"12px", lineHeight:"1.7",
                  minHeight:"40px"
                }}>
                  {loading ? (
                    <span style={{color:"#8866aa"}}>
                      ▌ {dialogue.agent === "dwight" ? "Analyzing threat level..." :
                         dialogue.agent === "ralph" ? "Thinking really hard..." :
                         "Calculating superior response..."}
                    </span>
                  ) : displayText}
                  {!loading && displayText && <span style={{
                    animation:"blink 0.7s infinite", color:"#cc88ff"
                  }}>▌</span>}
                </div>
                {!loading && displayText && (
                  <div style={{color:"#5544aa", fontSize:"9px", marginTop:"6px"}}>
                    [SPACE / ENTER] CLOSE
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        canvas { image-rendering: pixelated; }
      `}</style>
    </div>
  );
}
