import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Mic,
  Send,
  StopCircle,
  Paperclip,
  ChevronLeft,
  ChevronRight,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  MessageSquareText,
  Plus,
  Check,
  X,
  Copy,
  RotateCcw,
  Maximize2,
  ChevronDown,
} from "lucide-react";

// ==========================================================
// Hybrid AI Council — V3 Interactive UI
// Changes requested:
// 1) ChatGPT-style contextual Stop: Send button toggles to Stop while streaming
// 2) Page navigation moved to TOP (dropdown top-left)
// 3) Left column = Conversations + Projects (collections) from HAC mock
// 4) Operational mode toggle only in Settings/System (not in top bar)
// This is a React preview mock; will port 1:1 to SvelteKit + TS + Tailwind
// ==========================================================

// ---------- Helpers & Theme ----------
const BG = "#15141c"; // background
const ACCENT = "#232046"; // deep blue/purple accent
const PURPLE = "#6d5bd0"; // purple accent
const TXT_MUTED = "#a1a1aa"; // secondary text
const GLASS = { bg: "rgba(255,255,255,0.15)", border: "rgba(255,255,255,0.2)", subtle: "rgba(255,255,255,0.10)" };

const uid = () => Math.random().toString(36).slice(2);
const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

/** @typedef {"council"|"kip"|"pheromind"|"calendar"|"projects"|"system"} Page */
/** @typedef {"MANUAL"|"SUPERVISED"|"AUTONOMOUS"} Mode */

export default function HACTopNavV3() {
  // --- Global UI state ---
  const [page, setPage] = useState(/** @type {Page} */("council"));
  const [navOpen, setNavOpen] = useState(false); // page dropdown open
  const [collapsed, setCollapsed] = useState(false); // left sidebar collapse
  const [wsHealthy, setWsHealthy] = useState(true);
  const [showSettings, setShowSettings] = useState(false);
  const [mode, setMode] = useState(/** @type {Mode} */("SUPERVISED"));

  // --- Fullscreen panels ---
  const [showTreasury, setShowTreasury] = useState(false);
  const [showAgents, setShowAgents] = useState(false);
  const [showPheromind, setShowPheromind] = useState(false);
  const [agentDetail, setAgentDetail] = useState(null);

  // --- Left: Conversations + Collections (projects) ---
  const [collections, setCollections] = useState([
    { id: uid(), name: "All" },
    { id: uid(), name: "Work" },
    { id: uid(), name: "Research" },
    { id: uid(), name: "Personal" },
  ]);
  const [activeCollection, setActiveCollection] = useState("All");
  const addCollection = () => {
    const n = `Project ${collections.length}`;
    setCollections((xs) => [...xs, { id: uid(), name: n }]);
    setActiveCollection(n);
  };

  const [pinned, setPinned] = useState([
    { id: uid(), title: "Quarterly Strategy", unread: 0, collection: "Work" },
    { id: uid(), title: "Crypto Rebalance", unread: 2, collection: "Research" },
  ]);
  const [recents, setRecents] = useState([
    { id: uid(), title: "Agent Budget Tuning", unread: 0, collection: "Work" },
    { id: uid(), title: "Marketing Experiment", unread: 1, collection: "Work" },
    { id: uid(), title: "Model Upgrade Review", unread: 0, collection: "Personal" },
  ]);
  const [activeId, setActiveId] = useState(pinned[0].id);
  const activeConv = useMemo(() => [...pinned, ...recents].find((x) => x.id === activeId), [pinned, recents, activeId]);
  const updateConvCollection = (id, col) => {
    setPinned((ps) => ps.map((p) => (p.id === id ? { ...p, collection: col } : p)));
    setRecents((rs) => rs.map((r) => (r.id === id ? { ...r, collection: col } : r)));
  };
  const filterByCollection = (xs) => (activeCollection === "All" ? xs : xs.filter((c) => c.collection === activeCollection));

  // --- Council (chat) state ---
  const [messages, setMessages] = useState([
    { id: uid(), role: "user", ts: now(), text: "Help me analyze the crypto market for portfolio rebalancing." },
    { id: uid(), role: "assistant", ts: now(), verified: true, status: "complete", text: "Loaded macro + onchain context. Want a quick risk map? (/analyze)" },
  ]);
  const [composer, setComposer] = useState("");
  const taRef = useRef(null);
  const MAX_LINES = 6;
  const autosize = () => {
    if (!taRef.current) return;
    const el = taRef.current;
    el.style.height = "auto";
    const lh = parseFloat(getComputedStyle(el).lineHeight || "28");
    const maxH = lh * MAX_LINES;
    el.style.height = Math.min(el.scrollHeight, maxH) + "px";
  };
  useEffect(() => { autosize(); }, [composer]);

  const [streaming, setStreaming] = useState(false);
  const [streamIdx, setStreamIdx] = useState(0);
  const listRef = useRef(null);
  const streamRef = useRef({ iid: /** @type {any} */(null), aId: /** @type {string|null} */(null), tos: /** @type {any[]} */([]) });
  const streamText = "Local LLM drafting… risk map + suggested rebalances. ";

  useEffect(() => { listRef.current?.scrollTo({ top: 999999, behavior: "smooth" }); }, [messages.length, streaming, streamIdx]);

  const send = () => {
    if (!composer.trim()) return;
    const u = { id: uid(), role: "user", ts: now(), text: composer.trim() };
    setMessages((xs) => [...xs, u]);
    setComposer("");
    autosize();

    const aId = uid();
    const a = { id: aId, role: "assistant", ts: now(), text: "", verified: false, status: "generating" };
    setMessages((xs) => [...xs, a]);

    setStreaming(true);
    streamRef.current.aId = aId;
    streamRef.current.iid = setInterval(() => {
      setStreamIdx((i) => {
        const next = Math.min(i + 2, streamText.length);
        setMessages((xs) => xs.map((m) => (m.id === aId ? { ...m, text: streamText.slice(0, next) } : m)));
        return next;
      });
    }, 18);

    const t1 = setTimeout(() => {
      clearInterval(streamRef.current.iid);
      setMessages((xs) => xs.map((m) => (m.id === aId ? { ...m, text: streamText + "\nPreparing final answer…", status: "verifying" } : m)));
    }, 900);

    const t2 = setTimeout(() => {
      setMessages((xs) => xs.map((m) => (m.id === aId ? { ...m, text: streamText + "\nFinal: Based on volatility and liquidity, consider trimming BTC by 5% and allocating to ETH and cash equivalents.", status: "complete", verified: true } : m)));
      setStreaming(false);
      setStreamIdx(0);
      streamRef.current.iid = null;
    }, 1500);

    streamRef.current.tos.push(t1, t2);
  };

  const stop = () => {
    if (streamRef.current.iid) clearInterval(streamRef.current.iid);
    streamRef.current.tos.forEach(clearTimeout);
    setStreaming(false); setStreamIdx(0);
    const aId = streamRef.current.aId;
    if (aId) setMessages((xs) => xs.map((m) => (m.id === aId ? { ...m, status: "complete" } : m)));
    streamRef.current.iid = null; streamRef.current.tos = []; streamRef.current.aId = null;
  };

  // --- Right-side data (Treasury, Agents, Pheromind) ---
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

  const agents = [
    { id: uid(), name: "Sarah", role: "ContentCreation_Agent", revenue: 347, spend: 89, net: 258, state: "running" },
    { id: uid(), name: "StockAnalyst_Agent", role: "Equities", revenue: 160, spend: 48, net: 112, state: "idle" },
    { id: uid(), name: "MarketResearch_Agent", role: "Insights", revenue: 240, spend: 64, net: 176, state: "cooldown" },
  ];

  const [edges, setEdges] = useState([
    { a: "Bitcoin", b: "Inflation", s: 0.82 },
    { a: "Inflation", b: "Gold", s: 0.80 },
    { a: "Gold", b: "Safe Haven Assets", s: 0.87 },
    { a: "AI regulation", b: "European markets", s: 0.87 },
    { a: "Remote work", b: "Commercial real estate decline", s: 0.73 },
  ]);
  useEffect(() => {
    const t = setInterval(() => setEdges((es) => es.map((e) => ({ ...e, s: Math.max(0.2, e.s - 0.01) }))), 12000 / 12);
    return () => clearInterval(t);
  }, []);
  const reinforce = (i) => setEdges((es) => es.map((e, idx) => (idx === i ? { ...e, s: Math.min(0.95, e.s + 0.08) } : e)));

  // ----- Render -----
  return (
    <div className="min-h-screen" style={{ background: BG, color: "#fff" }}>
      {/* Top bar with page dropdown */}
      <header className="h-20 flex items-center justify-between px-12 border-b relative" style={{ borderColor: "rgba(255,255,255,0.12)" }}>
        <div className="flex items-center gap-6">
          <div className="h-12 w-12 rounded-2xl grid place-items-center" style={{ background: ACCENT, boxShadow: `0 0 0 1px ${PURPLE}40, 0 8px 30px ${PURPLE}33` }}>
            <div className="h-7 w-7 rounded-xl" style={{ background: `linear-gradient(135deg, ${PURPLE}, ${ACCENT})` }} />
          </div>
          {/* Page switcher (dropdown) */}
          <div className="relative">
            <button onClick={() => setNavOpen((o) => !o)} className="px-4 py-2 rounded-xl border inline-flex items-center gap-2" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <span className="text-base font-medium capitalize">{page}</span>
              <ChevronDown className="h-4 w-4" />
            </button>
            {navOpen && (
              <div className="absolute z-50 mt-2 w-56 rounded-2xl border p-2" style={{ background: BG, borderColor: GLASS.border }}>
                {(["council", "kip", "pheromind", "calendar", "projects", "system"])/** @type {Page[]} */(null) || []}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="px-4 py-2 rounded-xl border backdrop-blur-xl" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
            <span className="text-sm" style={{ color: TXT_MUTED }}>WS</span>
            <span className="ml-2">{wsHealthy ? "Connected" : "Reconnecting…"}</span>
          </div>
          <button className="px-4 py-2 rounded-xl border text-sm" style={{ background: GLASS.bg, borderColor: GLASS.border }} onClick={() => setShowSettings(true)}>
            <Settings2 className="inline h-4 w-4 mr-2" /> Settings
          </button>
        </div>
        {/* Dropdown menu content */}
        {navOpen && (
          <div className="absolute left-[140px] top-16 z-50 w-56 rounded-2xl border p-2" style={{ background: BG, borderColor: GLASS.border }}>
            {(["council", "kip", "pheromind", "calendar", "projects", "system"]).map((p) => (
              <button key={p} onClick={() => { setPage(p); setNavOpen(false); }} className={`w-full text-left px-4 py-3 rounded-xl capitalize ${page===p?"" : "opacity-80"}`} style={{ background: page===p? ACCENT : GLASS.subtle, border: `1px solid ${GLASS.border}` }}>
                {p}
              </button>
            ))}
          </div>
        )}
      </header>

      {/* Main layout */}
      <div className="grid grid-cols-12 gap-8 mx-8 my-8">
        {/* Left sidebar: Conversations + Collections */}
        <aside className="col-span-3" style={{ width: collapsed ? 80 : 320, transition: "width .2s" }}>
          <div className="flex items-center justify-between mb-6">
            <div className="text-lg font-medium" style={{ color: TXT_MUTED }}>Conversations</div>
            <button onClick={() => setCollapsed((c) => !c)} className="p-3 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              {collapsed ? <ChevronRight /> : <ChevronLeft />}
            </button>
          </div>
          {!collapsed && (
            <>
              <div className="mb-4">
                <div className="flex items-center gap-3 px-4 py-3 rounded-2xl border backdrop-blur-xl" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                  <Search className="h-5 w-5" />
                  <input placeholder="Search conversations…" className="bg-transparent outline-none text-lg flex-1" />
                </div>
              </div>
              <div className="mb-6 flex items-center flex-wrap gap-2">
                {collections.map((c) => (
                  <button key={c.id} onClick={() => setActiveCollection(c.name)} className={`px-3 py-1 rounded-xl border text-sm ${activeCollection === c.name ? "" : "opacity-80"}`} style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                    {c.name}
                  </button>
                ))}
                <button onClick={addCollection} className="px-3 py-1 rounded-xl border text-sm inline-flex items-center gap-1" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                  <Plus className="h-4 w-4" /> New
                </button>
              </div>
            </>
          )}

          <SectionTitle collapsed={collapsed} title="Pinned" />
          <div className="flex flex-col gap-4 mb-8">
            {filterByCollection(pinned).map((c) => (
              <ConvRow key={c.id} active={activeId === c.id} collapsed={collapsed} title={c.title} unread={c.unread} onClick={() => setActiveId(c.id)} />
            ))}
          </div>

          <SectionTitle collapsed={collapsed} title="Recent" />
          <div className="flex flex-col gap-4">
            {filterByCollection(recents).map((c) => (
              <ConvRow key={c.id} active={activeId === c.id} collapsed={collapsed} title={c.title} unread={c.unread} onClick={() => setActiveId(c.id)} />
            ))}
          </div>
        </aside>

        {/* Center: switches by page */}
        <main className="col-span-6">
          {page === "council" && (
            <CouncilChat
              listRef={listRef}
              messages={messages}
              mode={mode}
              composer={composer}
              setComposer={setComposer}
              taRef={taRef}
              MAX_LINES={MAX_LINES}
              autosize={autosize}
              streaming={streaming}
              send={send}
              stop={stop}
              collections={collections}
              activeConv={activeConv}
              activeId={activeId}
              updateConvCollection={(col)=>updateConvCollection(activeId,col)}
            />
          )}

          {page === "kip" && (
            <div className="rounded-3xl p-8 border backdrop-blur-xl space-y-8" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <div className="flex items-center justify-between">
                <div className="text-2xl font-semibold">KIP Engine — Operations</div>
                <button onClick={() => setShowAgents(true)} className="px-3 py-2 rounded-xl text-sm border inline-flex items-center gap-2" style={{ background: GLASS.bg, borderColor: GLASS.border }}><Maximize2 className="h-4 w-4" /> Expand</button>
              </div>
              <div className="grid grid-cols-3 gap-6">
                {agents.map((a) => <AgentCard key={a.id} a={a} onDetails={() => { setShowAgents(true); setAgentDetail(a); }} />)}
              </div>
              <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                <div className="text-lg font-medium mb-4" style={{ color: TXT_MUTED }}>Live Operations Feed</div>
                <ul className="space-y-3">
                  <li className="flex items-center justify-between px-4 py-3 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                    <span>1m • StockAnalyst_Agent purchased $AAPL analysis (Bloomberg API)</span>
                    <span className="text-rose-300">-$12</span>
                  </li>
                  <li className="flex items-center justify-between px-4 py-3 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                    <span>14m • MarketResearch_Agent completed client report</span>
                    <span className="text-emerald-300">+$150</span>
                  </li>
                </ul>
              </div>
            </div>
          )}

          {page === "pheromind" && (
            <div className="rounded-3xl p-8 border backdrop-blur-xl space-y-6" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <div className="flex items-center justify-between">
                <div className="text-2xl font-semibold">Pheromind — Concept Trails</div>
                <button onClick={() => setShowPheromind(true)} className="px-3 py-2 rounded-xl text-sm border inline-flex items-center gap-2" style={{ background: GLASS.bg, borderColor: GLASS.border }}><Maximize2 className="h-4 w-4" /> Expand</button>
              </div>
              <PheromindMini edges={edges} />
              <div className="flex gap-3">
                {edges.map((_, i) => (
                  <button key={i} onClick={() => reinforce(i)} className="px-4 py-2 rounded-xl text-sm border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>Reinforce #{i + 1}</button>
                ))}
              </div>
            </div>
          )}

          {page === "calendar" && (
            <div className="rounded-3xl p-8 border backdrop-blur-xl space-y-6" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <div className="text-2xl font-semibold">Calendar — Missions</div>
              <div className="grid grid-cols-2 gap-6">
                <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                  <div className="text-lg font-medium">Outbound campaign draft</div>
                  <div className="text-sm mt-1" style={{ color: TXT_MUTED }}>agent_task • active • 09:00</div>
                </div>
                <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                  <div className="text-lg font-medium">Data vendor review</div>
                  <div className="text-sm mt-1" style={{ color: TXT_MUTED }}>review • planned • 13:00</div>
                </div>
              </div>
              <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>Drag-drop timeline placeholder</div>
            </div>
          )}

          {page === "projects" && (
            <div className="rounded-3xl p-8 border backdrop-blur-xl space-y-6" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <div className="text-2xl font-semibold">Projects — Mission Control</div>
              <div className="grid grid-cols-2 gap-6">
                <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                  <div className="text-lg font-medium">Launch Brief v2</div>
                  <div className="text-sm mt-1" style={{ color: TXT_MUTED }}>in-progress</div>
                </div>
                <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                  <div className="text-lg font-medium">Ops Playbook</div>
                  <div className="text-sm mt-1" style={{ color: TXT_MUTED }}>review</div>
                </div>
              </div>
              <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>Native doc editor & Kanban placeholder</div>
            </div>
          )}

          {page === "system" && (
            <div className="rounded-3xl p-8 border backdrop-blur-xl space-y-6" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <div className="text-2xl font-semibold">System — Governance & Audit</div>
              <div className="grid grid-cols-3 gap-6">
                <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                  <div className="text-lg font-medium mb-2">Operational Mode</div>
                  <ModeToggle mode={mode} setMode={setMode} />
                </div>
                <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                  <div className="text-lg font-medium mb-2">Tool Permissions</div>
                  <div className="text-sm" style={{ color: TXT_MUTED }}>Registry placeholder</div>
                </div>
                <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                  <div className="text-lg font-medium mb-2">Audit Stream</div>
                  <ul className="space-y-2 text-sm">
                    <li>2m • Override accepted on Agent spend</li>
                    <li>1h • Constitutional check passed</li>
                  </ul>
                </div>
              </div>
            </div>
          )}
        </main>

        {/* Right panel: independent sections remain visible */}
        <aside className="col-span-3">
          <div className="flex flex-col gap-6">
            {/* Treasury */}
            <div className="rounded-3xl p-8 border backdrop-blur-xl" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <div className="flex items-center justify-between mb-6">
                <div className="text-xl font-semibold">Treasury</div>
                <button onClick={() => setShowTreasury(true)} className="px-3 py-2 rounded-xl text-sm border inline-flex items-center gap-2" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                  <Maximize2 className="h-4 w-4" /> Expand
                </button>
              </div>
              <div className="grid grid-cols-3 gap-6 mb-8">
                <KPI label="Available" value={`$${treasury.balance.toLocaleString()}`} />
                <KPI label="Allocated" value={`$${treasury.allocated.toLocaleString()}`} />
                <KPI label="Net P&L (wk)" value={`+$${treasury.pnlWeek}`} trend="up" />
              </div>
              <div className="text-base font-medium mb-3" style={{ color: TXT_MUTED }}>Recent transactions</div>
              <ul className="space-y-3">
                {treasury.tx.map((t) => (
                  <li key={t.id} className="flex items-center justify-between px-4 py-3 rounded-xl border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                    <span>{t.when} • {t.label}</span>
                    <span className={t.amount >= 0 ? "text-emerald-300" : "text-rose-300"}>{t.amount >= 0 ? "+$" + t.amount : "-$" + Math.abs(t.amount)}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* KIP Agents */}
            <div className="rounded-3xl p-8 border backdrop-blur-xl" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <div className="flex items-center justify-between mb-6">
                <div className="text-xl font-semibold">KIP Agents</div>
                <button onClick={() => { setShowAgents(true); setAgentDetail(null); }} className="px-3 py-2 rounded-xl text-sm border inline-flex items-center gap-2" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                  <Maximize2 className="h-4 w-4" /> Expand
                </button>
              </div>
              <div className="space-y-4">
                {agents.map((a) => (
                  <AgentCard key={a.id} a={a} onDetails={() => { setShowAgents(true); setAgentDetail(a); }} />
                ))}
              </div>
            </div>

            {/* Pheromind */}
            <div className="rounded-3xl p-8 border backdrop-blur-xl" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <div className="flex items-center justify-between mb-6">
                <div className="text-xl font-semibold">Pheromind</div>
                <button onClick={() => setShowPheromind(true)} className="px-3 py-2 rounded-xl text-sm border inline-flex items-center gap-2" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                  <Maximize2 className="h-4 w-4" /> Expand
                </button>
              </div>
              <PheromindMini edges={edges} />
            </div>
          </div>
        </aside>
      </div>

      {/* Settings drawer (hosts Operational Mode) */}
      {showSettings && (
        <div className="fixed inset-0 z-50" style={{ background: "rgba(0,0,0,0.5)" }} onClick={() => setShowSettings(false)}>
          <div className="absolute right-0 top-0 h-full w-[560px] p-12 overflow-auto border-l" style={{ background: BG, borderColor: GLASS.border }} onClick={(e) => e.stopPropagation()}>
            <div className="text-2xl font-semibold mb-8">Settings</div>
            <div className="space-y-8">
              <section>
                <div className="text-lg font-medium mb-3">Operational Mode</div>
                <ModeToggle mode={mode} setMode={setMode} />
              </section>
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

      {/* Fullscreens */}
      {showTreasury && (
        <Fullscreen title="Treasury — Detail" onClose={() => setShowTreasury(false)}>
          <div className="grid grid-cols-3 gap-8">
            <KPI label="Available" value={`$${treasury.balance.toLocaleString()}`} />
            <KPI label="Allocated" value={`$${treasury.allocated.toLocaleString()}`} />
            <KPI label="Net P&L (wk)" value={`+$${treasury.pnlWeek}`} trend="up" />
          </div>
          <div className="mt-8 rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>Spending trends & forecasts (placeholder)</div>
        </Fullscreen>
      )}
      {showAgents && (
        <Fullscreen title={agentDetail ? `Agent — ${agentDetail.name}` : "KIP Agents — Detail"} onClose={() => { setShowAgents(false); setAgentDetail(null); }}>
          {!agentDetail ? (
            <div className="grid grid-cols-3 gap-6">
              {agents.map((a) => <AgentCard key={a.id} a={a} onDetails={() => setAgentDetail(a)} />)}
            </div>
          ) : (
            <div className="space-y-6">
              <AgentCard a={agentDetail} onDetails={() => {}} />
              <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                <div className="text-lg mb-2" style={{ color: TXT_MUTED }}>Recent actions</div>
                <ul className="space-y-3 text-base">
                  <li className="flex items-center justify-between px-4 py-3 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                    <span>Purchased $AAPL analysis from Bloomberg API</span>
                    <span className="text-rose-300">-$12</span>
                  </li>
                  <li className="flex items-center justify-between px-4 py-3 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                    <span>Completed client report</span>
                    <span className="text-emerald-300">+$150</span>
                  </li>
                </ul>
              </div>
            </div>
          )}
        </Fullscreen>
      )}
      {showPheromind && (
        <Fullscreen title="Pheromind — Concept Trails" onClose={() => setShowPheromind(false)}>
          <PheromindCanvas edges={edges} onReinforce={reinforce} />
        </Fullscreen>
      )}
    </div>
  );
}

// ---------- Page: Council (Chat) ----------
function CouncilChat({ listRef, messages, mode, composer, setComposer, taRef, MAX_LINES, autosize, streaming, send, stop, collections, activeConv, activeId, updateConvCollection }) {
  return (
    <div className="rounded-3xl p-8 border backdrop-blur-xl" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
      {/* Thread header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="text-2xl font-semibold">{activeConv?.title || "Conversation"}</div>
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs" style={{ color: TXT_MUTED }}>Collection:</span>
            <select
              className="text-xs px-2 py-1 rounded-lg border bg-transparent"
              style={{ borderColor: GLASS.border }}
              value={activeConv?.collection || "All"}
              onChange={(e) => updateConvCollection(e.target.value)}
            >
              {collections.map((c) => (
                <option key={c.id} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>
          <div className="text-sm mt-2" style={{ color: TXT_MUTED }}>Unified response with verification • Send→Stop toggle while streaming</div>
        </div>
        <div className="flex items-center gap-3">
          <SlashQuickActions onPick={(cmd) => setComposer((t) => (t ? t + ` ${cmd} ` : cmd + " "))} />
        </div>
      </div>

      {/* Messages */}
      <div ref={listRef} className="space-y-6 pr-1" style={{ maxHeight: 540, overflow: "auto" }}>
        {messages.map((m) => (
          <MessageBubble key={m.id} m={m} mode={mode} />
        ))}
      </div>

      {/* Composer — auto-size + contextual Stop */}
      <div className="mt-8 rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
        <div className="flex items-center justify-between mb-4">
          <div className="text-base" style={{ color: TXT_MUTED }}>{composer ? "" : "Available: /analyze  /budget  /pheromind"}</div>
          <div className="flex items-center gap-3">
            <button title="Attach" className="p-3 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <Paperclip className="h-5 w-5" />
            </button>
            <button onClick={() => {}} className="p-3 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <Mic className="h-5 w-5" />
            </button>
          </div>
        </div>
        <textarea
          ref={taRef}
          value={composer}
          onChange={(e) => setComposer(e.target.value)}
          rows={1}
          placeholder="Type a message…"
          className="w-full bg-transparent outline-none text-lg placeholder-white/40 resize-none"
          style={{ lineHeight: "28px", maxHeight: 28 * MAX_LINES }}
        />
        <div className="mt-4 flex items-center justify-between">
          <div className="text-sm" style={{ color: TXT_MUTED }}>Press ⌘⏎ to send</div>
          {!streaming ? (
            <button onClick={() => { setTimeout(send, 10); setStreamingHint(); }} className="px-6 py-3 rounded-2xl text-lg font-medium border inline-flex items-center gap-2" style={{ background: ACCENT, borderColor: GLASS.border, boxShadow: `0 8px 30px ${PURPLE}33` }}>
              <Send className="h-5 w-5" /> Send
            </button>
          ) : (
            <button onClick={stop} className="px-6 py-3 rounded-2xl text-lg font-medium border inline-flex items-center gap-2" style={{ background: GLASS.bg, borderColor: GLASS.border }}>
              <StopCircle className="h-5 w-5" /> Stop generating
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// little helper so the button flips to Stop immediately when you click Send (purely visual in mock)
function setStreamingHint() {}

// ---------- Reusable components ----------
function ModeToggle({ mode, setMode }) {
  return (
    <div className="flex items-center gap-3">
      {(["MANUAL", "SUPERVISED", "AUTONOMOUS"]).map((m) => (
        <button key={m} onClick={() => setMode(m)} className={`px-5 py-3 rounded-2xl text-base font-medium border ${mode === m ? "" : "opacity-70"}`} style={{ background: mode === m ? "rgba(109,91,208,0.25)" : GLASS.bg, borderColor: GLASS.border, boxShadow: mode === m ? `0 8px 24px ${PURPLE}33` : "none" }}>{m}</button>
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
    <button onClick={onClick} className={`w-full rounded-2xl text-left ${active ? "" : "opacity-90"}`} style={{ padding: 18, background: active ? ACCENT : GLASS.subtle, border: `1px solid ${GLASS.border}`, boxShadow: active ? `0 8px 24px ${PURPLE}33` : "none" }}>
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
        {unread ? <span className="ml-auto text-sm px-3 py-1 rounded-xl" style={{ background: GLASS.bg }}>{unread}</span> : null}
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
        <div className="text-lg leading-relaxed rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border, boxShadow: isUser ? "none" : `0 8px 24px ${PURPLE}22` }}>
          {m.text}
          {!isUser && (
            <div className="mt-3 flex items-center gap-2 text-sm">
              {m.status === "generating" && <span className="px-3 py-1 rounded-xl" style={{ background: "rgba(251,191,36,0.15)" }}>Generating…</span>}
              {m.status === "verifying" && <span className="px-3 py-1 rounded-xl" style={{ background: "rgba(59,130,246,0.20)" }}>Verifying…</span>}
              {m.status === "complete" && (
                <span className="inline-flex items-center gap-2 text-sm px-3 py-1 rounded-xl" style={{ background: "rgba(16,185,129,0.2)" }}>
                  <ShieldCheck className="h-4 w-4" /> Verified
                </span>
              )}
            </div>
          )}
        </div>
        <div className="mt-3 flex items-center gap-3" style={{ color: TXT_MUTED }}>
          <span className="text-sm">{m.ts}</span>
          {!isUser && (
            <>
              {mode === "MANUAL" && (
                <>
                  <button className="px-3 py-1 rounded-xl border" style={{ background: "rgba(34,197,94,0.18)", borderColor: GLASS.border }}><Check className="h-4 w-4" /> Approve</button>
                  <button className="px-3 py-1 rounded-xl border" style={{ background: "rgba(244,63,94,0.18)", borderColor: GLASS.border }}><X className="h-4 w-4" /> Reject</button>
                </>
              )}
              <button className="px-3 py-1 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}><Copy className="h-4 w-4" /> Copy</button>
              <button className="px-3 py-1 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }}><RotateCcw className="h-4 w-4" /> Regenerate</button>
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
        <button key={c} onClick={() => onPick(c)} className="px-4 py-2 rounded-xl border text-base" style={{ background: GLASS.bg, borderColor: GLASS.border, boxShadow: `0 6px 18px ${PURPLE}22` }}>{c}</button>
      ))}
    </div>
  );
}

function KPI({ label, value, trend }) {
  return (
    <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
      <div className="text-sm mb-2" style={{ color: TXT_MUTED }}>{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
      {trend === "up" && <div className="mt-2 text-emerald-300 text-sm">▲ improving</div>}
    </div>
  );
}

function AgentCard({ a, onDetails }) {
  return (
    <div className="rounded-2xl p-6 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
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
        <button onClick={onDetails} className="px-3 py-2 rounded-xl border text-sm" style={{ background: GLASS.bg, borderColor: GLASS.border }}>Details</button>
      </div>
    </div>
  );
}

function ToggleRow({ label, defaultChecked }) {
  const [on, setOn] = useState(!!defaultChecked);
  return (
    <label className="flex items-center justify-between px-5 py-4 rounded-2xl border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
      <span className="text-base">{label}</span>
      <button onClick={() => setOn((v) => !v)} className={`w-14 h-8 rounded-full relative transition ${on ? "bg-emerald-500/70" : "bg-white/20"}`}>
        <span className={`absolute top-1 left-1 h-6 w-6 rounded-full bg-white transition ${on ? "translate-x-6" : ""}`} />
      </button>
    </label>
  );
}

function PheromindMini({ edges }) {
  const pos = (s) => s.split("").reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 0);
  const coords = (label) => ({ x: 40 + (pos(label) % 180), y: 30 + ((pos(label) >> 5) % 90) });
  return (
    <div className="rounded-2xl p-4 border" style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
      <svg viewBox="0 0 260 140" className="w-full h-[120px]">
        {edges.slice(0, 3).map((e, i) => {
          const A = coords(e.a), B = coords(e.b);
          return (
            <g key={i}>
              <defs>
                <linearGradient id={`mini${i}`} x1="0" y1="0" x2="1" y2="1">
                  <stop offset="0%" stopColor={PURPLE} />
                  <stop offset="100%" stopColor="#c084fc" />
                </linearGradient>
              </defs>
              <line x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={`url(#mini${i})`} strokeWidth={Math.max(1.2, e.s * 6)} strokeOpacity={0.9} />
              <circle cx={A.x} cy={A.y} r={7} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
              <circle cx={B.x} cy={B.y} r={7} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
            </g>
          );
        })}
      </svg>
      <div className="mt-2 text-sm" style={{ color: TXT_MUTED }}>Trails strengthen with repetition; decay over ~12s.</div>
    </div>
  );
}

function Fullscreen({ title, children, onClose }) {
  return (
    <div className="fixed inset-0 z-50" style={{ background: "rgba(0,0,0,0.7)" }} onClick={onClose}>
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[1200px] h-[700px] rounded-3xl p-12 border backdrop-blur-xl" style={{ background: GLASS.bg, borderColor: GLASS.border }} onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-8">
          <div className="text-2xl font-semibold">{title}</div>
          <button className="px-4 py-2 rounded-xl border" style={{ background: GLASS.bg, borderColor: GLASS.border }} onClick={onClose}>Close</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function PheromindCanvas({ edges, onReinforce }) {
  const pos = (s) => s.split("").reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 0);
  const coords = (label) => ({ x: 120 + (pos(label) % 800), y: 80 + ((pos(label) >> 5) % 420) });
  return (
    <div className="w-full h-full relative rounded-2xl overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
      <svg viewBox="0 0 1200 600" className="absolute inset-0 w-full h-full">
        {edges.map((e, i) => { const A = coords(e.a), B = coords(e.b); return (
          <g key={i}>
            <defs>
              <linearGradient id={`g${i}`} x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor={PURPLE} />
                <stop offset="100%" stopColor="#c084fc" />
              </linearGradient>
            </defs>
            <line x1={A.x} y1={A.y} x2={B.x} y2={B.y} stroke={`url(#g${i})`} strokeWidth={Math.max(1.5, e.s * 8)} strokeOpacity={0.9} />
            <circle cx={A.x} cy={A.y} r={12} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
            <circle cx={B.x} cy={B.y} r={12} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
            <text x={A.x} y={A.y - 16} textAnchor="middle" fill="#fff" fontSize="12">{e.a}</text>
            <text x={B.x} y={B.y - 16} textAnchor="middle" fill="#fff" fontSize="12">{e.b}</text>
          </g>
        );})}
      </svg>
      <div className="absolute bottom-6 left-6 flex gap-3">
        {edges.map((_, i) => (
          <button key={i} onClick={() => onReinforce(i)} className="px-4 py-2 rounded-xl text-sm border" style={{ background: GLASS.bg, borderColor: GLASS.border }}>Reinforce #{i + 1}</button>
        ))}
      </div>
    </div>
  );
}
