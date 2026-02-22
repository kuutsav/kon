# Local Models

This document provides detailed information about running and configuring local models with Kon.

## Tested Models

| Model | Quantization | Context Length | GPU Offload | TPS | System Specs |
| ----- | -------------- | -------------- | ----------- | --- | ------------ |
| `qwen/qwen3-coder-next` | Q4_K_M | 200,000 | 17 | ~10-12 | i7-14700F × 28, 64GB RAM, 24GB VRAM (RTX 3090) |
| `zai-org/glm-4.7-flash` | Q4_K_M | 200,000 | 30 | ~15 | i7-14700F × 28, 64GB RAM, 24GB VRAM (RTX 3090) |

## Running with LM Studio

### qwen/qwen3-coder-next

```bash
kon --provider openai-responses \
  --base-url http://127.0.0.1:1234/v1 \
  --model qwen/qwen3-coder-next \
  --api-key ""
```

### zai-org/glm-4.7-flash

```bash
kon --provider openai-responses \
  --base-url http://127.0.0.1:1234/v1 \
  --model zai-org/glm-4.7-flash \
  --api-key ""
```

## Directly with llama.cpp

... (coming soon)
