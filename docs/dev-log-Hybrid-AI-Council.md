Hybrid AI Council - Dev Notes
July 28, 2025 @ 3:30pm
Sprint 0: Project Kickoff & Environment Setup
STATUS: COMPLETED

Actions:

Installed core development tools: Docker Desktop, Python 3.11+, Git, and WSL 2.

Created a private GitHub repository (hybrid-cognitive-architecture) and cloned it locally.

Scaffolded the Python project by creating pyproject.toml and installing poetry.

Set up initial configuration management by creating a .env file and adding it to .gitignore.

Initialized the testing framework by creating the tests/ directory and writing a successful initial pytest sanity check.

Sprint 1: Local Foundation & Troubleshooting
STATUS: IN PROGRESS (Awaiting successful build)

Key Decisions & Actions:

Manual Model Download: Switched from in-build downloads to a manual download ("sideloading") strategy to bypass slow and unreliable Docker build downloads. Manually downloaded all three models (Qwen, DeepSeek, Mistral) to a local ./models directory.

Docker Authentication: Troubleshooted multiple 401 Unauthorized errors with Hugging Face. The final, successful solution was to pass the HUGGING_FACE_HUB_TOKEN from the .env file directly into the build process via docker-compose.yaml and log in with huggingface-cli login inside the Dockerfile.

Docker Data Relocation: Successfully moved the Docker WSL data from the C: drive to the D: drive using wsl --export and wsl --import to manage disk space.

Build Failure & Refactor: Encountered a critical build failure (lease does not exist: not found) and diagnosed that the "baking-in" models method was causing unsustainable disk usage (969 GB).

Architectural Pivot: Based on the build failure and Grok's recommendation, we pivoted to a runtime volume mounting strategy. This involved a major refactor:

The Dockerfile was simplified to remove all COPY commands for models.

The docker-compose.yaml was updated to mount the local ./models subdirectories directly into the vllm container.

System Cleanup: Performed a full reset of Docker Desktop data by unregistering the WSL distributions to reclaim disk space from the bloated virtual disk.

Current Status:

A new build is currently running using the superior runtime mounting method.

The next step is to verify the successful build and then run the test_connections.py script to officially complete Sprint 1.


July 28, 2025 @ 11:21pm
Sprint 1: Local Foundation & Troubleshooting
STATUS: COMPLETED

Key Decisions & Actions:

Manual Model Download: Successfully downloaded all three models (Qwen, DeepSeek, Mistral) to a local ./models directory to bypass slow in-build Docker downloads.

Docker Build Failure & Refactor: Encountered a critical build failure (lease does not exist: not found) and diagnosed that the "baking-in" models method caused unsustainable disk usage (969 GB).

Architectural Pivot: Based on the build failure and external analysis, we pivoted to a runtime volume mounting strategy. This was a major refactor:

The Dockerfile was simplified to remove all COPY commands for models.

The docker-compose.yaml was updated to mount the local ./models subdirectories directly into the vllm container.

TigerGraph Stability Fix: After multiple failed startup attempts with the standard and -dev images, the root cause was identified as a license check blocking gsql.

Switched the service to use the official TigerGraph Community Edition, which requires no license.

Removed TigerGraph from docker-compose.yaml and implemented a manual, scripted setup (setup-tigergraph.ps1) for a more stable and reliable initialization.

WSL Resource Allocation: Created a .wslconfig file to allocate significantly more resources (32GB RAM, 12 CPUs) to the Docker engine to ensure stability for heavy services like TigerGraph.

Dependency & Code Fixes: Resolved multiple FAILED tests by adding pyTigerGraph to the pyproject.toml dependencies and fixing a decode error in the redis_client.py script.

Final Status:

All Sprint 1 verification tests passed successfully (6/6 tests passed).

The local development environment is stable, configured, and fully operational.

Sprint 2: The Local Conscious Mind
STATUS: STARTED

Current Goal: Begin building the core application logic, starting with the configuration and main application files.

