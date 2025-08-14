import React, { useEffect, useMemo, useRef, useState } from "react";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, AreaChart, Area } from "recharts";

// Tailwind palette
const BG = "#15141c";
const ACCENT = "#232046";
const TEXT = "#ffffff";
const MUTED = "#a1a1aa";

// --- Types (preview only) ---
type Mode = "MANUAL" | "SUPERVISED" | "AUTONOMOUS";

type Message = {
  id: string;
  role: "user" | "ai";
  content: string;
  verifying?: boolean;
  verified?: "pass" | "flag" | "block";
  costUsd?: number;
};

// --- Sample data ---
const initialMessages: Message[] = [
  { id: "1", role: "user", content: "Help me analyze the crypto market for portfolio rebalancing" },
  { id: "2", role: "ai", content: "Understood. Pulling BTC/ETH macro, funding rates, and correlation with risk-on indexes…", verifying: true },
];

const treasuryHistory = Array.from({ length: 14 }).map((_, i) => ({
  d: `D${i+1}`,
  balance: 2000 + i * 60 + (Math.sin(i) * 50),
  allocated: 900 + i * 20,
}));

const agentCards = [
  { name: "Sarah", role: "ContentCreation_Agent", revenue: 347, cost: 89, pnl: 347-89, status: "🟢" },
  { name: "StockAnalyst_Agent", role: "StockAnalyst_Agent", revenue: 190, cost: 34, pnl: 156, status: "🟡" },
  { name: "MarketResearch_Agent", role: "MarketResearch_Agent", revenue: 150, cost: 18, pnl: 132, status: "🟢" },
];

const actionFeed = [
  { t: "09:42", text: "StockAnalyst_Agent purchased $AAPL analysis from Bloomberg API (-$12)" },
  { t: "10:03", text: "MarketResearch_Agent completed client report (+$150)" },
  { t: "11:17", text: "Constitutional Verifier flagged budget increase request (>$500)" },
];

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

// --- UI Helpers ---
const Badge: React.FC<{ color?: string; children: React.ReactNode }> = ({ color = "bg-zinc-700/60", children }) => (
  <span className={`px-2 py-1 rounded-md text-xs ${color} text-white/90 border border-white/10`}>{children}</span>
);

const Glass: React.FC<React.PropsWithChildren<{ className?: string }>> = ({ className, children }) => (
  <div className={`backdrop-blur-sm bg-white/5 border border-white/10 rounded-xl shadow-xl ${className || ""}`}>{children}</div>
);

// --- Components ---

const OperationalModeControl: React.FC<{ mode: Mode; setMode: (m: Mode) => void }> = ({ mode, setMode }) => {
  const modes: Mode[] = ["MANUAL", "SUPERVISED", "AUTONOMOUS"];
  const colors: Record<Mode, string> = {
    MANUAL: "bg-red-500/20 text-red-300",
    SUPERVISED: "bg-amber-500/20 text-amber-300",
    AUTONOMOUS: "bg-emerald-500/20 text-emerald-300",
  };
  return (
    <div className="flex items-center gap-3">
      <div className="text-zinc-300 text-sm">Mode</div>
      <Glass className="flex items-center gap-1 p-1">
        {modes.map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`px-3 py-1 rounded-lg transition-all duration-200 ${mode === m ? colors[m] : "text-zinc-400 hover:text-white"}`}
            aria-pressed={mode === m}
          >
            {m === "MANUAL" && "Manual"}
            {m === "SUPERVISED" && "Supervised"}
            {m === "AUTONOMOUS" && "Autonomous"}
          </button>
        ))}
      </Glass>
    </div>
  );
};

const SystemHealth: React.FC = () => (
  <div className="flex items-center gap-3 text-xs text-zinc-300">
    <Badge color="bg-emerald-500/20 text-emerald-300">Compliance 96%</Badge>
    <Badge>Local TigerGraph <span className="text-emerald-400">98%</span></Badge>
    <Badge>Cloud APIs <span className="text-amber-300">94%</span></Badge>
    <Badge>Tailscale <span className="text-emerald-400">Connected</span></Badge>
    <Badge color="bg-fuchsia-500/20 text-fuchsia-300">Violations 2</Badge>
  </div>
);

const Sidebar: React.FC<{ collapsed: boolean; setCollapsed: (v: boolean) => void }> = ({ collapsed, setCollapsed }) => (
  <Glass className={`h-full ${collapsed ? "w-16" : "w-64"} p-3 flex flex-col transition-all duration-200`}>
    <button className="self-end text-zinc-400 hover:text-white" onClick={() => setCollapsed(!collapsed)} aria-label="Toggle sidebar">{collapsed ? "→" : "←"}</button>
    <div className="text-zinc-200 font-semibold mt-2 mb-2">{collapsed ? "" : "Conversations"}</div>
    <div className="space-y-2 overflow-auto">
      {[
        "Crypto Rebalancing",
        "Ads Budget Review",
        "Lead Gen Experiment",
        "Weekly Snapshot",
      ].map((t, i) => (
        <div key={i} className={`p-3 rounded-lg bg-white/5 hover:bg-white/10 cursor-pointer ${collapsed ? "text-xs" : ""}`}>{collapsed ? t[0] : t}</div>
      ))}
    </div>
  </Glass>
);

const ChatBubble: React.FC<{ m: Message; mode: Mode }> = ({ m, mode }) => (
  <div className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
    <div className={`max-w-[70%] p-3 rounded-2xl shadow-lg border ${m.role === "user" ? "bg-[#232046] border-white/10" : "bg-[#1f1f23] border-white/10"}`}>
      <div className="text-zinc-100 whitespace-pre-wrap leading-relaxed">{m.content}</div>
      <div className="mt-2 flex items-center gap-2 text-[11px] text-zinc-400">
        {m.verifying && <Badge color="bg-sky-500/20 text-sky-300">Verifying…</Badge>}
        {m.verified && <Badge color={m.verified === "pass" ? "bg-emerald-500/20 text-emerald-300" : m.verified === "flag" ? "bg-amber-500/20 text-amber-300" : "bg-red-500/20 text-red-300"}>Verifier: {m.verified}</Badge>}
        {mode === "MANUAL" && (
          <>
            <Badge>Cost ${m.costUsd?.toFixed(2) || "0.02"}</Badge>
            <button className="px-2 py-1 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-400/20 hover:bg-emerald-500/30">Approve</button>
            <button className="px-2 py-1 rounded-md bg-red-500/20 text-red-300 border border-red-400/20 hover:bg-red-500/30">Reject</button>
          </>
        )}
      </div>
    </div>
  </div>
);

const ChatInterface: React.FC<{ mode: Mode }> = ({ mode }) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const streamRef = useRef<number | null>(null);

  const send = () => {
    if (!input.trim()) return;
    const user: Message = { id: crypto.randomUUID(), role: "user", content: input };
    setMessages((m) => [...m, user]);
    setInput("");

    // Simulated stream + verify badge
    const aiId = crypto.randomUUID();
    const target: Message = { id: aiId, role: "ai", content: "", verifying: true };
    setMessages((m) => [...m, target]);
    const tokens = "Drafting analysis… Funding rates currently neutral. BTC-ETH correlation falling; consider rebalancing 5–8% toward ETH if risk tolerance allows.".split(" ");
    let i = 0;
    setStreaming(true);
    streamRef.current = window.setInterval(() => {
      i++;
      setMessages((m) => m.map((mm) => mm.id === aiId ? { ...mm, content: tokens.slice(0, i).join(" ") } : mm));
      if (i >= tokens.length) {
        window.clearInterval(streamRef.current!);
        setStreaming(false);
        setMessages((m) => m.map((mm) => mm.id === aiId ? { ...mm, verifying: false, verified: Math.random() > 0.15 ? "pass" : "flag", costUsd: 0.03 } : mm));
      }
    }, 60);
  };

  return (
    <Glass className="h-full w-full flex flex-col p-4">
      <div className="flex-1 overflow-auto space-y-4 pr-2">
        {messages.map((m) => (
          <ChatBubble key={m.id} m={m} mode={mode} />
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
      {/* TODO: replace simulated streaming with WebSocket to FastAPI */}
    </Glass>
  );
};

const KIPDashboard: React.FC = () => {
  const net = agentCards.reduce((a,c)=>a+c.pnl,0);
  return (
    <div className="space-y-4">
      <Glass className="p-4">
        <div className="flex items-center justify-between">
          <div className="text-zinc-200 font-semibold">Treasury</div>
          <div className="text-zinc-400 text-sm">$2,847 available • $1,203 allocated</div>
        </div>
        <div className="h-28 mt-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={treasuryHistory}>
              <defs>
                <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#a78bfa" stopOpacity={0.7} />
                  <stop offset="100%" stopColor="#a78bfa" stopOpacity={0.05} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="d" stroke="#a1a1aa" tick={{ fill: MUTED, fontSize: 12 }} />
              <YAxis stroke="#a1a1aa" tick={{ fill: MUTED, fontSize: 12 }} />
              <Tooltip contentStyle={{ background: "#1f1f23", border: "1px solid rgba(255,255,255,0.1)", color: "#fff" }} />
              <Area dataKey="balance" stroke="#a78bfa" fill="url(#grad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="mt-3 text-sm text-zinc-300">Net P&L (agents, week): <span className="text-emerald-300 font-medium">${net}</span></div>
      </Glass>

      <Glass className="p-4">
        <div className="text-zinc-200 font-semibold mb-3">Agents</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {agentCards.map((a) => (
            <div key={a.name} className="p-3 bg-white/5 rounded-xl border border-white/10">
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
            </div>
          ))}
        </div>
      </Glass>

      <Glass className="p-4">
        <div className="text-zinc-200 font-semibold mb-3">Action Log</div>
        <div className="space-y-2 max-h-48 overflow-auto pr-1">
          {actionFeed.map((e, i) => (
            <div key={i} className="p-3 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 transition-all">
              <div className="text-[11px] text-zinc-500">{e.t}</div>
              <div className="text-zinc-100 text-sm">{e.text}</div>
            </div>
          ))}
        </div>
      </Glass>

      <Glass className="p-4">
        <div className="text-zinc-200 font-semibold mb-3">Costs</div>
        <div className="grid grid-cols-3 gap-3 text-sm">
          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300">Verifier Costs <div className="text-fuchsia-300 text-lg">$4.18</div></div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300">API Usage <div className="text-fuchsia-300 text-lg">$39.60</div></div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10 text-zinc-300">GPU Hours <div className="text-fuchsia-300 text-lg">$12.00</div></div>
        </div>
      </Glass>
    </div>
  );
};

const PheromindVisualization: React.FC = () => {
  // Simple organic layout: place nodes around a circle; weight controls size/opacity
  const nodes = pheromindNodes;
  const edges = pheromindEdges;
  const R = 110;
  const coords = useMemo(() => nodes.map((n, i) => {
    const a = (i / nodes.length) * Math.PI * 2;
    return { id: n.id, x: 150 + Math.cos(a) * R, y: 120 + Math.sin(a) * R };
  }), [nodes.length]);
  const get = (id: string) => coords.find((c) => c.id === id)!;

  return (
    <Glass className="p-4">
      <div className="text-zinc-200 font-semibold mb-2">Pheromind — Subconscious Insights</div>
      <svg viewBox="0 0 300 240" className="w-full h-64 bg-white/5 rounded-xl border border-white/10">
        <defs>
          <filter id="glow"><feGaussianBlur stdDeviation="2.5" result="coloredBlur" /><feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>
        {/* edges */}
        {edges.map((e, i) => {
          const a = get(e.a), b = get(e.b);
          return (
            <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#a78bfa" strokeOpacity={0.2 + e.weight * 0.6} strokeWidth={1 + e.weight * 2} />
          );
        })}
        {/* nodes */}
        {nodes.map((n, i) => {
          const c = get(n.id);
          const r = 8 + n.strength * 8;
          return (
            <g key={i}>
              <circle cx={c.x} cy={c.y} r={r} fill="#7c3aed" filter="url(#glow)" opacity={0.7} />
              <text x={c.x} y={c.y - (r + 6)} textAnchor="middle" fontSize={11} fill="#d4d4d8">{n.id}</text>
            </g>
          );
        })}
      </svg>
      <div className="mt-2 text-zinc-300 text-sm">
        Strong trail: <span className="text-fuchsia-300 font-medium">AI regulation</span> ↔ <span className="text-fuchsia-300 font-medium">European markets</span> <span className="text-zinc-400">(confidence 87%)</span>
      </div>
    </Glass>
  );
};

const TopNav: React.FC<{ mode: Mode; setMode: (m: Mode) => void }> = ({ mode, setMode }) => (
  <div className="w-full flex items-center justify-between px-4 py-3">
    <div className="flex items-center gap-3">
      <div className="h-8 w-8 rounded-lg bg-fuchsia-600/40 border border-fuchsia-400/30" />
      <div className="text-white font-semibold tracking-wide">Hybrid AI Council</div>
      <div className="ml-4 text-xs text-zinc-400">Current convo: <span className="text-zinc-200">Crypto Rebalancing</span></div>
    </div>
    <div className="flex items-center gap-6">
      <SystemHealth />
      <OperationalModeControl mode={mode} setMode={setMode} />
    </div>
  </div>
);

const AppShell: React.FC = () => {
  const [mode, setMode] = useState<Mode>("SUPERVISED");
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen" style={{ background: BG, color: TEXT }}>
      <div className="border-b border-white/10 sticky top-0 z-30 bg-black/20 backdrop-blur-md">
        <TopNav mode={mode} setMode={setMode} />
      </div>

      <div className="grid grid-cols-12 gap-4 p-4">
        <div className="col-span-12 md:col-span-3 lg:col-span-2">
          <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
        </div>
        <div className="col-span-12 md:col-span-6 lg:col-span-7">
          <ChatInterface mode={mode} />
        </div>
        <div className="col-span-12 md:col-span-3 lg:col-span-3">
          <div className="space-y-4">
            <KIPDashboard />
            <PheromindVisualization />
          </div>
        </div>
      </div>
    </div>
  );
};

export default function Preview() {
  return <AppShell />;
}
