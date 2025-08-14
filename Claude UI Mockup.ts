<artifact identifier="hac-unified-command-v5" type="text/html" title="HAC Unified Command Center - Interactive UI">
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HAC Unified Command Center</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; margin: 0; padding: 0; }
        .scrollbar-thin::-webkit-scrollbar { width: 6px; }
        .scrollbar-thin::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
        .scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 3px; }
        .glass { backdrop-filter: blur(12px); }
    </style>
</head>
<body>
    <div id="root"></div>
    <script type="text/babel">
        const { useState, useEffect, useRef } = React;
    // Theme constants
    const BG = "#15141c";
    const ACCENT = "#232046";
    const PURPLE = "#7c5cf6";
    const TXT_MUTED = "#a1a1aa";
    const GLASS = { 
        bg: "rgba(255,255,255,0.15)", 
        border: "rgba(255,255,255,0.2)", 
        subtle: "rgba(255,255,255,0.10)" 
    };

    // Utils
    const uid = () => Math.random().toString(36).slice(2);
    const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    function HACUnifiedUI() {
        // Navigation & Layout
        const [page, setPage] = useState("council");
        const [navOpen, setNavOpen] = useState(false);
        const [collapsed, setCollapsed] = useState(false);
        const [mode, setMode] = useState("SUPERVISED");
        const [showSettings, setShowSettings] = useState(false);
        const [showTreasury, setShowTreasury] = useState(false);
        const [showAgents, setShowAgents] = useState(false);
        const [showPheromind, setShowPheromind] = useState(false);

        // Conversations & Collections
        const [collections] = useState([
            { id: uid(), name: "All" },
            { id: uid(), name: "Work" },
            { id: uid(), name: "Research" },
            { id: uid(), name: "Personal" }
        ]);
        const [activeCollection, setActiveCollection] = useState("All");
        const [pinned] = useState([
            { id: uid(), title: "Quarterly Strategy", unread: 0, collection: "Work" },
            { id: uid(), title: "Crypto Rebalance", unread: 2, collection: "Research" }
        ]);
        const [recents] = useState([
            { id: uid(), title: "Agent Budget Tuning", unread: 0, collection: "Work" },
            { id: uid(), title: "Marketing Experiment", unread: 1, collection: "Work" },
            { id: uid(), title: "Model Upgrade Review", unread: 0, collection: "Personal" }
        ]);
        const [activeConvId, setActiveConvId] = useState(pinned[0].id);
        const activeConv = [...pinned, ...recents].find(c => c.id === activeConvId);

        // Chat state
        const [messages, setMessages] = useState([
            { id: uid(), role: "user", ts: now(), text: "Help me analyze the crypto market for portfolio rebalancing." },
            { id: uid(), role: "assistant", ts: now(), status: "complete", verified: true, text: "I've analyzed the current crypto market conditions. Based on volatility indices and correlation patterns, I recommend a 5% rebalancing from BTC to ETH, with 3% allocation to stablecoins for risk mitigation." }
        ]);
        const [composer, setComposer] = useState("");
        const [streaming, setStreaming] = useState(false);
        const taRef = useRef(null);
        const listRef = useRef(null);
        const streamRef = useRef({ timeout: null });

        // Auto-resize textarea
        useEffect(() => {
            if (!taRef.current) return;
            const el = taRef.current;
            el.style.height = "auto";
            const lh = 28;
            el.style.height = Math.min(el.scrollHeight, lh * 6) + "px";
        }, [composer]);

        // Treasury & Agents data
        const [treasury] = useState({
            balance: 2847,
            allocated: 1203,
            weekPnL: 546,
            tx: [
                { id: uid(), ts: "2m", label: "Constitutional verification", amount: -4.18 },
                { id: uid(), ts: "8m", label: "API usage", amount: -39.6 },
                { id: uid(), ts: "1h", label: "GPU hours", amount: -12.0 },
                { id: uid(), ts: "1h", label: "Client payment", amount: 210.0 }
            ]
        });

        const agents = [
            { id: uid(), name: "Sarah", role: "ContentCreation_Agent", revenue: 347, spend: 89, net: 258 },
            { id: uid(), name: "StockAnalyst_Agent", role: "Equities", revenue: 160, spend: 48, net: 112 },
            { id: uid(), name: "MarketResearch_Agent", role: "Insights", revenue: 240, spend: 64, net: 176 }
        ];

        // Pheromind edges
        const [edges, setEdges] = useState([
            { a: "Bitcoin", b: "Inflation", s: 0.82 },
            { a: "Inflation", b: "Gold", s: 0.80 },
            { a: "AI regulation", b: "European markets", s: 0.87 }
        ]);

        // Decay simulation
        useEffect(() => {
            const interval = setInterval(() => {
                setEdges(prev => prev.map(e => ({ ...e, s: Math.max(0.2, e.s - 0.01) })));
            }, 1000);
            return () => clearInterval(interval);
        }, []);

        const reinforce = (idx) => {
            setEdges(prev => prev.map((e, i) => 
                i === idx ? { ...e, s: Math.min(0.95, e.s + 0.15) } : e
            ));
        };

        // Filter conversations by collection
        const filterByCollection = (convs) => {
            if (activeCollection === "All") return convs;
            return convs.filter(c => c.collection === activeCollection);
        };

        // Send message
        const send = () => {
            if (!composer.trim() || streaming) return;
            const userMsg = { id: uid(), role: "user", ts: now(), text: composer.trim() };
            setMessages(prev => [...prev, userMsg]);
            setComposer("");
            
            // Start streaming AI response
            setStreaming(true);
            const aiId = uid();
            const aiMsg = { 
                id: aiId, 
                role: "assistant", 
                ts: now(), 
                status: "generating", 
                text: "Analyzing market conditions..." 
            };
            setMessages(prev => [...prev, aiMsg]);
            
            // Simulate progressive status
            streamRef.current.timeout = setTimeout(() => {
                setMessages(prev => prev.map(m => 
                    m.id === aiId 
                        ? { ...m, status: "verifying", text: "Running constitutional verification on the analysis..." }
                        : m
                ));
                
                setTimeout(() => {
                    setMessages(prev => prev.map(m => 
                        m.id === aiId 
                            ? { 
                                ...m, 
                                status: "complete", 
                                verified: true,
                                text: "Based on current market analysis: BTC dominance at 48%, ETH showing strong momentum. Recommend 5% portfolio rebalancing with risk-adjusted stops at -8%. Constitutional verification passed with 0.94 confidence." 
                              }
                            : m
                    ));
                    setStreaming(false);
                }, 1500);
            }, 1500);
        };

        const stop = () => {
            if (streamRef.current.timeout) {
                clearTimeout(streamRef.current.timeout);
            }
            setStreaming(false);
            setMessages(prev => prev.map(m => 
                m.status === "generating" || m.status === "verifying"
                    ? { ...m, status: "complete", text: m.text + " (interrupted)" }
                    : m
            ));
        };

        // Scroll to bottom on new messages
        useEffect(() => {
            if (listRef.current) {
                listRef.current.scrollTop = listRef.current.scrollHeight;
            }
        }, [messages]);

        return (
            <div className="min-h-screen" style={{ background: BG, color: "#fff" }}>
                {/* Top Navigation Bar */}
                <header className="h-20 flex items-center justify-between px-12 border-b relative z-50" 
                        style={{ borderColor: "rgba(255,255,255,0.12)" }}>
                    <div className="flex items-center gap-6">
                        {/* Logo */}
                        <div className="h-12 w-12 rounded-2xl grid place-items-center" 
                             style={{ background: ACCENT, boxShadow: `0 0 0 1px ${PURPLE}44, 0 12px 36px ${PURPLE}33` }}>
                            <div className="h-7 w-7 rounded-xl" 
                                 style={{ background: `linear-gradient(135deg, ${PURPLE}, ${ACCENT})` }} />
                        </div>
                        
                        {/* Page Dropdown Navigation */}
                        <div className="relative">
                            <button onClick={() => setNavOpen(!navOpen)} 
                                    className="px-4 py-2 rounded-xl border inline-flex items-center gap-2 capitalize"
                                    style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                <span className="text-base font-medium">
                                    {page === "kip" ? "KIP Engine" : page}
                                </span>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>
                            
                            {navOpen && (
                                <div className="absolute left-0 top-full mt-2 w-56 rounded-2xl border p-2 shadow-2xl"
                                     style={{ background: BG, borderColor: GLASS.border }}>
                                    {["council", "kip", "pheromind", "calendar", "projects", "system"].map(p => (
                                        <button key={p}
                                                onClick={() => { setPage(p); setNavOpen(false); }}
                                                className="w-full text-left px-4 py-3 rounded-xl capitalize mb-1 transition-all"
                                                style={{ 
                                                    background: page === p ? ACCENT : GLASS.subtle,
                                                    border: `1px solid ${GLASS.border}`
                                                }}>
                                            {p === "kip" ? "KIP Engine" : p}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                        
                        <div className="text-xl font-semibold">Hybrid AI Council</div>
                    </div>
                    
                    <div className="flex items-center gap-6">
                        <div className="px-4 py-2 rounded-xl border glass"
                             style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                            <span className="text-sm" style={{ color: TXT_MUTED }}>WS</span>
                            <span className="ml-2 text-emerald-400">Connected</span>
                        </div>
                        <button onClick={() => setShowSettings(true)}
                                className="px-4 py-2 rounded-xl border text-sm inline-flex items-center gap-2"
                                style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                      d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            Settings
                        </button>
                    </div>
                </header>

                {/* Main Layout Grid */}
                <div className="grid grid-cols-12 gap-8 mx-8 my-8">
                    {/* Left Sidebar - Conversations + Collections */}
                    <aside className="col-span-3" style={{ width: collapsed ? 80 : 320, transition: "width .2s" }}>
                        <div className="flex items-center justify-between mb-6">
                            <div className="text-lg font-medium" style={{ color: TXT_MUTED }}>
                                {!collapsed && "Conversations"}
                            </div>
                            <button onClick={() => setCollapsed(!collapsed)}
                                    className="p-3 rounded-xl border"
                                    style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                {collapsed ? "→" : "←"}
                            </button>
                        </div>
                        
                        {!collapsed && (
                            <>
                                {/* Search */}
                                <div className="mb-4">
                                    <div className="flex items-center gap-3 px-4 py-3 rounded-2xl border glass"
                                         style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                        </svg>
                                        <input placeholder="Search conversations..."
                                               className="bg-transparent outline-none text-base flex-1" />
                                    </div>
                                </div>
                                
                                {/* Collections */}
                                <div className="mb-6 flex items-center flex-wrap gap-2">
                                    {collections.map(c => (
                                        <button key={c.id}
                                                onClick={() => setActiveCollection(c.name)}
                                                className="px-3 py-1 rounded-xl border text-sm transition-all"
                                                style={{ 
                                                    background: activeCollection === c.name ? PURPLE + "30" : GLASS.bg,
                                                    borderColor: GLASS.border,
                                                    opacity: activeCollection === c.name ? 1 : 0.8
                                                }}>
                                            {c.name}
                                        </button>
                                    ))}
                                    <button className="px-3 py-1 rounded-xl border text-sm inline-flex items-center gap-1"
                                            style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <span>+</span> New
                                    </button>
                                </div>
                                
                                {/* Pinned Conversations */}
                                <div className="mb-6">
                                    <div className="text-sm mb-3" style={{ color: TXT_MUTED }}>Pinned</div>
                                    <div className="space-y-3">
                                        {filterByCollection(pinned).map(conv => (
                                            <button key={conv.id}
                                                    onClick={() => setActiveConvId(conv.id)}
                                                    className="w-full rounded-2xl p-4 text-left transition-all"
                                                    style={{ 
                                                        background: activeConvId === conv.id ? ACCENT : GLASS.subtle,
                                                        border: `1px solid ${GLASS.border}`,
                                                        boxShadow: activeConvId === conv.id ? `0 8px 24px ${PURPLE}33` : "none"
                                                    }}>
                                                <div className="text-base font-medium">{conv.title}</div>
                                                {conv.unread > 0 && (
                                                    <span className="text-xs px-2 py-1 rounded-lg mt-1 inline-block"
                                                          style={{ background: PURPLE + "30" }}>
                                                        {conv.unread} new
                                                    </span>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                
                                {/* Recent Conversations */}
                                <div>
                                    <div className="text-sm mb-3" style={{ color: TXT_MUTED }}>Recent</div>
                                    <div className="space-y-3">
                                        {filterByCollection(recents).map(conv => (
                                            <button key={conv.id}
                                                    onClick={() => setActiveConvId(conv.id)}
                                                    className="w-full rounded-2xl p-4 text-left transition-all"
                                                    style={{ 
                                                        background: activeConvId === conv.id ? ACCENT : GLASS.subtle,
                                                        border: `1px solid ${GLASS.border}`,
                                                        boxShadow: activeConvId === conv.id ? `0 8px 24px ${PURPLE}33` : "none"
                                                    }}>
                                                <div className="text-base font-medium">{conv.title}</div>
                                                {conv.unread > 0 && (
                                                    <span className="text-xs px-2 py-1 rounded-lg mt-1 inline-block"
                                                          style={{ background: PURPLE + "30" }}>
                                                        {conv.unread} new
                                                    </span>
                                                )}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </>
                        )}
                    </aside>

                    {/* Center Content Area */}
                    <main className="col-span-6">
                        {page === "council" && (
                            <div className="rounded-3xl p-8 border glass"
                                 style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                <div className="flex items-center justify-between mb-6">
                                    <div>
                                        <div className="text-2xl font-semibold">{activeConv?.title || "Council"}</div>
                                        <div className="mt-2 flex items-center gap-2">
                                            <span className="text-xs" style={{ color: TXT_MUTED }}>Collection:</span>
                                            <select className="text-xs px-2 py-1 rounded-lg border bg-transparent"
                                                    style={{ borderColor: GLASS.border }}
                                                    value={activeConv?.collection || "All"}>
                                                {collections.map(c => (
                                                    <option key={c.id} value={c.name} style={{ background: BG }}>
                                                        {c.name}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="text-sm mt-2" style={{ color: TXT_MUTED }}>
                                            Unified response with constitutional verification • Send→Stop toggle while streaming
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        {["/analyze", "/budget", "/pheromind"].map(cmd => (
                                            <button key={cmd}
                                                    onClick={() => setComposer(composer + " " + cmd + " ")}
                                                    className="px-4 py-2 rounded-xl border text-sm"
                                                    style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                {cmd}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                
                                {/* Messages */}
                                <div ref={listRef} className="space-y-6 pr-1 scrollbar-thin" 
                                     style={{ maxHeight: 440, overflow: "auto" }}>
                                    {messages.map(m => (
                                        <div key={m.id} className={`flex gap-4 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
                                            <div className="h-10 w-10 rounded-2xl grid place-items-center flex-shrink-0"
                                                 style={{ background: m.role === "user" ? "rgba(255,255,255,0.12)" : ACCENT }}>
                                                <span className="text-sm font-medium">{m.role === "user" ? "U" : "AI"}</span>
                                            </div>
                                            <div className="flex-1">
                                                <div className="text-lg leading-relaxed rounded-2xl p-6 border relative"
                                                     style={{ 
                                                         background: GLASS.subtle, 
                                                         borderColor: GLASS.border,
                                                         boxShadow: m.role === "user" ? "none" : `0 8px 24px ${PURPLE}22`
                                                     }}>
                                                    {m.text}
                                                    {m.role === "assistant" && (
                                                        <div className="mt-3 flex items-center gap-2 text-sm">
                                                            {m.status === "generating" && (
                                                                <>
                                                                    <span className="px-3 py-1 rounded-xl"
                                                                          style={{ background: "rgba(251,191,36,0.15)" }}>
                                                                        Generating...
                                                                    </span>
                                                                    <button onClick={stop}
                                                                            className="px-3 py-1 rounded-xl border inline-flex items-center gap-2"
                                                                            style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                                                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                                                  d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                                                                        </svg>
                                                                        Stop
                                                                    </button>
                                                                </>
                                                            )}
                                                            {m.status === "verifying" && (
                                                                <>
                                                                    <span className="px-3 py-1 rounded-xl"
                                                                          style={{ background: "rgba(59,130,246,0.20)" }}>
                                                                        Verifying...
                                                                    </span>
                                                                    <button onClick={stop}
                                                                            className="px-3 py-1 rounded-xl border inline-flex items-center gap-2"
                                                                            style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                                                  d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                                                  d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                                                                        </svg>
                                                                        Stop
                                                                    </button>
                                                                </>
                                                            )}
                                                            {m.status === "complete" && m.verified && (
                                                                <span className="px-3 py-1 rounded-xl inline-flex items-center gap-2"
                                                                      style={{ background: "rgba(16,185,129,0.2)" }}>
                                                                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                                                        <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                                    </svg>
                                                                    Verified
                                                                </span>
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                                <div className="mt-3 flex items-center gap-3 text-sm" style={{ color: TXT_MUTED }}>
                                                    <span>{m.ts}</span>
                                                    {m.role === "assistant" && mode === "MANUAL" && m.status === "complete" && (
                                                        <>
                                                            <button className="px-3 py-1 rounded-xl border inline-flex items-center gap-1"
                                                                    style={{ background: "rgba(34,197,94,0.18)", borderColor: GLASS.border }}>
                                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                                                </svg>
                                                                Approve
                                                            </button>
                                                            <button className="px-3 py-1 rounded-xl border inline-flex items-center gap-1"
                                                                    style={{ background: "rgba(244,63,94,0.18)", borderColor: GLASS.border }}>
                                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                                                </svg>
                                                                Reject
                                                            </button>
                                                        </>
                                                    )}
                                                    {m.role === "assistant" && (
                                                        <>
                                                            <button className="px-3 py-1 rounded-xl border"
                                                                    style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                                Copy
                                                            </button>
                                                            <button className="px-3 py-1 rounded-xl border"
                                                                    style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                                Regenerate
                                                            </button>
                                                        </>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                
                                {/* Composer with auto-sizing and ChatGPT-style Send→Stop */}
                                <div className="mt-8 rounded-2xl p-6 border"
                                     style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                    <div className="flex items-center justify-between mb-4">
                                        <div className="text-base" style={{ color: TXT_MUTED }}>
                                            {composer ? "" : "Available: /analyze  /budget  /pheromind"}
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <button className="p-3 rounded-xl border"
                                                    style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                          d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                                                </svg>
                                            </button>
                                            <button className="p-3 rounded-xl border"
                                                    style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                    <textarea
                                        ref={taRef}
                                        value={composer}
                                        onChange={(e) => setComposer(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && e.metaKey) {
                                                e.preventDefault();
                                                send();
                                            }
                                        }}
                                        rows={1}
                                        placeholder="Type a message..."
                                        className="w-full bg-transparent outline-none text-lg placeholder-white/40 resize-none"
                                        style={{ lineHeight: "28px", maxHeight: 28 * 6 }}
                                    />
                                    <div className="mt-4 flex items-center justify-between">
                                        <div className="text-sm" style={{ color: TXT_MUTED }}>Press ⌘↩ to send</div>
                                        {!streaming ? (
                                            <button onClick={send}
                                                    className="px-6 py-3 rounded-2xl text-lg font-medium border inline-flex items-center gap-2"
                                                    style={{ 
                                                        background: ACCENT, 
                                                        borderColor: GLASS.border, 
                                                        boxShadow: `0 8px 30px ${PURPLE}33` 
                                                    }}>
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                          d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                                </svg>
                                                Send
                                            </button>
                                        ) : (
                                            <button onClick={stop}
                                                    className="px-6 py-3 rounded-2xl text-lg font-medium border inline-flex items-center gap-2"
                                                    style={{ 
                                                        background: "rgba(244,63,94,0.2)", 
                                                        borderColor: "rgba(244,63,94,0.5)"
                                                    }}>
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                          d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                          d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                                                </svg>
                                                Stop generating
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                        
                        {page === "kip" && (
                            <div className="rounded-3xl p-8 border glass space-y-8"
                                 style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                <div className="flex items-center justify-between">
                                    <div className="text-2xl font-semibold">KIP Engine — Operations</div>
                                    <button onClick={() => setShowAgents(true)}
                                            className="px-3 py-2 rounded-xl text-sm border inline-flex items-center gap-2"
                                            style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                  d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                                        </svg>
                                        Expand
                                    </button>
                                </div>
                                <div className="grid grid-cols-3 gap-6">
                                    {agents.map(a => (
                                        <div key={a.id} className="rounded-2xl p-6 border"
                                             style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <div className="text-lg font-medium">{a.name}</div>
                                                    <div className="text-sm" style={{ color: TXT_MUTED }}>{a.role}</div>
                                                </div>
                                                <div className="text-right">
                                                    <div className="text-sm" style={{ color: TXT_MUTED }}>Net</div>
                                                    <div className={`text-xl font-semibold ${a.net >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                                        {a.net >= 0 ? "+$" + a.net : "-$" + Math.abs(a.net)}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="grid grid-cols-3 gap-4 mt-4 text-sm">
                                                <div>Revenue <span className="text-emerald-300">${a.revenue}</span></div>
                                                <div>Spend <span className="text-rose-300">${a.spend}</span></div>
                                                <button className="px-3 py-2 rounded-xl border text-sm"
                                                        style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                    Details
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                        
                        {page === "pheromind" && (
                            <div className="rounded-3xl p-8 border glass space-y-6"
                                 style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                <div className="flex items-center justify-between">
                                    <div className="text-2xl font-semibold">Pheromind — Concept Trails</div>
                                    <button onClick={() => setShowPheromind(true)}
                                            className="px-3 py-2 rounded-xl text-sm border inline-flex items-center gap-2"
                                            style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                                                  d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                                        </svg>
                                        Expand
                                    </button>
                                </div>
                                <div className="rounded-2xl p-4 border"
                                     style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                    <svg viewBox="0 0 260 140" className="w-full h-[120px]">
                                        {edges.map((e, i) => {
                                            const pos = (s) => s.split("").reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 0);
                                            const A = { x: 40 + (pos(e.a) % 180), y: 30 + ((pos(e.a) >> 5) % 90) };
                                            const B = { x: 40 + (pos(e.b) % 180), y: 30 + ((pos(e.b) >> 5) % 90) };
                                            return (
                                                <g key={i}>
                                                    <defs>
                                                        <linearGradient id={`mini${i}`} x1="0" y1="0" x2="1" y2="1">
                                                            <stop offset="0%" stopColor={PURPLE} />
                                                            <stop offset="100%" stopColor="#c084fc" />
                                                        </linearGradient>
                                                    </defs>
                                                    <line x1={A.x} y1={A.y} x2={B.x} y2={B.y} 
                                                          stroke={`url(#mini${i})`} 
                                                          strokeWidth={Math.max(1.2, e.s * 6)} 
                                                          strokeOpacity={0.9} />
                                                    <circle cx={A.x} cy={A.y} r={7} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
                                                    <circle cx={B.x} cy={B.y} r={7} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
                                                </g>
                                            );
                                        })}
                                    </svg>
                                    <div className="mt-2 text-sm" style={{ color: TXT_MUTED }}>
                                        Trails strengthen with repetition; decay over ~12s.
                                    </div>
                                </div>
                                <div className="flex gap-3">
                                    {edges.map((_, i) => (
                                        <button key={i} onClick={() => reinforce(i)}
                                                className="px-4 py-2 rounded-xl text-sm border"
                                                style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                            Reinforce #{i + 1}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                        
                        {page === "calendar" && (
                            <div className="rounded-3xl p-8 border glass"
                                 style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                <div className="text-2xl font-semibold mb-6">Calendar — Missions</div>
                                <div className="rounded-2xl p-6 border"
                                     style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                    <div className="text-center" style={{ color: TXT_MUTED }}>
                                        Calendar view with agent tasks and missions will appear here
                                    </div>
                                </div>
                            </div>
                        )}
                        
                        {page === "projects" && (
                            <div className="rounded-3xl p-8 border glass"
                                 style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                <div className="text-2xl font-semibold mb-6">Projects — Mission Control</div>
                                <div className="rounded-2xl p-6 border"
                                     style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                    <div className="text-center" style={{ color: TXT_MUTED }}>
                                        Project management with documents and kanban will appear here
                                    </div>
                                </div>
                            </div>
                        )}
                        
                        {page === "system" && (
                            <div className="rounded-3xl p-8 border glass space-y-6"
                                 style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                <div className="text-2xl font-semibold">System — Governance & Audit</div>
                                <div className="grid grid-cols-3 gap-6">
                                    <div className="rounded-2xl p-6 border"
                                         style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                        <div className="text-lg font-medium mb-4">Operational Mode</div>
                                        <div className="flex flex-col gap-3">
                                            {["MANUAL", "SUPERVISED", "AUTONOMOUS"].map(m => (
                                                <button key={m}
                                                        onClick={() => setMode(m)}
                                                        className="px-4 py-3 rounded-xl text-sm font-medium border transition-all"
                                                        style={{ 
                                                            background: mode === m ? "rgba(124,92,246,0.25)" : GLASS.bg,
                                                            borderColor: GLASS.border,
                                                            boxShadow: mode === m ? `0 8px 24px ${PURPLE}33` : "none"
                                                        }}>
                                                    {m}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="rounded-2xl p-6 border"
                                         style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                        <div className="text-lg font-medium mb-2">Tool Permissions</div>
                                        <div className="text-sm" style={{ color: TXT_MUTED }}>
                                            Registry placeholder
                                        </div>
                                    </div>
                                    <div className="rounded-2xl p-6 border"
                                         style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
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

                    {/* Right Panel - Situational Awareness (Context-Sensitive) */}
                    <aside className="col-span-3">
                        <div className="flex flex-col gap-6">
                            {/* Contextual content based on active page */}
                            {page === "council" && (
                                <>
                                    <div className="rounded-3xl p-8 border glass"
                                         style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <div className="text-xl font-semibold mb-3">Verification & Rationale</div>
                                        <div className="text-sm" style={{ color: TXT_MUTED }}>
                                            Constitutional reasoning • TigerGraph traces • Confidence scores
                                        </div>
                                        <div className="mt-4 p-3 rounded-xl border"
                                             style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                            <div className="text-sm">Last verification: 0.94 confidence</div>
                                        </div>
                                    </div>
                                    <div className="rounded-3xl p-8 border glass"
                                         style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <div className="text-xl font-semibold mb-3">Suggested Actions</div>
                                        <ul className="space-y-2 text-sm">
                                            <li className="p-2 rounded-lg" style={{ background: GLASS.subtle }}>
                                                Run /analyze for risk assessment
                                            </li>
                                            <li className="p-2 rounded-lg" style={{ background: GLASS.subtle }}>
                                                Review agent allocations
                                            </li>
                                        </ul>
                                    </div>
                                </>
                            )}
                            
                            {page === "kip" && (
                                <>
                                    <div className="rounded-3xl p-8 border glass"
                                         style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <div className="flex items-center justify-between mb-6">
                                            <div className="text-xl font-semibold">Treasury</div>
                                            <button onClick={() => setShowTreasury(true)}
                                                    className="px-3 py-2 rounded-xl text-sm border"
                                                    style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                                Expand
                                            </button>
                                        </div>
                                        <div className="grid grid-cols-3 gap-4 mb-4">
                                            <div className="rounded-xl p-4 border"
                                                 style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                                <div className="text-xs" style={{ color: TXT_MUTED }}>Available</div>
                                                <div className="text-xl font-semibold">${treasury.balance}</div>
                                            </div>
                                            <div className="rounded-xl p-4 border"
                                                 style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                                <div className="text-xs" style={{ color: TXT_MUTED }}>Allocated</div>
                                                <div className="text-xl font-semibold">${treasury.allocated}</div>
                                            </div>
                                            <div className="rounded-xl p-4 border"
                                                 style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                                <div className="text-xs" style={{ color: TXT_MUTED }}>P&L (wk)</div>
                                                <div className="text-xl font-semibold text-emerald-300">+${treasury.weekPnL}</div>
                                            </div>
                                        </div>
                                        <div className="text-sm font-medium mb-2" style={{ color: TXT_MUTED }}>
                                            Recent transactions
                                        </div>
                                        <ul className="space-y-2">
                                            {treasury.tx.slice(0, 2).map(t => (
                                                <li key={t.id} className="flex items-center justify-between px-3 py-2 rounded-xl border"
                                                    style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                                    <span className="text-sm">{t.ts} • {t.label}</span>
                                                    <span className={`text-sm ${t.amount >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                                        {t.amount >= 0 ? "+$" + t.amount : "-$" + Math.abs(t.amount)}
                                                    </span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                    <div className="rounded-3xl p-8 border glass"
                                         style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <div className="text-xl font-semibold mb-3">Scheduling</div>
                                        <div className="text-sm" style={{ color: TXT_MUTED }}>
                                            Auto-assign windows • Resource matrix
                                        </div>
                                    </div>
                                </>
                            )}
                            
                            {page === "pheromind" && (
                                <>
                                    <div className="rounded-3xl p-8 border glass"
                                         style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <div className="text-xl font-semibold mb-3">Emergent Insights</div>
                                        <ul className="space-y-2 text-sm">
                                            <li className="p-2 rounded-lg" style={{ background: GLASS.subtle }}>
                                                AI regulation ↔ European markets (87%)
                                            </li>
                                            <li className="p-2 rounded-lg" style={{ background: GLASS.subtle }}>
                                                Bitcoin → Inflation → Gold (73%)
                                            </li>
                                        </ul>
                                    </div>
                                    <div className="rounded-3xl p-8 border glass"
                                         style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        <div className="text-xl font-semibold mb-3">Export / Consolidation</div>
                                        <div className="text-sm" style={{ color: TXT_MUTED }}>
                                            Export to project brief • Consolidate concepts
                                        </div>
                                    </div>
                                </>
                            )}
                            
                            {page === "calendar" && (
                                <div className="rounded-3xl p-8 border glass"
                                     style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                    <div className="text-xl font-semibold mb-3">Mission Brief</div>
                                    <div className="text-sm" style={{ color: TXT_MUTED }}>
                                        Objectives • Success metrics • Dependencies
                                    </div>
                                </div>
                            )}
                            
                            {page === "projects" && (
                                <div className="rounded-3xl p-8 border glass"
                                     style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                    <div className="text-xl font-semibold mb-3">Project Settings</div>
                                    <div className="text-sm" style={{ color: TXT_MUTED }}>
                                        Allocation • Permissions • Related operations
                                    </div>
                                </div>
                            )}
                            
                            {page === "system" && (
                                <div className="rounded-3xl p-8 border glass"
                                     style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                    <div className="text-xl font-semibold mb-3">Diagnostics</div>
                                    <div className="space-y-2 text-sm">
                                        <div className="flex justify-between">
                                            <span style={{ color: TXT_MUTED }}>TigerGraph</span>
                                            <span className="text-emerald-400">98% uptime</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span style={{ color: TXT_MUTED }}>Cloud APIs</span>
                                            <span className="text-amber-400">94% uptime</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span style={{ color: TXT_MUTED }}>Tailscale</span>
                                            <span className="text-emerald-400">Connected</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </aside>
                </div>

                {/* Settings Modal */}
                {showSettings && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center"
                         style={{ background: "rgba(0,0,0,0.7)" }}
                         onClick={() => setShowSettings(false)}>
                        <div className="w-[600px] rounded-3xl p-12 border glass"
                             style={{ background: BG, borderColor: GLASS.border }}
                             onClick={(e) => e.stopPropagation()}>
                            <div className="text-2xl font-semibold mb-8">Settings</div>
                            <div className="space-y-8">
                                <section>
                                    <div className="text-lg font-medium mb-3">Operational Mode</div>
                                    <div className="flex gap-3">
                                        {["MANUAL", "SUPERVISED", "AUTONOMOUS"].map(m => (
                                            <button key={m}
                                                    onClick={() => setMode(m)}
                                                    className="px-5 py-3 rounded-2xl text-base font-medium border flex-1"
                                                    style={{ 
                                                        background: mode === m ? "rgba(124,92,246,0.25)" : GLASS.bg,
                                                        borderColor: GLASS.border
                                                    }}>
                                                {m}
                                            </button>
                                        ))}
                                    </div>
                                </section>
                                <section>
                                    <div className="text-lg font-medium mb-3">Supervised Rules</div>
                                    <div className="space-y-3">
                                        <label className="flex items-center justify-between p-4 rounded-xl border"
                                               style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                            <span>Auto-approve actions under $50</span>
                                            <input type="checkbox" defaultChecked />
                                        </label>
                                        <label className="flex items-center justify-between p-4 rounded-xl border"
                                               style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                            <span>Flag content-risk replies</span>
                                            <input type="checkbox" defaultChecked />
                                        </label>
                                    </div>
                                </section>
                                <button onClick={() => setShowSettings(false)}
                                        className="w-full px-6 py-3 rounded-2xl text-lg font-medium border"
                                        style={{ background: ACCENT, borderColor: GLASS.border }}>
                                    Done
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Fullscreen Modals */}
                {showTreasury && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center"
                         style={{ background: "rgba(0,0,0,0.7)" }}
                         onClick={() => setShowTreasury(false)}>
                        <div className="w-[1200px] h-[700px] rounded-3xl p-12 border glass"
                             style={{ background: BG, borderColor: GLASS.border }}
                             onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-between mb-8">
                                <div className="text-2xl font-semibold">Treasury — Detail</div>
                                <button onClick={() => setShowTreasury(false)}
                                        className="px-4 py-2 rounded-xl border"
                                        style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                    Close
                                </button>
                            </div>
                            <div className="grid grid-cols-3 gap-8">
                                <div className="rounded-2xl p-6 border"
                                     style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                    <div className="text-sm mb-2" style={{ color: TXT_MUTED }}>Available</div>
                                    <div className="text-3xl font-semibold">${treasury.balance}</div>
                                </div>
                                <div className="rounded-2xl p-6 border"
                                     style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                    <div className="text-sm mb-2" style={{ color: TXT_MUTED }}>Allocated</div>
                                    <div className="text-3xl font-semibold">${treasury.allocated}</div>
                                </div>
                                <div className="rounded-2xl p-6 border"
                                     style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                    <div className="text-sm mb-2" style={{ color: TXT_MUTED }}>Net P&L (week)</div>
                                    <div className="text-3xl font-semibold text-emerald-300">+${treasury.weekPnL}</div>
                                </div>
                            </div>
                            <div className="mt-8 rounded-2xl p-6 border"
                                 style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                <div className="text-lg font-medium mb-4">All Transactions</div>
                                <ul className="space-y-3">
                                    {treasury.tx.map(t => (
                                        <li key={t.id} className="flex items-center justify-between px-4 py-3 rounded-xl border"
                                            style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                            <span>{t.ts} • {t.label}</span>
                                            <span className={t.amount >= 0 ? "text-emerald-300" : "text-rose-300"}>
                                                {t.amount >= 0 ? "+$" + t.amount : "-$" + Math.abs(t.amount)}
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                )}

                {showAgents && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center"
                         style={{ background: "rgba(0,0,0,0.7)" }}
                         onClick={() => setShowAgents(false)}>
                        <div className="w-[1200px] h-[700px] rounded-3xl p-12 border glass overflow-auto"
                             style={{ background: BG, borderColor: GLASS.border }}
                             onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-between mb-8">
                                <div className="text-2xl font-semibold">KIP Agents — Detail</div>
                                <button onClick={() => setShowAgents(false)}
                                        className="px-4 py-2 rounded-xl border"
                                        style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                    Close
                                </button>
                            </div>
                            <div className="grid grid-cols-3 gap-6">
                                {agents.map(a => (
                                    <div key={a.id} className="rounded-2xl p-6 border"
                                         style={{ background: GLASS.subtle, borderColor: GLASS.border }}>
                                        <div className="flex items-center justify-between mb-4">
                                            <div>
                                                <div className="text-lg font-medium">{a.name}</div>
                                                <div className="text-sm" style={{ color: TXT_MUTED }}>{a.role}</div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-sm" style={{ color: TXT_MUTED }}>Net P&L</div>
                                                <div className={`text-2xl font-semibold ${a.net >= 0 ? "text-emerald-300" : "text-rose-300"}`}>
                                                    ${Math.abs(a.net)}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="space-y-2 text-sm">
                                            <div className="flex justify-between">
                                                <span style={{ color: TXT_MUTED }}>Revenue</span>
                                                <span className="text-emerald-300">${a.revenue}</span>
                                            </div>
                                            <div className="flex justify-between">
                                                <span style={{ color: TXT_MUTED }}>Spending</span>
                                                <span className="text-rose-300">${a.spend}</span>
                                            </div>
                                        </div>
                                        <div className="mt-4 pt-4 border-t" style={{ borderColor: GLASS.border }}>
                                            <div className="text-xs" style={{ color: TXT_MUTED }}>Recent Actions</div>
                                            <div className="mt-2 space-y-1 text-xs">
                                                <div>Purchased data API (-$12)</div>
                                                <div>Completed report (+$150)</div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {showPheromind && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center"
                         style={{ background: "rgba(0,0,0,0.7)" }}
                         onClick={() => setShowPheromind(false)}>
                        <div className="w-[1200px] h-[700px] rounded-3xl p-12 border glass"
                             style={{ background: BG, borderColor: GLASS.border }}
                             onClick={(e) => e.stopPropagation()}>
                            <div className="flex items-center justify-between mb-8">
                                <div className="text-2xl font-semibold">Pheromind — Concept Trails</div>
                                <button onClick={() => setShowPheromind(false)}
                                        className="px-4 py-2 rounded-xl border"
                                        style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                    Close
                                </button>
                            </div>
                            <div className="rounded-2xl overflow-hidden"
                                 style={{ background: "rgba(255,255,255,0.06)" }}>
                                <svg viewBox="0 0 1200 500" className="w-full h-[400px]">
                                    {edges.map((e, i) => {
                                        const pos = (s) => s.split("").reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 0);
                                        const A = { x: 120 + (pos(e.a) % 800), y: 80 + ((pos(e.a) >> 5) % 340) };
                                        const B = { x: 120 + (pos(e.b) % 800), y: 80 + ((pos(e.b) >> 5) % 340) };
                                        return (
                                            <g key={i}>
                                                <defs>
                                                    <linearGradient id={`g${i}`} x1="0" y1="0" x2="1" y2="1">
                                                        <stop offset="0%" stopColor={PURPLE} />
                                                        <stop offset="100%" stopColor="#c084fc" />
                                                    </linearGradient>
                                                </defs>
                                                <line x1={A.x} y1={A.y} x2={B.x} y2={B.y} 
                                                      stroke={`url(#g${i})`} 
                                                      strokeWidth={Math.max(1.5, e.s * 8)} 
                                                      strokeOpacity={0.9} />
                                                <circle cx={A.x} cy={A.y} r={12} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
                                                <circle cx={B.x} cy={B.y} r={12} fill="#0f0e14" stroke="#a78bfa" strokeWidth={2} />
                                                <text x={A.x} y={A.y - 16} textAnchor="middle" fill="#fff" fontSize="12">{e.a}</text>
                                                <text x={B.x} y={B.y - 16} textAnchor="middle" fill="#fff" fontSize="12">{e.b}</text>
                                            </g>
                                        );
                                    })}
                                </svg>
                            </div>
                            <div className="mt-6 flex gap-3">
                                {edges.map((_, i) => (
                                    <button key={i} onClick={() => reinforce(i)}
                                            className="px-4 py-2 rounded-xl text-sm border"
                                            style={{ background: GLASS.bg, borderColor: GLASS.border }}>
                                        Reinforce #{i + 1}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    ReactDOM.render(<HACUnifiedUI />, document.getElementById('root'));
</script>
</body>
</html>
</artifact>
</artifacts>