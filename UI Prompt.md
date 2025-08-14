You are an expert Svelte 5 + Tailwind CSS front-end engineer building the UI for a bleeding-edge Hybrid AI Council personal assistant. This is NOT a simple chatbot - it's a sophisticated cognitive architecture with Pheromind (subconscious memory), KIP agents (autonomous economic actors), and constitutional AI verification. The stack uses SvelteKit, TypeScript, and Tailwind CSS with real-time WebSocket streaming from FastAPI backend.

Design/Aesthetic Requirements (Critical):
Visual Inspiration: Linear.app's clean navigation + Notion's card layouts + Miro's interactive panels

Color Palette: Deep blue/purple cyberpunk aesthetic (accent: #232046, background: #15141c, text: #ffffff, secondary text: #a1a1aa)

Typography: Inter font family throughout, proper font weights (400, 500, 600)

Visual Style: Modern glassmorphic panels, subtle gradients, soft shadows (shadow-lg, shadow-xl), clean lines

Spacing: Rounded corners (8px minimum), generous whitespace, clear visual hierarchy

Interactions: Smooth hover/focus transitions, micro-animations, responsive feedback

Theme: Dark mode ONLY - no light mode toggle needed

Feel: Should feel like a "command center for AI consciousness" - sophisticated, powerful, visually striking

Layout Structure:
Persistent top nav: Clean, Linear.app style with system status indicators

Collapsible left sidebar: Notion-style navigation with conversation history

Main chat panel: Center focus with glassmorphic chat bubbles

Right dashboard panel: Miro-style widget panels (hidden on mobile)

Mobile responsive: Single sidebar, persistent top nav, main content

Core System Architecture:
Generator-Verifier AI: Local LLM generation + cloud constitutional verification

Pheromind Layer: Subconscious memory with pheromone trails and emergent insights

KIP Layer: Autonomous AI agents with individual budgets and P&L tracking

Three Operational Modes: Manual (full approval), Supervised (rule-based), Autonomous (full AI control)

Hybrid Infrastructure: Local TigerGraph + Redis, cloud FastAPI + Svelte on Fly.io

Detailed System Context for Realistic Preview:
KIP Agents (Knowledge-Incentive-Performance):

Semi-autonomous AI agents that perform real-world tasks with individual budgets

Each agent has specializations: StockAnalyst_Agent, MarketResearch_Agent, ContentCreation_Agent

They generate revenue through completed tasks and spend money on API calls/tools

Track P&L: Agent "Sarah" made $347 this week, spent $89 on data APIs, net profit +$258

Action examples: "StockAnalyst_Agent purchased $AAPL analysis from Bloomberg API (-$12)", "MarketResearch_Agent completed client report (+$150)"

Pheromind (Subconscious Memory System):

Works like ant pheromone trails - tracks patterns and connections between concepts

Creates "scent trails" between related ideas: "Bitcoin" → "Inflation" → "Gold" → "Safe Haven Assets"

Pheromones decay over time (12-second TTL) unless reinforced by repeated connections

Sample insights: "Strong trail detected: 'AI regulation' ↔ 'European markets' (confidence: 87%)", "Emerging pattern: 'Remote work' → 'Commercial real estate decline' (strength: 0.73)"

Visualize as connected nodes with varying line thickness showing trail strength

Operational Modes:

Manual: Every AI response needs human approval before execution (red indicator)

Supervised: Auto-approve actions under $50, require approval above (yellow indicator)

Autonomous: AI acts independently within constitutional guidelines (green indicator)

Sample Data for Realistic Feel:

Treasury balance: $2,847 available, $1,203 allocated to agents

Recent constitutional violations: 2 flagged this week (content policy, budget exceeded)

System health: Local TigerGraph (98% uptime), Cloud APIs (94% uptime), Tailscale VPN (connected)

Current conversation: "Help me analyze the crypto market for portfolio rebalancing"

Critical UI Components (Must Include All):
1. Operational Mode Control (Top Priority)
Prominent three-state toggle: Manual | Supervised | Autonomous (Linear.app style toggle)

Mode-specific approval interfaces with Notion-style card layouts

Visual indicators showing current operational mode with status colors

Settings panel for Supervised mode rules (glassmorphic modal overlay)

2. Main Chat Interface
Streaming token display with constitutional verification status badges

Chat bubbles: user (right, #232046 bg), AI (left, #1f1f23 bg) with proper contrast

Approval/rejection controls for Manual mode with cost indicators

Voice input/output controls (mic/speaker buttons) integrated into chat

Markdown support with proper syntax highlighting

3. KIP Economic Engine Dashboard (Right panel)
Agent P&L Panel: Notion-style cards with real-time profit/loss metrics

Treasury Overview: Central budget visualization with spending trends graph

Action Log: Live feed with timestamps, smooth scroll, Miro-style activity cards

Cost Tracking: Constitutional verification costs, API usage, clean data visualization

4. Pheromind Visualization (Dashboard section)
Subconscious Insights Panel: Interactive node graph or tag cloud visualization

Emergent Connections: Display strongest connections with connecting lines/trails

Memory Trails: Visual pheromone decay with opacity/size variations

Use force-directed graph or organic tag cloud layout

5. System Health & Monitoring (Top nav area)
Constitutional compliance scoring with color-coded indicators

Hybrid cloud connection status (green/yellow/red dots)

Agent performance metrics in compact, Linear.app style indicators

Technical Implementation:
SvelteKit + TypeScript + Tailwind CSS (no external UI libraries except for graph visualization if needed)

Responsive design with mobile-first approach

Real-time WebSocket integration stubs with // TODO comments

Custom Tailwind color variables for theme consistency

Proper TypeScript interfaces for all data structures

Accessible design (proper contrast, focus states, keyboard navigation)

Output Format:
Provide complete, production-ready Svelte components:

OperationalModeControl.svelte

ChatInterface.svelte

KIPDashboard.svelte

PheromindVisualization.svelte

SystemHealth.svelte

Sidebar.svelte

Layout.svelte (main app shell)

+layout.svelte (SvelteKit root layout)

TypeScript interfaces file (types.ts)

Tailwind config additions for custom colors

Visual Quality Requirements:

Every component should look "expensive" and professional

Consistent spacing using Tailwind spacing scale (4, 6, 8, 12, 16px)

Subtle animations on state changes (transition-all duration-200)

Proper loading states and error handling UI

Clean, readable code with consistent formatting

Make this the most visually impressive AI interface you've ever created - it should feel like controlling the future of AI consciousness while being intuitive and beautiful to use.

Interactive Preview Request:
After generating all the code components, please create a live interactive preview using ChatGPT Canvas. Open the main layout with working components so I can see exactly how the interface will look and function. Include realistic sample data for the KIP dashboard, sample pheromind connections, and demonstration of the operational mode switching. Make the preview fully interactive with clickable buttons, working toggles, and realistic data flows so I can experience the actual UI before implementing it in my codebase.