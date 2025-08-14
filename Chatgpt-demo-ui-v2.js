import React, { useEffect, useMemo, useRef, useState } from "react";

/*********************
 * HYBRID AI COUNCIL — OPTIMAL UI (React Preview)
 * Palette: cyberpunk dark (#15141c bg, #232046 accent)
 * Typography: Inter
 * Feel: Linear + Notion + Miro, glassmorphic
 * NOTE: This is a Canvas preview. Your project code remains Svelte.
 *********************/

// Theme
const BG = "#15141c";
const ACCENT = "#232046";
const TEXT = "#ffffff";
const MUTED = "#a1a1aa";

// Types
 type Mode = "MANUAL" | "SUPERVISED" | "AUTONOMOUS";
 type Route = "dashboard" | "treasury" | "agents" | "agentDetail" | "actions" | "pheromind";
 type Verify = "pass" | "flag" | "block";

 type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
  verifying?: boolean;
  verified?: Verify;
  entropy?: number; // semantic entropy proxy
  route?: "pass" | "suggest" | "block";
  fallback?: boolean;
  costUsd?: number;
};

 type Approval = { id: string; summary: string; cost: number; risk: string };

 type Agent = {
  id: string;
  name: string;
  role: string;
  revenue: number;
  cost: number;
  pnl: number;
  status: "🟢" | "🟡" | "🔴";
  throttle: number; // budget cap slider
  paused: boolean;
};

// Sample data
const seedAgents: Agent[] = [
  { id: "sarah", name: "Sarah", role: "ContentCreation_Agent", revenue: 347, cost: 89, pnl: 258, status: "🟢", throttle: 120, paused: false },
  { id: "stock", name: "StockAnalyst_Agent", role: "StockAnalyst_Agent", revenue: 190, cost: 34, pnl: 156, status: "🟡", throttle: 80, paused: false },
  { id: "market", name: "MarketResearch_Agent", role: "MarketResearch_Agent", revenue: 150, cost: 18, pnl: 132, status: "🟢", throttle: 60, paused: false },
];

const actionFeed = [
  { t: "09:42", text: "StockAnalyst_Agent purchased $AAPL analysis from Bloomberg API (-$12)" },
  { t: "10:03", text: "MarketResearch_Agent completed client report (+$150)" },
  { t: "11:17", text: "Verifier flagged budget increase request (>$500)" },
];

const treasuryDays = Array.from({ length: 30 }).map((_, i) => ({
  d: `D${i + 1}`,
  balance: 2100 + i * 40 + Math.sin(i) * 60,
  spend: 60 + Math.max(0, Math.sin(i / 2)) * 40,
  cap: 120 + (i % 5) * 5,
}));

const pheromindNodes = [
  { id: "Bitcoin", strength: 0.86 },
  { id: "Inflation", strength: 0.72 },
  { id: "Gold", strength: 0.68 },
  { id: "Safe Haven Assets", strength: 0.74 },
  { id: "AI regulation", strength: 0.87 },
  { id: "European markets", strength: 0.81 },
  { id: "Remote work", strength: 0.73 },
  { id: "Commercial real estate decline", strength: 0.73 },
];

const pheromindEdges: Array<{ a: string; b: string; weight: number }> = [
  { a: "Bitcoin", b: "Inflation", weight: 0.6 },
  { a: "Inflation", b: "Gold", weight: 0.55 },
  { a: "Gold", b: "Safe Haven Assets", weight: 0.7 },
  { a: "AI regulation", b: "European markets", weight: 0.87 },
  { a: "Remote work", b: "Commercial real estate decline", weight: 0.73 },
];

// Helpers
const Glass: React.FC<React.PropsWithChildren<{ className?: string }>> = ({ className, children }) => (
  <div className={`backdrop-blur-sm bg-white/5 border border-white/10 rounded-xl shadow-xl ${className || ""}`}>{children}</div>
);

const Chip: React.FC<React.PropsWithChildren<{ className?: string }>> = ({ className, children }) => (
  <span className={`px-2 py-1 rounded-md text-xs border ${className || "bg-white/5 border-white/10 text-zinc-300"}`}>{children}</span>
);

// Components
const ModeRail: React.FC<{ mode: Mode }> = ({ mode }) => {
  const color = mode === "MANUAL" ? "bg-red-600/60" : mode === "SUPERVISED" ? "bg-amber-500/60" : "bg-emerald-600/60";
  return (
    <div className={`w-full h-8 backdrop-blur-sm border-b border-white/10 flex items-center justify-between px-3 ${color}`}>
      <div className="text-xs text-white/90 tracking-wide">
        {mode === "MANUAL" && "Manual • Every action awaits approval"}
        {mode === "SUPERVISED" && "Supervised • Auto ≤ $50 • Flag ≥ $500 • Fallback < 0.30"}
        {mode === "AUTONOMOUS" && "Autonomous • Within constitutional limits"}
      </div>
      <div className="text-[11px] text-white/80 space-x-3">
        <span>Legal floor ≥ 0.85</span><span>Financial floor ≥ 0.75</span>
      </div>
    </div>
  );
};

const SystemHealth: React.FC = () => (
  <div className="flex items-center gap-2">
    <Chip className="bg-emerald-500/20 border-white/10 text-emerald-300">Compliance 96%</Chip>
    <Chip>LLM latency 210ms</Chip>
    <Chip>Queue 2</Chip>
    <Chip>Local TG 98%</Chip>
    <Chip>Cloud APIs 94%</Chip>
    <Chip className="bg-fuchsia-500/20 border-white/10 text-fuchsia-300">Violations 2</Chip>
  </div>
);

const TopNav: React.FC<{ mode: Mode; setMode: (m: Mode) => void; onApprovals: () => void; route: Route; setRoute: (r: Route)=>void }>
= ({ mode, setMode, onApprovals, route, setRoute }) => {
  return (
    <div className="w-full flex items-center justify-between px-4 py-3">
      <div className="flex items-center gap-4">
        <div className="h-8 w-8 rounded-lg bg-fuchsia-600/40 border border-fuchsia-400/30" />
        <div className="text-white font-semibold tracking-wide">Hybrid AI Council</div>
        <div className="hidden md:flex items-center gap-2 text-xs text-zinc-400 ml-2">
          <button onClick={()=>setRoute('dashboard')} className={`px-2 py-1 rounded ${route==='dashboard'?'bg-white/10 text-white':'hover:bg-white/10'}`}>Dashboard</button>
          <button onClick={()=>setRoute('treasury')} className={`px-2 py-1 rounded ${route==='treasury'?'bg-white/10 text-white':'hover:bg-white/10'}`}>Treasury</button>
          <button onClick={()=>setRoute('agents')} className={`px-2 py-1 rounded ${route==='agents'?'bg-white/10 text-white':'hover:bg-white/10'}`}>Agents</button>
          <button onClick={()=>setRoute('actions')} className={`px-2 py-1 rounded ${route==='actions'?'bg-white/10 text-white':'hover:bg-white/10'}`}>Action Log</button>
          <button onClick={()=>setRoute('pheromind')} className={`px-2 py-1 rounded ${route==='pheromind'?'bg-white/10 text-white':'hover:bg-white/10'}`}>Pheromind</button>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <SystemHealth />
        <div className="flex items-center gap-1 backdrop-blur-sm bg-white/5 border border-white/10 rounded-xl shadow-xl p-1">
          {(["MANUAL","SUPERVISED","AUTONOMOUS"] as Mode[]).map(m => (
            <button key={m} onClick={()=>setMode(m)} className={`px-3 py-1 rounded-lg transition-all ${mode===m ? (m==='MANUAL'?'bg-red-500/20 text-red-300': m==='SUPERVISED'?'bg-amber-500/20 text-amber-300':'bg-emerald-500/20 text-emerald-300') : 'text-zinc-400 hover:text-white'}`}>{m==='MANUAL'?'Manual':m==='SUPERVISED'?'Supervised':'Autonomous'}</button>
          ))}
        </div>
        <button onClick={onApprovals} className="relative px-3 py-1 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10">
          Approvals
          <span className="absolute -top-1 -right-1 bg-amber-500 text-black text-[10px] px-1.5 py-0.5 rounded-full">3</span>
        </button>
      </div>
    </div>
  );
};

const Sidebar: React.FC<{ collapsed: boolean; setCollapsed:(v:boolean)=>void; route: Route; setRoute:(r:Route)=>void }>
= ({ collapsed, setCollapsed, route, setRoute }) => {
  const items: { label: string; href: Route }[] = [
    { label: 'Dashboard', href: 'dashboard' },
    { label: 'Treasury', href: 'treasury' },
    { label: 'Agents', href: 'agents' },
    { label: 'Action Log', href: 'actions' },
    { label: 'Pheromind', href: 'pheromind' }
  ];
  return (
    <Glass className={`h-full ${collapsed ? 'w-16' : 'w-64'} p-3 flex flex-col transition-all duration-200`}>
      <button className="self-end text-zinc-400 hover:text-white" onClick={()=>setCollapsed(!collapsed)} aria-label="Toggle sidebar">{collapsed ? '→' : '←'}</button>
      {!collapsed && <div className="text-zinc-200 font-semibold mt-2 mb-2">Navigation</div>}
      <nav className="space-y-2 overflow-auto">
        {items.map(it => {
          const active = route === it.href;
          return (
            <button key={it.href} onClick={()=>setRoute(it.href)} className={`block w-full text-left p-3 rounded-lg border transition-all ${active ? 'bg-white/10 border-white/20 text-white' : 'bg-white/5 border-white/10 text-zinc-300 hover:bg-white/10'} ${collapsed ? 'text-xs text-center' : ''}`}>{collapsed ? it.label[0] : it.label}</button>
          );
        })}
      </nav>
    </Glass>
  );
};

const DecisionTimeline: React.FC<{ m: Message }> = ({ m }) => (
  <div className="flex items-center gap-2 text-[11px] text-zinc-400 mt-1">
    <Chip>Generator</Chip>
    <span>→</span>
    <Chip className={m.verified==='pass' ? 'bg-emerald-500/20 text-emerald-300 border-white/10' : m.verified==='flag' ? 'bg-amber-500/20 text-amber-300 border-white/10' : 'bg-red-500/20 text-red-300 border-white/10'}>
      {m.verified==='pass'?'Checked ✓':m.verified==='flag'?'Needs approval ⚑':'Blocked ✖'}{m.entropy!=null && <span className="ml-1 text-zinc-500">entropy {m.entropy.toFixed(2)}</span>}
    </Chip>
    <span>→</span>
    <Chip>Router {m.route ?? 'pass'}</Chip>
    {m.fallback && <span className="ml-1 text-amber-300">fallback used</span>}
  </div>
);

const ChatBubble: React.FC<{ m: Message; mode: Mode; onQueue:(a:Approval)=>void }> = ({ m, mode, onQueue }) => (
  <div className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
    <div className={`max-w-[70%] p-3 rounded-2xl shadow-lg border ${m.role === 'user' ? 'bg-[#232046] border-white/10' : 'bg-[#1f1f23] border-white/10'}`}>
      <div className="text-zinc-100 whitespace-pre-wrap leading-relaxed">{m.content}</div>
      <DecisionTimeline m={m} />
      <div className="mt-2 flex items-center gap-2 text-[11px] text-zinc-400">
        {m.verifying && <Chip className="bg-sky-500/20 text-sky-300 border-white/10">Verifying…</Chip>}
        {mode === 'MANUAL' && (
          <>
            <Chip>Cost ${m.costUsd?.toFixed(2) || '0.02'}</Chip>
            <button onClick={()=>onQueue({ id:m.id, summary:'Approve action: rebalancing 5–8% to ETH', cost:m.costUsd||0.03, risk:'financial'})} className="px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-400/20 hover:bg-emerald-500/30">Queue</button>
          </>
        )}
      </div>
    </div>
  </div>
);

const ChatPanel: React.FC<{ mode: Mode; onQueue:(a:Approval)=>void }> = ({ mode, onQueue }) => {
  const [messages, setMessages] = useState<Message[]>([
    { id: '1', role: 'user', content: 'Help me analyze the crypto market for portfolio rebalancing' },
    { id: '2', role: 'ai', content: 'Understood. Pulling BTC/ETH macro, funding rates, and correlation with risk-on indexes…', verifying: true }
  ]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const streamRef = useRef<number | null>(null);

  const send = () => {
    if (!input.trim()) return;
    const user: Message = { id: crypto.randomUUID(), role: 'user', content: input };
    setMessages((m) => [...m, user]);
    setInput("");

    const aiId = crypto.randomUUID();
    const target: Message = { id: aiId, role: 'ai', content: "", verifying: true };
    setMessages((m) => [...m, target]);
    const tokens = "Drafting analysis… Funding rates neutral. BTC–ETH correlation falling; consider rebalancing 5–8% toward ETH if risk tolerance allows.".split(" ");
    let i = 0;
    setStreaming(true);
    streamRef.current = window.setInterval(() => {
      i++;
      setMessages((m) => m.map((mm) => mm.id === aiId ? { ...mm, content: tokens.slice(0, i).join(" ") } : mm));
      if (i >= tokens.length) {
        window.clearInterval(streamRef.current!);
        setStreaming(false);
        const verified: Verify = Math.random() < 0.1 ? 'block' : (Math.random() < 0.3 ? 'flag' : 'pass');
        setMessages((m) => m.map((mm) => mm.id === aiId ? { ...mm, verifying: false, verified, route: verified==='pass'?'pass': verified==='flag'?'suggest':'block', entropy: Math.random()*0.5 + 0.3, costUsd: 0.03, fallback: verified==='block' && Math.random() < 0.5 } : mm));
      }
    }, 45);
  };

  useEffect(()=>()=>{ if (streamRef.current) window.clearInterval(streamRef.current); },[]);

  return (
    <Glass className="h-full w-full flex flex-col p-4">
      <div className="flex-1 overflow-auto space-y-4 pr-2">
        {messages.map((m) => (
          <ChatBubble key={m.id} m={m} mode={mode} onQueue={onQueue} />
        ))}
      </div>
      <div className="mt-3 flex items-center gap-2">
        <button className="p-2 rounded-lg bg-white/5 text-zinc-300 border border-white/10 hover:bg-white/10" title="Voice input">🎙️</button>
        <button className="p-2 rounded-lg bg-white/5 text-zinc-300 border border-white/10 hover:bg-white/10" title="Voice output">🔊</button>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Type a message…"
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-fuchsia-500/30"
        />
        <button onClick={send} disabled={streaming} className="px-4 py-2 rounded-lg bg-fuchsia-600 text-white hover:bg-fuchsia-500 disabled:opacity-50 transition-all">Send</button>
      </div>
    </Glass>
  );
};

const ApprovalsDrawer: React.FC<{ open:boolean; items:Approval[]; onClose:()=>void; onApprove:(id:string)=>void; onReject:(id:string)=>void }>
= ({ open, items, onClose, onApprove, onReject }) => (
  <div className={`fixed top-0 right-0 h-full w-[360px] bg-[#1f1f23]/95 backdrop-blur-md border-l border-white/10 shadow-xl transition-transform duration-200 ${open ? 'translate-x-0' : 'translate-x-full'}`}>
    <div className="p-3 border-b border-white/10 flex items-center justify-between">
      <div className="text-sm font-semibold">Pending Approvals</div>
      <button onClick={onClose} className="text-zinc-400 hover:text-white">✕</button>
    </div>
    <div className="p-3 space-y-2 overflow-auto h-full">
      {items.length===0 && <div className="text-zinc-400 text-sm">No pending approvals.</div>}
      {items.map((it) => (
        <div key={it.id} className="p-3 rounded-lg bg-white/5 border border-white/10">
          <div className="text-zinc-100 text-sm">{it.summary}</div>
          <div className="text-[11px] text-zinc-400 mt-1">Cost ${it.cost.toFixed(2)} • Risk {it.risk}</div>
          <div className="mt-2 flex gap-2">
            <button onClick={()=>onApprove(it.id)} className="px-2 py-1 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/20 hover:bg-emerald-500/30">Approve</button>
            <button onClick={()=>onReject(it.id)} className="px-2 py-1 rounded bg-red-500/20 text-red-300 border border-red-400/20 hover:bg-red-500/30">Reject</button>
          </div>
        </div>
      ))}
    </div>
  </div>
);

const AgentsPanel: React.FC<{ agents:Agent[]; setAgents: (f:(a:Agent[])=>Agent[])=>void; onOpenDetail:(id:string)=>void }>
= ({ agents, setAgents, onOpenDetail }) => (
  <Glass className="p-4">
    <div className="text-zinc-200 font-semibold mb-3">Agents</div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {agents.map(a => (
        <div key={a.id} className="p-3 bg-white/5 rounded-xl border border-white/10">
          <div className="flex items-center justify-between">
            <div className="text-zinc-100 font-medium">{a.name}</div>
            <div className="text-zinc-400 text-sm">{a.role}</div>
          </div>
          <div className="mt-2 flex items-center gap-4 text-sm text-zinc-300">
            <span>Revenue <span className="text-emerald-300">${a.revenue}</span></span>
            <span>Cost <span className="text-rose-300">${a.cost}</span></span>
            <span>P&L <span className={a.pnl>=0?"text-emerald-300":"text-rose-300"}>${a.pnl}</span></span>
            <span className="ml-auto">{a.status}</span>
          </div>
          <div className="mt-3 flex items-center gap-3 text-xs text-zinc-300">
            <label className="w-20">Budget</label>
            <input type="range" min={0} max={500} value={a.throttle}
                   onChange={(e)=>setAgents(prev=>prev.map(x=>x.id===a.id?{...x, throttle: Number((e.target as HTMLInputElement).value)}:x))}
                   className="w-full accent-fuchsia-500" />
            <button onClick={()=>setAgents(prev=>prev.map(x=>x.id===a.id?{...x, paused:!x.paused}:x))}
                    className="px-2 py-1 rounded bg-white/5 border border-white/10 hover:bg-white/10">{a.paused? 'Resume':'Pause'}</button>
            <button onClick={()=>onOpenDetail(a.id)} className="px-2 py-1 rounded bg-white/5 border border-white/10 hover:bg-white/10">Open ↗︎</button>
          </div>
        </div>
      ))}
    </div>
  </Glass>
);

const TreasuryPanel: React.FC = () => {
  const total = treasuryDays.at(-1)?.balance ?? 0;
  // Simple dual series mini chart: cap vs spend
  const ptsSpend = treasuryDays.map((t,i)=>{
    const x = (i/(treasuryDays.length-1))*100;
    const y = 100 - (t.spend/200)*100;
    return `${x},${y}`;
  }).join(' ');
  const ptsCap = treasuryDays.map((t,i)=>{
    const x = (i/(treasuryDays.length-1))*100;
    const y = 100 - (t.cap/250)*100;
    return `${x},${y}`;
  }).join(' ');
  return (
    <div className="space-y-4">
      <Glass className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-zinc-200 font-semibold">Treasury</div>
          <div className="text-zinc-400 text-sm">Balance ${total.toFixed(0)} • $1,203 allocated</div>
        </div>
        <div className="h-28 mt-2">
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
            <polyline points={ptsCap} fill="none" stroke="#60a5fa" strokeWidth={1.2} opacity={0.8} />
            <polyline points={ptsSpend} fill="none" stroke="#a78bfa" strokeWidth={1.2} opacity={0.9} />
          </svg>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-3 text-sm text-zinc-300">
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">Variance today <div className="text-fuchsia-300 text-lg">-$32</div></div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">Projected runway <div className="text-emerald-300 text-lg">42d</div></div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">Flag threshold <div className="text-emerald-300 text-lg">$500</div></div>
        </div>
      </Glass>
      <Glass className="p-4">
        <div className="text-zinc-200 font-semibold mb-2">Costs</div>
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300">Verifier Costs <div className="text-fuchsia-300 text-lg">$4.18</div></div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300">API Usage <div className="text-fuchsia-300 text-lg">$39.60</div></div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300">GPU Hours <div className="text-fuchsia-300 text-lg">$12.00</div></div>
        </div>
      </Glass>
    </div>
  );
};

const ActionLogPanel: React.FC = () => (
  <Glass className="p-4">
    <div className="flex items-center justify-between">
      <div className="text-zinc-200 font-semibold">Action Log</div>
      <div className="text-xs text-zinc-400">Today</div>
    </div>
    <div className="space-y-2 max-h-64 overflow-auto pr-1 mt-2">
      {actionFeed.map((e,i)=>(
        <div key={i} className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-all">
          <div className="text-[11px] text-zinc-500">{e.t}</div>
          <div className="text-zinc-100 text-sm">{e.text}</div>
        </div>
      ))}
    </div>
  </Glass>
);

const PheromindVisualization: React.FC = () => {
  const nodes = pheromindNodes; const edges = pheromindEdges; const R = 110;
  const coords = useMemo(()=> nodes.map((n,i)=>({ id:n.id, x: 150 + Math.cos((i/nodes.length)*Math.PI*2)*R, y: 120 + Math.sin((i/nodes.length)*Math.PI*2)*R, r: 8 + n.strength*8 })),[nodes.length]);
  const get = (id:string)=>coords.find(c=>c.id===id)!;
  const insights = [
    { text: 'AI regulation ↔ European markets', conf: 0.87 },
    { text: 'Bitcoin → Inflation → Gold', conf: 0.73 }
  ];
  return (
    <Glass className="p-4">
      <div className="text-zinc-200 font-semibold mb-2">Pheromind — Subconscious Insights</div>
      <div className="grid md:grid-cols-3 gap-3">
        <svg viewBox="0 0 300 240" className="md:col-span-2 w-full h-64 bg-white/5 rounded-xl border border-white/10">
          {edges.map((e,i)=>{ const a=get(e.a), b=get(e.b); return (
            <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#a78bfa" strokeOpacity={0.2 + e.weight*0.6} strokeWidth={1 + e.weight*2} />
          );})}
          {coords.map((c,i)=> (
            <g key={i}>
              <circle cx={c.x} cy={c.y} r={c.r} fill="#7c3aed" opacity={0.75} />
              <text x={c.x} y={c.y-(c.r+6)} textAnchor="middle" fontSize={11} fill="#d4d4d8">{c.id}</text>
            </g>
          ))}
        </svg>
        <div className="md:col-span-1">
          <div className="p-3 bg-white/5 border border-white/10 rounded-lg">
            <div className="text-sm text-zinc-200 font-medium mb-2">Insights</div>
            {insights.map((s,i)=> (
              <div key={i} className="flex items-center justify-between py-1">
                <div className="text-sm text-zinc-300">{s.text}</div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-zinc-400">conf {Math.round(s.conf*100)}%</span>
                  <button className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/20">Promote</button>
                  <button className="px-2 py-0.5 rounded bg-white/5 border border-white/10">Snooze</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </Glass>
  );
};

// Pages
const Dashboard: React.FC<{ mode:Mode; onQueue:(a:Approval)=>void; agents:Agent[]; setAgents:(f:(a:Agent[])=>Agent[])=>void; onOpenAgent:(id:string)=>void }>
= ({ mode, onQueue, agents, setAgents, onOpenAgent }) => (
  <div className="grid grid-cols-12 gap-4">
    <div className="col-span-12 lg:col-span-7">
      <ChatPanel mode={mode} onQueue={onQueue} />
    </div>
    <div className="col-span-12 lg:col-span-5 space-y-4">
      <TreasuryPanel />
      <AgentsPanel agents={agents} setAgents={setAgents} onOpenDetail={onOpenAgent} />
      <ActionLogPanel />
      <PheromindVisualization />
    </div>
  </div>
);

const TreasuryPage: React.FC = () => (
  <div className="space-y-4">
    <TreasuryPanel />
    <Glass className="p-4">
      <div className="flex items-center justify-between">
        <div className="text-zinc-200 font-semibold">Rules & Caps</div>
        <button className="px-3 py-1 rounded-lg bg-fuchsia-600 hover:bg-fuchsia-500 transition-all">Edit</button>
      </div>
      <ul className="mt-3 text-sm text-zinc-300 space-y-2">
        <li>• Financial flag threshold: <span className="text-emerald-300">$500</span></li>
        <li>• Daily VaR limit: <span className="text-emerald-300">$250</span> (example)</li>
        <li>• Panic flatten: enabled (heartbeat 24h)</li>
      </ul>
    </Glass>
  </div>
);

const AgentsPage: React.FC<{ agents:Agent[]; setAgents:(f:(a:Agent[])=>Agent[])=>void; open:(id:string)=>void }>
= ({ agents, setAgents, open }) => (
  <div className="space-y-4">
    <AgentsPanel agents={agents} setAgents={setAgents} onOpenDetail={open} />
  </div>
);

const AgentDetailPage: React.FC<{ agent:Agent; back:()=>void }>
= ({ agent, back }) => (
  <div className="space-y-4">
    <button onClick={back} className="text-zinc-400 hover:text-white">← Back</button>
    <Glass className="p-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xl font-semibold">Agent: {agent.name}</div>
          <div className="text-zinc-400 text-sm">{agent.role}</div>
        </div>
        <div className="text-emerald-300 text-2xl">${agent.pnl}</div>
      </div>
      <div className="mt-4 grid md:grid-cols-2 gap-3">
        <div className="p-3 bg-white/5 border border-white/10 rounded-lg">Completed: Client report (+$150)</div>
        <div className="p-3 bg-white/5 border border-white/10 rounded-lg">Purchased: Data API (-$12)</div>
      </div>
      <div className="mt-4 flex items-center gap-3 text-sm text-zinc-300">
        <label>Budget</label>
        <input type="range" min={0} max={500} defaultValue={agent.throttle} className="w-64 accent-fuchsia-500" />
        <button className="px-2 py-1 rounded bg-white/5 border border-white/10 hover:bg-white/10">Pause</button>
      </div>
    </Glass>
  </div>
);

const ActionsPage: React.FC = () => (
  <div className="space-y-4">
    <ActionLogPanel />
  </div>
);

const PheromindPage: React.FC = () => (
  <div className="space-y-4">
    <PheromindVisualization />
  </div>
);

// App Shell
const App: React.FC = () => {
  const [mode, setMode] = useState<Mode>("SUPERVISED");
  const [collapsed, setCollapsed] = useState(false);
  const [route, setRoute] = useState<Route>("dashboard");
  const [approvalsOpen, setApprovalsOpen] = useState(false);
  const [approvals, setApprovals] = useState<Approval[]>([
    { id: 'ap1', summary: 'Increase ad budget by $60 (under cap)', cost: 0.01, risk: 'financial' },
    { id: 'ap2', summary: 'Run programmatic SEO batch (20 pages)', cost: 0.12, risk: 'content' },
    { id: 'ap3', summary: 'Purchase market data API ($18)', cost: 0.02, risk: 'financial' },
  ]);
  const [agents, setAgents] = useState<Agent[]>(seedAgents);
  const [agentDetail, setAgentDetail] = useState<Agent | null>(null);

  const onQueue = (a:Approval) => { setApprovals(prev => [{...a, id: 'ap'+(prev.length+1)}, ...prev]); setApprovalsOpen(true); };
  const approve = (id:string) => setApprovals(prev => prev.filter(x=>x.id!==id));
  const reject = (id:string) => setApprovals(prev => prev.filter(x=>x.id!==id));

  useEffect(()=>{
    if (agentDetail) setRoute('agentDetail');
  },[agentDetail]);

  return (
    <div className="min-h-screen" style={{ background: BG, color: TEXT }}>
      <div className="border-b border-white/10 sticky top-0 z-30 bg-black/20 backdrop-blur-md">
        <TopNav mode={mode} setMode={setMode} onApprovals={()=>setApprovalsOpen(true)} route={route} setRoute={setRoute} />
        <ModeRail mode={mode} />
      </div>

      <div className="grid grid-cols-12 gap-4 p-4">
        <div className="col-span-12 md:col-span-3 lg:col-span-2">
          <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} route={route} setRoute={setRoute} />
        </div>
        <div className="col-span-12 md:col-span-9 lg:col-span-10">
          {route==='dashboard' && (
            <Dashboard mode={mode} onQueue={onQueue} agents={agents} setAgents={setAgents} onOpenAgent={(id)=>setAgentDetail(agents.find(a=>a.id===id) || null)} />
          )}
          {route==='treasury' && (<TreasuryPage />)}
          {route==='agents' && (<AgentsPage agents={agents} setAgents={setAgents} open={(id)=>setAgentDetail(agents.find(a=>a.id===id) || null)} />)}
          {route==='agentDetail' && agentDetail && (<AgentDetailPage agent={agentDetail} back={()=>{ setAgentDetail(null); setRoute('agents'); }} />)}
          {route==='actions' && (<ActionsPage />)}
          {route==='pheromind' && (<PheromindPage />)}
        </div>
      </div>

      <ApprovalsDrawer open={approvalsOpen} items={approvals} onClose={()=>setApprovalsOpen(false)} onApprove={approve} onReject={reject} />
    </div>
  );
};

export default function Preview() { return <App />; }
