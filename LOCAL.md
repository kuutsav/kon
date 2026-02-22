# Local Models

This document provides detailed information about running and configuring local models with Kon.

## Tested Models

| Model | Quantization | Context Length | GPU Offload | TPS | System Specs |
| ----- | -------------- | -------------- | ----------- | --- | ------------ |
| `qwen/qwen3-coder-next` | Q4_K_M | 200,000 | 17 | ~10-12 | i7-14700F × 28, 64GB RAM, 24GB VRAM (RTX 3090) |
| `zai-org/glm-4.7-flash` | Q4_K_M | 200,000 | 30 | ~80-90 | i7-14700F × 28, 64GB RAM, 24GB VRAM (RTX 3090) |

### qwen/qwen3-coder-next

Run a local model using llama-server with the following command:

```bash
./llama-server -m <models-dir>/GLM-4.7-Flash-GGUF/GLM-4.7-Flash-Q4_K_M.gguf -n 8192 -c 64000
```

Then start kon:

```bash
kon --model zai-org/glm-4.7-flash --provider openai --base-url http://localhost:8080/v1 --api-key ""
```
