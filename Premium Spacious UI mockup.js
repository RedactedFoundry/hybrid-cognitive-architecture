import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Mic,
  MicOff,
  Send,
  StopCircle,
  Paperclip,
  ChevronLeft,
  ChevronRight,
  Search,
  Star,
  StarOff,
  Settings2,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  MessageSquareText,
  FolderKanban,
  Plus,
  Bot,
  Check,
  X,
  Copy,
  RotateCcw,
} from "lucide-react";

// ==========================================================
// Hybrid AI Council — Premium Spacious UI Mock (React parity)
// Visual philosophy: Linear nav + Notion cards + Miro canvas
// DO NOT ship as Svelte yet — this is an interactive preview only.
// Colors: bg #15141c, accent #232046, text #fff, secondary #a1a1aa
// Spacing: p-8/p-12, m-6/m-8/m-12; generous whitespace
// ==========================================================

// ---------- Helpers & Types (kept simple for preview) ----------
const BG = "#15141c";
const ACCENT = "#232046";
const TXT_MUTED = "#a1a1aa";

const uid = () => Math.random().toString(36).slice(2);
const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

/** @typedef {"MANUAL"|"SUPERVISED"|"AUTONOMOUS"} Mode */

// ---------- Root Preview ----------
export default function HACPreview() {
  const [collapsed, setCollapsed] = useState(false); // left sidebar
  /** @type {[Mode, Function]} */
  const [mode, setMode] = useState("SUPERVISED");
  const [wsHealthy, setWsHealthy] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [showPheromind, setShowPheromind] = useState(false); // fullscreen canvas

  // Conversations / Projects
  const [pinned, setPinned] = useState([
    { id: uid(), title: "Quarterly Strategy", unread: 0 },
    { id: uid(), title: "Crypto Rebalance", unread: 2 },
  ]);
  const [recents, setRecents] = useState([
    { id: uid(), title: "Agent Budget Tuning", unread: 0 },
    { id: uid(), title: "Marketing Experiment", unread: 1 },
    { id: uid(), title: "Model Upgrade Review", unread: 0 },
  ]);
  const [activeId, setActiveId] = useState(pinned[0].id);

  // Chat
  const [messages, setMessages] = useState([
    { id: uid(), role: "user", ts: now(), text: "Help me analyze the crypto market for portfolio rebalancing." },
    { id: uid(), role: "assistant", ts: now(), verified: true, text: "Loaded macro + onchain context. Want a quick risk map? (/analyze)" },
  ]);
  const [composer, setComposer] = useState("");
  const [recording, setRecording] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [streamIdx, setStreamIdx] = useState(0);
  const streamText = "Local LLM: drafting… | Cloud Verifier: checks pass | Budget: ok | Responding with rebalancing suggestion and risk notes.";
  const listRef = useRef(null);

  useEffect(() => {
    if (!streaming) return;
    const t = setInterval(() => setStreamIdx((i) => Math.min(i + 2, streamText.length)), 18);
    return () => clearInterval(t);
  }, [streaming]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: 999999, behavior: "smooth" });
  }, [messages.length, streaming, streamIdx]);

  const send = () => {
    if (!composer.trim() && !recording) return;
    const u = { id: uid(), role: "user", ts: now(), text: composer.trim() || "[Voice message]" };
    setMessages((xs) => [...xs, u]);
    setComposer(""); setRecording(false);
    const aId = uid(); const a = { id: aId, role: "assistant", ts: now(), text: "", verified: false };
    setMessages((xs) => [...xs, a]);
    setStreamIdx(0); setStreaming(true);
    setTimeout(() => {
      setStreaming(false);
      setMessages((xs) => xs.map((m) => (m.id === aId ? { ...m, text: streamText } : m)));
      setMessages((xs) => [...xs, { id: uid(), role: "assistant", ts: now(), text: "Verifier: constitutional checks passed; rationale recorded.", verified: true }]);
    }, 900);
  };

  const stop = () => setStreaming(false);

  // Treasury sample
  const [treasury, setTreasury] = useState({
    balance: 2847,
    allocated: 1203,
    pnlWeek: 546,
    tx: [
      { id: uid(), when: "2m", label: "Constitutional verification", amount: -4.18 },
      { id: uid(), when: "8m", label: "API usage", amount: -39.6 },
      { id: uid(), when: "1h", label: "GPU hours", amount: -12.0 },
      { id: uid(), when: "1h", label: "Client payment", amount: +210.0 },
    ],
  });

  // Agents sample
  const agents = [
    { name: "Sarah", role: "ContentCreation_Agent", revenue: 347, spend: 89, net: 258, state: "running" },
    { name: "StockAnalyst_Agent", role: "Equities", revenue: 160, spend: 48, net: 112, state: "idle" },
    { name: "MarketResearch_Agent", role: "Insights", revenue: 240, spend: 64, net: 176, state: "cooldown" },
  ];

  // Pheromind demo edges (decay + reinforce)
  const [edges, setEdges] = useState([
    { a: "Bitcoin", b: "Inflation", s: 0.82 },
    { a: "Inflation", b: "Gold", s: 0.80 },
    { a: "Gold", b: "Safe Haven Assets", s: 0.87 },
    { a: "AI regulation", b: "European markets", s: 0.87 },
    { a: "Remote work", b: "Commercial real estate decline", s: 0.73 },
  ]);
  useEffect(() => {
    const t = setInterval(() => {
      setEdges((es) => es.map((e) => ({ ...e, s: Math.max(0.2, e.s - 0.01) })));
    }, 12000 / 12); // simulate ~12s TTL decay
    return () => clearInterval(t);
  }, []);

  const reinforce = (idx) => setEdges((es) => es.map((e, i) => (i === idx ? { ...e, s: Math.min(0.95, e.s + 0.08) } : e)));

  // Mode color accents
  const modeColor = mode === "MANUAL" ? "rose" : mode === "SUPERVISED" ? "amber" : "emerald";

  return (
    <div className="min-h-screen" style={{ background: BG, color: "#fff" }}>
      {/* Top nav (80px) */}
      <header className="h-20 flex items-center justify-between px-12 border-b" style={{ borderColor: "rgba(255,255,255,0.12)" }}>
        <div className="flex items-center gap-6">
          <div className="h-12 w-12 rounded-2xl grid place-items-center" style={{ background: ACCENT }}>
            <Bot className="h-6 w-6" />
          </div>
          <div className="text-xl font-semibold tracking-tight">Hybrid AI Council</div>
        </div>
        <div className="flex items-center gap-6">
          <ModeToggle mode={mode} setMode={setMode} />
          <div className={`px-4 py-2 rounded-xl border backdrop-blur-xl`} style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>
            <span className="text-sm" style={{ color: TXT_MUTED }}>WS</span> <span className="ml-2">{wsHealthy ? "Connected" : "Reconnecting…"}</span>
          </div>
          <button className="px-4 py-2 rounded-xl border text-sm" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }} onClick={() => setShowSettings(true)}>
            <Settings2 className="inline h-4 w-4 mr-2" /> Settings
          </button>
        </div>
      </header>

      {/* Main layout */}
      <div className="grid grid-cols-12 gap-8 mx-8 my-8">
        {/* Left sidebar (320px wide) */}
        <aside className="col-span-3" style={{ width: collapsed ? 80 : 320, transition: "width .2s" }}>
          <div className="flex items-center justify-between mb-6">
            <div className="text-lg font-medium" style={{ color: TXT_MUTED }}>Projects & Conversations</div>
            <button onClick={() => setCollapsed((c) => !c)} className="p-3 rounded-xl border" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>
              {collapsed ? <ChevronRight /> : <ChevronLeft />}
            </button>
          </div>
          {/* Search */}
          {!collapsed && (
            <div className="mb-6">
              <div className="flex items-center gap-3 px-4 py-3 rounded-2xl border backdrop-blur-xl" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>
                <Search className="h-5 w-5" />
                <input placeholder="Search…" className="bg-transparent outline-none text-lg flex-1" />
              </div>
            </div>
          )}

          {/* Pinned */}
          <SectionTitle collapsed={collapsed} title="Pinned" />
          <div className="flex flex-col gap-4 mb-8">
            {pinned.map((c) => (
              <ConvRow key={c.id} active={activeId === c.id} collapsed={collapsed} title={c.title} unread={c.unread} onClick={() => setActiveId(c.id)} onPin={() => {}} />
            ))}
          </div>

          {/* Recent */}
          <SectionTitle collapsed={collapsed} title="Recent" />
          <div className="flex flex-col gap-4">
            {recents.map((c) => (
              <ConvRow key={c.id} active={activeId === c.id} collapsed={collapsed} title={c.title} unread={c.unread} onClick={() => setActiveId(c.id)} />
            ))}
          </div>
        </aside>

        {/* Center: Conversation Interface */}
        <main className="col-span-6">
          <div className="rounded-3xl p-8 border backdrop-blur-xl" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>
            {/* Thread header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-2xl font-semibold">{getTitleById(activeId, pinned, recents)}</div>
                <div className="text-sm" style={{ color: TXT_MUTED }}>Threaded replies • Context preserved • Mode-aware approvals</div>
              </div>
              <div className="flex items-center gap-3">
                <SlashQuickActions onPick={(cmd) => setComposer((t) => t + ` ${cmd} `)} />
                {streaming ? (
                  <button onClick={stop} className="px-4 py-3 rounded-xl text-base inline-flex items-center gap-2" style={{ background: "rgba(255,255,255,0.15)", border: "1px solid rgba(255,255,255,0.2)" }}>
                    <StopCircle className="h-5 w-5" /> Stop
                  </button>
                ) : null}
              </div>
            </div>

            {/* Messages */}
            <div ref={listRef} className="space-y-6 pr-1" style={{ maxHeight: 540, overflow: "auto" }}>
              {messages.map((m) => (
                <MessageBubble key={m.id} m={m} mode={mode} />
              ))}
              {streaming && (
                <div className="flex items-start gap-4">
                  <div className="h-10 w-10 rounded-2xl grid place-items-center" style={{ background: ACCENT }}>
                    <Sparkles className="h-5 w-5" />
                  </div>
                  <div className="flex-1 text-lg leading-relaxed rounded-2xl p-6 border" style={{ background: "rgba(255,255,255,0.10)", borderColor: "rgba(255,255,255,0.2)" }}>
                    {streamText.slice(0, streamIdx)}
                  </div>
                </div>
              )}
            </div>

            {/* Composer */}
            <div className="mt-8 rounded-2xl p-6 border" style={{ background: "rgba(255,255,255,0.10)", borderColor: "rgba(255,255,255,0.2)" }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3 text-base" style={{ color: TXT_MUTED }}>
                  Multimodal input supported
                </div>
                <div className="flex items-center gap-3">
                  <button title="Attach" className="p-3 rounded-xl border" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>
                    <Paperclip className="h-5 w-5" />
                  </button>
                  <button onClick={() => setRecording((r) => !r)} className="p-3 rounded-xl border" style={{ background: recording ? "rgba(244,63,94,0.6)" : "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>
                    {recording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
                  </button>
                </div>
              </div>
              {recording && <VoiceBars />}
              <textarea value={composer} onChange={(e) => setComposer(e.target.value)} rows={3} className="w-full bg-transparent outline-none text-lg placeholder-white/40" placeholder="Type a message or use /analyze, /budget, /pheromind…" />
              <div className="mt-4 flex items-center justify-between">
                <div className="text-sm" style={{ color: TXT_MUTED }}>Press ⌘⏎ to send</div>
                <button onClick={() => { setStreaming(true); setTimeout(send, 10); }} className="px-6 py-3 rounded-2xl text-lg font-medium border inline-flex items-center gap-2" style={{ background: ACCENT, borderColor: "rgba(255,255,255,0.2)" }}>
                  <Send className="h-5 w-5" /> Send
                </button>
              </div>
            </div>
          </div>
        </main>

        {/* Right panel — glass cards, generous gaps */}
        <aside className="col-span-3">
          <div className="flex flex-col gap-6">
            {/* Treasury */}
            <div className="rounded-3xl p-8 border backdrop-blur-xl" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>
              <div className="flex items-center justify-between mb-6">
                <div className="text-xl font-semibold">Treasury</div>
                <div className="text-sm" style={{ color: TXT_MUTED }}>Realtime KPIs</div>
              </div>
              <div className="grid grid-cols-3 gap-6 mb-8">
                <KPI label="Available" value={`$${treasury.balance.toLocaleString()}`} />
                <KPI label="Allocated" value={`$${treasury.allocated.toLocaleString()}`} />
                <KPI label="Net P&L (wk)" value={`+$${treasury.pnlWeek}`} trend="up" />
              </div>
              <div className="text-base font-medium mb-3" style={{ color: TXT_MUTED }}>Recent transactions</div>
              <ul className="space-y-3">
                {treasury.tx.map((t) => (
                  <li key={t.id} className="flex items-center justify-between px-4 py-3 rounded-xl border" style={{ background: "rgba(255,255,255,0.10)", borderColor: "rgba(255,255,255,0.2)" }}>
                    <span>{t.when} • {t.label}</span>
                    <span className={t.amount >= 0 ? "text-emerald-300" : "text-rose-300"}>{t.amount >= 0 ? "+$" + t.amount : "-$" + Math.abs(t.amount)}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Agents */}
            <div className="rounded-3xl p-8 border backdrop-blur-xl" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>
              <div className="flex items-center justify-between mb-6">
                <div className="text-xl font-semibold">KIP Agents</div>
                <button onClick={() => setShowPheromind(true)} className="px-4 py-2 rounded-xl text-sm border" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>Open Pheromind</button>
              </div>
              <div className="space-y-4">
                {agents.map((a) => (
                  <AgentCard key={a.name} a={a} />
                ))}
              </div>
            </div>
          </div>
        </aside>
      </div>

      {/* Settings drawer for Supervised rules */}
      {showSettings && (
        <div className="fixed inset-0 z-50" style={{ background: "rgba(0,0,0,0.5)" }} onClick={() => setShowSettings(false)}>
          <div className="absolute right-0 top-0 h-full w-[520px] p-12 overflow-auto border-l" style={{ background: BG, borderColor: "rgba(255,255,255,0.2)" }} onClick={(e) => e.stopPropagation()}>
            <div className="text-2xl font-semibold mb-8">Mode Settings</div>
            <div className="space-y-8">
              <section>
                <div className="text-lg font-medium mb-3">Supervised rules</div>
                <div className="space-y-4">
                  <ToggleRow label="Auto-approve actions under $50" defaultChecked />
                  <ToggleRow label="Flag content-risk replies for review" defaultChecked />
                  <ToggleRow label="Require approval for external API charges" />
                </div>
              </section>
              <section>
                <div className="text-lg font-medium mb-3">Manual mode</div>
                <div className="space-y-4">
                  <ToggleRow label="Require approve/reject per action" defaultChecked />
                  <ToggleRow label="Allow batch approvals" />
                </div>
              </section>
              <section>
                <div className="text-lg font-medium mb-3">Autonomous guardrails</div>
                <div className="space-y-4">
                  <ToggleRow label="Budget ceiling per 24h: $250" defaultChecked />
                  <ToggleRow label="Block unreviewed vendor tools" />
                </div>
              </section>
            </div>
          </div>
        </div>
      )}

      {/* Fullscreen Pheromind canvas */}
      {showPheromind && (
        <div className="fixed inset-0 z-50" style={{ background: "rgba(0,0,0,0.7)" }} onClick={() => setShowPheromind(false)}>
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[1200px] h-[700px] rounded-3xl p-12 border backdrop-blur-xl" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }} onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-8">
              <div className="text-2xl font-semibold">Pheromind — Concept Trails</div>
              <button className="px-4 py-2 rounded-xl border" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }} onClick={() => setShowPheromind(false)}>Close</button>
            </div>
            <PheromindCanvas edges={edges} onReinforce={reinforce} />
          </div>
        </div>
      )}
    </div>
  );
}

// ---------- Components ----------
function ModeToggle({ mode, setMode }) {
  return (
    <div className="flex items-center gap-3">
      {(["MANUAL", "SUPERVISED", "AUTONOMOUS"]).map((m) => (
        <button key={m} onClick={() => setMode(m)} className={`px-5 py-3 rounded-2xl text-base font-medium border ${mode === m ? "" : "opacity-70"}`} style={{
          background: mode === m ? "rgba(34,197,94,0.18)" : "rgba(255,255,255,0.15)",
          borderColor: "rgba(255,255,255,0.2)",
        }}>
          {m}
        </button>
      ))}
    </div>
  );
}

function SectionTitle({ title, collapsed }) {
  return (
    <div className="mt-6 mb-4" style={{ paddingLeft: collapsed ? 0 : 8 }}>
      {!collapsed && <div className="text-sm" style={{ color: TXT_MUTED }}>{title}</div>}
    </div>
  );
}

function ConvRow({ title, unread, active, onClick, collapsed }) {
  return (
    <button onClick={onClick} className={`w-full rounded-2xl text-left ${active ? "" : "opacity-90"}`}
      style={{ padding: 18, background: active ? ACCENT : "rgba(255,255,255,0.10)", border: "1px solid rgba(255,255,255,0.2)" }}>
      <div className="flex items-center gap-4">
        <div className="h-10 w-10 rounded-2xl grid place-items-center" style={{ background: "rgba(255,255,255,0.12)" }}>
          <MessageSquareText className="h-5 w-5" />
        </div>
        {!collapsed && (
          <div className="flex-1">
            <div className="text-lg font-medium leading-tight">{title}</div>
            <div className="text-sm" style={{ color: TXT_MUTED }}>Last active {Math.ceil(Math.random() * 4)}h ago</div>
          </div>
        )}
        {unread ? <span className="ml-auto text-sm px-3 py-1 rounded-xl" style={{ background: "rgba(255,255,255,0.15)" }}>{unread}</span> : null}
      </div>
    </button>
  );
}

function MessageBubble({ m, mode }) {
  const isUser = m.role === "user";
  return (
    <div className={`flex gap-4 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className="h-10 w-10 rounded-2xl grid place-items-center" style={{ background: isUser ? "rgba(255,255,255,0.12)" : ACCENT }}>
        {isUser ? <span className="text-sm">U</span> : <Sparkles className="h-5 w-5" />}
      </div>
      <div className="flex-1">
        <div className="text-lg leading-relaxed rounded-2xl p-6 border" style={{ background: "rgba(255,255,255,0.10)", borderColor: "rgba(255,255,255,0.2)" }}>
          {m.text}
        </div>
        <div className="mt-3 flex items-center gap-3" style={{ color: TXT_MUTED }}>
          <span className="text-sm">{m.ts}</span>
          {!isUser && (
            <>
              {m.verified ? (
                <span className="inline-flex items-center gap-2 text-sm px-3 py-1 rounded-xl" style={{ background: "rgba(16,185,129,0.2)" }}>
                  <ShieldCheck className="h-4 w-4" /> Verified
                </span>
              ) : (
                <span className="inline-flex items-center gap-2 text-sm px-3 py-1 rounded-xl" style={{ background: "rgba(251,191,36,0.15)" }}>
                  <ShieldAlert className="h-4 w-4" /> Verifying…
                </span>
              )}
              {/* Message controls */}
              {mode === "MANUAL" && (
                <>
                  <button className="px-3 py-1 rounded-xl border" style={{ background: "rgba(34,197,94,0.18)", borderColor: "rgba(255,255,255,0.2)" }}><Check className="h-4 w-4" /> Approve</button>
                  <button className="px-3 py-1 rounded-xl border" style={{ background: "rgba(244,63,94,0.18)", borderColor: "rgba(255,255,255,0.2)" }}><X className="h-4 w-4" /> Reject</button>
                </>
              )}
              <button className="px-3 py-1 rounded-xl border" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}><Copy className="h-4 w-4" /> Copy</button>
              <button className="px-3 py-1 rounded-xl border" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}><RotateCcw className="h-4 w-4" /> Regenerate</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function SlashQuickActions({ onPick }) {
  const chips = ["/analyze", "/budget", "/pheromind"];
  return (
    <div className="flex items-center gap-3">
      {chips.map((c) => (
        <button key={c} onClick={() => onPick(c)} className="px-4 py-2 rounded-xl border text-base" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>{c}</button>
      ))}
    </div>
  );
}

function KPI({ label, value, trend }) {
  return (
    <div className="rounded-2xl p-6 border" style={{ background: "rgba(255,255,255,0.10)", borderColor: "rgba(255,255,255,0.2)" }}>
      <div className="text-sm mb-2" style={{ color: TXT_MUTED }}>{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
      {trend === "up" && <div className="mt-2 text-emerald-300 text-sm">▲ improving</div>}
    </div>
  );
}

function AgentCard({ a }) {
  return (
    <div className="rounded-2xl p-6 border" style={{ background: "rgba(255,255,255,0.10)", borderColor: "rgba(255,255,255,0.2)" }}>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-medium">{a.name}</div>
          <div className="text-sm" style={{ color: TXT_MUTED }}>{a.role}</div>
        </div>
        <div className="text-right">
          <div className="text-sm" style={{ color: TXT_MUTED }}>Net</div>
          <div className={`text-xl font-semibold ${a.net >= 0 ? "text-emerald-300" : "text-rose-300"}`}>{a.net >= 0 ? "+$" + a.net : "-$" + Math.abs(a.net)}</div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-4 mt-4 text-sm">
        <div>Revenue <span className="text-emerald-300 font-medium">${a.revenue}</span></div>
        <div>Spend <span className="text-rose-300 font-medium">${a.spend}</span></div>
        <button className="px-3 py-2 rounded-xl border text-sm" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>Details</button>
      </div>
    </div>
  );
}

function ToggleRow({ label, defaultChecked }) {
  const [on, setOn] = useState(!!defaultChecked);
  return (
    <label className="flex items-center justify-between px-5 py-4 rounded-2xl border" style={{ background: "rgba(255,255,255,0.10)", borderColor: "rgba(255,255,255,0.2)" }}>
      <span className="text-base">{label}</span>
      <button
        onClick={() => setOn((v) => !v)}
        className={`w-14 h-8 rounded-full relative transition ${on ? "bg-emerald-500/70" : "bg-white/20"}`}
      >
        <span className={`absolute top-1 left-1 h-6 w-6 rounded-full bg-white transition ${on ? "translate-x-6" : ""}`} />
      </button>
    </label>
  );
}

function VoiceBars() {
  return (
    <div className="mt-4 rounded-2xl p-4 border" style={{ background: "rgba(255,255,255,0.10)", borderColor: "rgba(255,255,255,0.2)" }}>
      <div className="text-sm mb-2" style={{ color: TXT_MUTED }}>Listening (simulated)…</div>
      <div className="h-10 flex items-end gap-1">
        {Array.from({ length: 56 }).map((_, i) => (
          <span key={i} className="w-1 inline-block animate-[pulse_1s_ease-in-out_infinite]" style={{ height: `${8 + ((i * 37) % 28)}px`, background: ACCENT, animationDelay: `${(i % 10) * 0.06}s` }} />
        ))}
      </div>
    </div>
  );
}

// Miro-like pheromind canvas
function PheromindCanvas({ edges, onReinforce }) {
  const pos = (s) => s.split("").reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 0);
  const coords = (label, i) => ({ x: 120 + (pos(label) % 800), y: 80 + ((pos(label) >> 5) % 420) });
  return (
    <div className="w-full h-full relative rounded-2xl overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
      <svg viewBox="0 0 1200 600" className="absolute inset-0 w-full h-full">
        {edges.map((e, i) => {
          const A = coords(e.a, i), B = coords(e.b, i);
          return (
            <g key={i}>
              <defs>
                <linearGradient id={`g${i}`} x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor="#6d5bd0" />
                  <stop offset="100%" stopColor="#c084fc" />
                </linearGradient>
              </defs>
              <line x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={`url(#g${i})`} strokeWidth={Math.max(1.5, e.s * 8)} strokeOpacity={0.9} />
              <circle cx={A.x} cy={A.y} r={12} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
              <circle cx={B.x} cy={B.y} r={12} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
              <text x={A.x} y={A.y - 16} textAnchor="middle" fill="#fff" fontSize="12">{e.a}</text>
              <text x={B.x} y={B.y - 16} textAnchor="middle" fill="#fff" fontSize="12">{e.b}</text>
            </g>
          );
        })}
      </svg>
      {/* Reinforce buttons */}
      <div className="absolute bottom-6 left-6 flex gap-3">
        {edges.map((_, i) => (
          <button key={i} onClick={() => onReinforce(i)} className="px-4 py-2 rounded-xl text-sm border" style={{ background: "rgba(255,255,255,0.15)", borderColor: "rgba(255,255,255,0.2)" }}>Reinforce #{i + 1}</button>
        ))}
      </div>
    </div>
  );
}

function getTitleById(id, pinned, recents) {
  const all = [...pinned, ...recents];
  return all.find((x) => x.id === id)?.title || "Conversation";
}
