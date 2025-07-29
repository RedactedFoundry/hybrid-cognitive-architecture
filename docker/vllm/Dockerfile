# Dockerfile for the vLLM service
# This is the final image. It uses the official vLLM image as a base.
# Models will be mounted at runtime via docker-compose, not copied during the build.
FROM vllm/vllm-openai:v0.6.3

# The command to start the vLLM server with Council + Pheromind architecture models.
CMD ["--model", "Qwen/Qwen3-14B-AWQ", "--served-model-name", "qwen3-council", "--model", "neuralmagic/DeepSeek-Coder-V2-Instruct-FP8", "--served-model-name", "deepseek-council", "--model", "solidrust/Mistral-7B-Instruct-v0.3-AWQ", "--served-model-name", "mistral-pheromind", "--host", "0.0.0.0"] 