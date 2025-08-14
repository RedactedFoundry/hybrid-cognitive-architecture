#!/usr/bin/env python3
"""
Start llama.cpp servers for both HuiHui OSS20B and Mistral 7B models.
"""

import subprocess
import time
import signal
import sys
import os
from pathlib import Path
import structlog

from pathlib import Path
import sys

# Import llama_cpp_models safely despite root-level config.py module shadowing the package
# We import the module directly from the config/ directory to avoid the name collision
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
if str(CONFIG_DIR) not in sys.path:
    sys.path.insert(0, str(CONFIG_DIR))

import llama_cpp_models as llama_cfg  # type: ignore

logger = structlog.get_logger(__name__)

class LlamaCppServerManager:
    """Manages multiple llama.cpp server instances."""
    
    def __init__(self):
        self.processes = {}
        self.should_stop = False
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal, stopping servers...")
        self.should_stop = True
        self.stop_all_servers()
        sys.exit(0)
    
    def _resolve_llama_server_binary(self) -> str:
        """Resolve the llama.cpp server executable path.

        Order of resolution:
        1) Environment variable LLAMA_SERVER_BIN (absolute path or command in PATH)
        2) "llama-server" / "llama-server.exe" if discoverable in PATH
        3) Common local build paths (D:/llama.cpp/llama-server.exe)
        """
        import shutil
        # 1) Env var override
        env_path = os.getenv("LLAMA_SERVER_BIN")
        if env_path:
            # If absolute path exists, return it; otherwise allow PATH lookup
            p = Path(env_path)
            if p.exists():
                return str(p)
            which = shutil.which(env_path)
            if which:
                return which
        # 2) PATH candidates
        for candidate in ("llama-server", "llama-server.exe", "server", "server.exe"):
            which = shutil.which(candidate)
            if which:
                return which
        # 3) Common local build path
        common = Path("D:/llama.cpp/llama-server.exe")
        if common.exists():
            return str(common)
        # As a last resort return the default name (will fail loudly)
        return "llama-server"

    def start_server(self, model_name: str, config: dict) -> bool:
        """Start a llama.cpp server for a specific model."""
        model_path = config["file_path"]
        port = config["port"]
        
        if not model_path.exists():
            logger.error(f"Model file not found: {model_path}")
            return False
        
        # Check if port is already in use
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
        except OSError:
            logger.warning(f"Port {port} already in use for {model_name}")
            return False
        
        # Build llama.cpp server command
        server_bin = self._resolve_llama_server_binary()
        host = str(config.get("host", "127.0.0.1"))
        cmd = [
            server_bin,
            "--model", str(model_path),
            "--port", str(port),
            "--host", host,
            "--ctx-size", str(config.get("context_size", 4096)),
            "--batch-size", str(config.get("batch_size", 512)),
            "--threads", str(config.get("threads", 8)),
            "--n-gpu-layers", str(config.get("gpu_layers", 32)),
            "--log-disable",  # Reduce noise
        ]
        
        logger.info(f"Starting {model_name} on port {port}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.getcwd()
            )
            
            self.processes[model_name] = {
                "process": process,
                "port": port,
                "config": config
            }
            
            logger.info(f"✅ {model_name} server started (PID: {process.pid}, Port: {port})")
            return True
            
        except FileNotFoundError:
            logger.error("llama-server executable not found! Please install llama.cpp with server support")
            return False
        except Exception as e:
            logger.error(f"Failed to start {model_name} server: {e}")
            return False
    
    def stop_server(self, model_name: str):
        """Stop a specific llama.cpp server."""
        if model_name in self.processes:
            process_info = self.processes[model_name]
            process = process_info["process"]
            
            logger.info(f"Stopping {model_name} server...")
            process.terminate()
            
            try:
                process.wait(timeout=10)
                logger.info(f"✅ {model_name} server stopped")
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing {model_name} server...")
                process.kill()
                process.wait()
            
            del self.processes[model_name]
    
    def stop_all_servers(self):
        """Stop all running servers."""
        for model_name in list(self.processes.keys()):
            self.stop_server(model_name)
    
    def wait_for_server_ready(self, model_name: str, timeout: int = 60) -> bool:
        """Wait for a server to be ready to accept requests."""
        if model_name not in self.processes:
            return False
        
        port = self.processes[model_name]["port"]
        
        import socket
        import time
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('127.0.0.1', port))
                    if result == 0:
                        logger.info(f"✅ {model_name} server is ready on port {port}")
                        return True
            except Exception:
                pass
            
            time.sleep(2)
        
        logger.error(f"❌ {model_name} server failed to become ready within {timeout} seconds")
        return False
    
    def start_all_servers(self) -> bool:
        """Start all configured llama.cpp servers."""
        logger.info("🚀 Starting llama.cpp servers...")
        
        # Validate model files first
        validation_results = llama_cfg.validate_model_files()
        missing_models = [model for model, exists in validation_results.items() if not exists]
        
        if missing_models:
            logger.error(f"Missing model files: {missing_models}")
            logger.error("Please ensure all models are in D:\\Council-Project\\models\\llama-cpp\\")
            return False
        
        success_count = 0
        for model_name, config in llama_cfg.LLAMACPP_MODELS.items():
            if self.start_server(model_name, config):
                success_count += 1
        
        if success_count == 0:
            logger.error("❌ Failed to start any llama.cpp servers")
            return False
        
        # Wait for all servers to be ready
        logger.info("⏳ Waiting for servers to be ready...")
        ready_count = 0
        for model_name in self.processes:
            if self.wait_for_server_ready(model_name):
                ready_count += 1
        
        if ready_count == len(self.processes):
            logger.info(f"🎉 All {ready_count} llama.cpp servers are ready!")
            return True
        else:
            logger.error(f"❌ Only {ready_count}/{len(self.processes)} servers became ready")
            return False
    
    def monitor_servers(self):
        """Monitor running servers and restart if needed."""
        logger.info("👀 Monitoring llama.cpp servers...")
        
        while not self.should_stop:
            # Check if any processes have died
            dead_servers = []
            for model_name, process_info in self.processes.items():
                process = process_info["process"]
                if process.poll() is not None:
                    logger.warning(f"❌ {model_name} server died, restarting...")
                    dead_servers.append(model_name)
            
            # Restart dead servers
            for model_name in dead_servers:
                config = self.processes[model_name]["config"]
                del self.processes[model_name]
                self.start_server(model_name, config)
                self.wait_for_server_ready(model_name)
            
            time.sleep(10)

def main():
    """Main entry point."""
    manager = LlamaCppServerManager()
    
    # Set up signal handlers for clean shutdown
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    if not manager.start_all_servers():
        sys.exit(1)
    
    try:
        # Monitor servers until shutdown
        manager.monitor_servers()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    finally:
        manager.stop_all_servers()

if __name__ == "__main__":
    main()
