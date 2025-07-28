# Dockerfile for the vLLM service
# Stage 1: Model Downloader
# This stage uses a base python image to download all required models from Hugging Face.
# This keeps the final vLLM image clean and only contains the necessary files.
FROM python:3.11-slim as downloader

# Install git and git-lfs to handle large model files
RUN apt-get update && apt-get install -y git git-lfs && git lfs install

# Set the cache directory for Hugging Face models
ENV HF_HOME=/root/.cache/huggingface
ENV TRANSFORMERS_CACHE=$HF_HOME

# Download our three core models for Council + Pheromind architecture.
# Council Models: Heavyweight reasoning and technical specialists (quantized for efficiency)
# Pheromind Model: Lightweight ambient pattern recognition (12s TTL processing)
RUN git clone https://huggingface.co/Qwen/Qwen3-14B-AWQ $HF_HOME/hub/models--Qwen--Qwen3-14B-AWQ
RUN git clone https://huggingface.co/neuralmagic/DeepSeek-Coder-V2-Instruct-FP8 $HF_HOME/hub/models--neuralmagic--DeepSeek-Coder-V2-Instruct-FP8
RUN git clone https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.3-AWQ $HF_HOME/hub/models--TheBloke--Mistral-7B-Instruct-v0.3-AWQ

# Stage 2: vLLM Runtime
# This is the final image. It uses the official vLLM image as a base.
FROM vllm/vllm-openai:latest

# Copy the pre-downloaded models from the downloader stage into the final image.
# This ensures the models are available without needing to download them on startup.
COPY --from=downloader /root/.cache/huggingface /root/.cache/huggingface

# The command to start the vLLM server with Council + Pheromind architecture models.
# Council Models: Heavy reasoning (qwen3-council) and technical expertise (deepseek-council) - quantized
# Pheromind Model: Fast ambient processing (mistral-pheromind) for 12-second TTL operations - quantized
# NOTE: This command is long and must be on a single line.
CMD ["--model", "Qwen/Qwen3-14B-AWQ", "--served-model-name", "qwen3-council", "--model", "neuralmagic/DeepSeek-Coder-V2-Instruct-FP8", "--served-model-name", "deepseek-council", "--model", "TheBloke/Mistral-7B-Instruct-v0.3-AWQ", "--served-model-name", "mistral-pheromind", "--host", "0.0.0.0"] 