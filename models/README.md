# Apollo 7 Model Files

## CLIP ViT-B/32 ONNX Models

Download the following ONNX models and place them in this directory:

### Visual Encoder
- **File:** `clip_vit_b32_visual.onnx`
- **Source:** [Qdrant/clip-ViT-B-32-vision](https://huggingface.co/Qdrant/clip-ViT-B-32-vision) or [immich-app/ViT-B-32__openai](https://huggingface.co/immich-app/ViT-B-32__openai)
- **Input:** (1, 3, 224, 224) float32
- **Output:** (1, 512) float32

### Text Encoder
- **File:** `clip_vit_b32_text.onnx`
- **Source:** Same repository as visual encoder (text encoder variant)
- **Input:** (N, 77) int32 token IDs
- **Output:** (N, 512) float32

### BPE Vocabulary
- **File:** `bpe_simple_vocab_16e6.txt.gz`
- **Source:** [OpenAI CLIP repository](https://github.com/openai/CLIP/blob/main/clip/bpe_simple_vocab_16e6.txt.gz)
- **Format:** Gzipped text file with BPE merge pairs

## Depth Anything V2
- **File:** `depth_anything_v2_vits.onnx` (already present)
