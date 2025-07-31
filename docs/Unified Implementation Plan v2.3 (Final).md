# **Unified Implementation Plan v2.3 (Final)**

**Objective:** This is the single, unified, and final source of truth for building the Hybrid AI Council MVP. It integrates our validated v2.2 framework with the critical, production-hardening additions and project management best practices recommended by external AI reviews.

## **Part 1: Project Management & Methodology**

### **1.1 Our Guiding Philosophy: Agile-Scrum Hybrid Model**

* **Sprints:** We will work in distinct Sprints, each with a clear goal.  
* **Project Board:** You will manage your work on your Notion project board with **To Do**, **In Progress**, and **Done** columns.

### **1.2 Daily Development Cycle**

1. **Morning (15 min):** Review goals for the day.  
2. **Development (6-7 hrs):** Work on the current user story.  
3. **Testing (1 hr):** Write and run tests for today's code.  
4. **End of Day (30 min):** Update project board, commit code, review plan for tomorrow.

### **1.3 Quality Gates (End of Each Sprint)**

* All user stories for the current sprint are "Done."  
* Integration tests for the completed components are passing.  
* Code is committed to your Git repository.

## **Part 2: The "Staged Rollout" Plan to MVP**

This is our high-level roadmap, incorporating the safer, more methodical "Local First" strategy.

| Phase | Duration | Goal & Key Deliverables |
| :---- | :---- | :---- |
| **Sprint 0** | **2-3 Days** | **Project Kickoff & Environment Setup:** Prepare the development environment to prevent setup issues from derailing Sprint 1\. |
| **Sprint 1** | **Week 1** | **Local Foundation & Observability:** Establish core infrastructure, data backbone, and structured logging, all running locally. |
| **Sprint 2** | **Week 2** | **The Local Conscious Mind:** Build the core reasoning and orchestration loop with robust state management, all running locally. |
| **Sprint 3** | **Week 3** | **The Local Cognitive Engine:** Implement and test the Pheromind and KIP layers, all running locally. |
| **Sprint 4** | **Week 4** | **Cloud Migration & Persistence:** Move non-GPU services to Render and establish the secure network. |
| **Sprint 5** | **Week 5** | **Full System Integration & Hardening:** Connect all components, implement cost controls, and build in resilience. |
| **Sprint 6** | **Week 6** | **Interface & Final Validation:** Build the MVP UI and conduct end-to-end system and load testing. |

## **Part 3: Detailed Sprint Breakdown & Tactical Steps**

### **Sprint 0: Project Kickoff & Environment Setup (2-3 Days)**

* **Epic 1: Development Environment**  
  * **Story 1.1:** Install all required tools (Docker, Python 3.11+, Git).  
  * **Story 1.2:** Create the Git repository on GitHub.  
  * **Story 1.3:** Set up your Notion project board with columns for each sprint.  
* **Epic 2: Project Scaffolding**  
  * **Story 2.1:** Create the main project directory and initialize a Python project with a pyproject.toml file.  
  * **Story 2.2:** Set up the application to read configuration from environment variables and a .env file.  
  * **Story 2.3:** Set up pytest and write a single initial test to ensure the framework is configured correctly.

### **Sprint 1: Local Foundation & Observability (Week 1\)**

* **Epic 3: Observability Platform**  
  * **Story 3.1:** Structured Logging: Implement consistent, queryable JSON logging across all future components using structlog.  
* **Epic 4: Local Infrastructure Deployment**  
  * **Story 4.1:** Docker Compose Setup (vllm, tigervector, redis).  
  * **Story 4.2:** Custom vLLM Dockerfile (with model pre-loading).  
* **Epic 5: Local Memory Definition**  
  * **Story 5.1:** TigerVector Schema (schema.gsql).  
  * **Story 5.2:** Database Clients (tigervector\_client.py, redis\_client.py).

### **Sprint 2: The Local Conscious Mind (Week 2\)**

* **Epic 6: The Council Orchestrator**  
  * **Story 6.1:** Basic LangGraph State Machine (UserFacingOrchestrator class).  
  * **Story 6.2:** LLM Integration (call local vLLM service).  
* **Epic 7: State Management Infrastructure**  
  * **Story 7.1:** Request ID Implementation: Implement request ID generation in the WebSocket handler and pass it through the LangGraph state.  
* **Epic 8: The API Layer**  
  * **Story 8.1:** WebSocket Endpoint (/ws/chat).  
  * **Story 8.2:** Real-time Streaming (stream tokens from orchestrator).  
* **Epic 9: Health Checks**  
  * **Story 9.1:** Implement a /health endpoint in FastAPI to monitor service status.

### **Sprint 3: The Local Cognitive Engine (Week 3\)**

* **Epic 10: Pheromind Layer MVP**  
  * **Story 10.1:** Pheromone Class & Redis I/O (with 12s TTL).  
  * **Story 10.2:** Orchestrator Integration (query\_pheromind node).  
* **Epic 11: KIP Layer MVP**  
  * **Story 11.1:** KIP Agent & Genome (load from TigerVector).  
  * **Story 11.2:** Treasury Class (read/write budget in TigerVector).  
  * **Story 11.3:** Implement First Live Data Tool. The goal for this story will be to create a simple tool (e.g., one that fetches the current weather or a stock price) and integrate it into our first KIP agent.
* **Epic 12: Chaos Engineering**  
  * **Story 12.1:** Service Failure Testing: Write scripts to test graceful degradation when Redis or TigerVector is unavailable locally.

### **Sprint 4: Cloud Migration & Persistence (Week 4\)**

***Note: Plan for 1 buffer day this week for inevitable cloud deployment surprises.***

* **Epic 13: Cloud Service Deployment**  
  * **Story 13.1:** Deploy to Render (TigerVector, main application).  
  * **Story 13.2:** Provision Managed Redis on Render.  
  * **Story 13.3:** Update Configuration to use cloud addresses.  
* **Epic 14: Secure Networking**  
  * **Story 14.1:** Setup Tailscale on local rig and Render service.  
* **Epic 15: Distributed Tracing**  
  * **Story 15.1:** Instrument key operations with OpenTelemetry to trace requests across the cloud/local boundary.  
* **Epic 16: Rollback Plan**  
  * **Story 16.1:** Document the steps required to revert to a fully local configuration. Keep local config files in a separate, version-controlled file.

### **Sprint 5: Full System Integration & Hardening (Week 5\)**

***Note: This is a heavy sprint. Plan for 1.5 buffer days.***

* **Epic 17: Hybrid Connection**  
  * **Story 17.1:** Cloud-to-Local Call (over Tailscale).  
  * **Story 17.2:** Network Resilience (retry logic, timeouts).  
* **Epic 18: Governance MVP**  
  * **Story 18.1:** Operational Mode Switch (in TigerVector).  
* **Epic 19: Advanced State Management**  
  * **Story 19.1:** Distributed Locking: Implement Redis-based distributed locks for critical state-changing operations.  
* **Epic 20: Cost Management System**  
  * **Story 20.1:** Cost Tracking Infrastructure: Implement token counting and cost aggregation.  
  * **Story 20.2:** Budget Enforcement: Implement daily budget checks and automatic throttling.  
* **Epic 21: Advanced Economic Model**
    **Story 21.1: Internal Bounty System:** Implement a mechanism for the `UserFacingOrchestrator` to create and fund 'bounty' tasks from a central reserve. The quality of the agent's work on these non-revenue-generating tasks will be validated by the Council's GEDI voting module to determine if a bonus reward is warranted.
* **Epic 22: Core Logic Refinement & Optimization**
    **Story 22.1: Refactor Core Logic:** Refactor `main.py` and `core/orchestrator.py` to improve modularity and separation of concerns now that the full cognitive architecture is complete.
    **Story 22.2: Implement Smart Routing: I**mplement a triage/routing node in the orchestrator that can send simple queries to a faster, 2-phase response path, while sending complex queries to the full 3-phase deliberation path.
* **Epic 23: Advanced Chaos Engineering**
    **Story 23.1:** Network Partition Testing: Write scripts to verify system fallback behavior when the Tailscale connection is dropped.

### Sprint 6: Interface & Final Validation (Week 6\)

* **Epic 24: User Interface MVP**
    **Story 24.1:** Streamlit Dashboard (connect to WebSocket).
    **Story 24.2:** Real-time Response Streaming.
    **Story 24.3:** Approval UI (for Manual mode).
* **Epic 25: Advanced Cost Management**
    **Story 25.1:** Cost Dashboard: Add a real-time cost visibility tab to the Streamlit dashboard.
* **Epic 26: Final Validation**
    **Story 26.1:** Pre-Flight Checklist Execution.
* **Epic 27: Final Chaos Engineering**
    **Story 27.1:** Load Testing: Use locust to find performance breaking points of the final hybrid system.

### Sprint 7: Post MVP Improvements (Week 7)

* **Epic 28: KIP Agent Capability Expansion**
    **Story 28.1:** Create a `stock_tools.py` module and integrate it with a financial data API (e.g., Alpha Vantage) to give agents stock market analysis capabilities.
    **Story 28.2:** Create a `marketing_tools.py` module and integrate it with social media and ad platform APIs to give agents lead generation capabilities.