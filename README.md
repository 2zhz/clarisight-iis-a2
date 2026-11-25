# ClariSight — Adaptive Multimodal Visual Assistant (A2 Prototype)

**README Prose Word Count:** 568 words (excluding code blocks and setup commands)  
**Module:** LH/LM Intelligent Interactive Systems (A2 Project)  
**Author:** Hongze Zuo  

## Project Status

ClariSight is a working local interactive prototype exploring adaptive verbosity, calibrated uncertainty, and eyes-free user control for an indoor AI visual assistant.

* **Implemented:** Adaptive verbosity state machine (Tier 0 earcon-only, Tier 1 concise cues, Tier 2 on-demand detailed scene), image-quality and confidence uncertainty gate (threshold 0.65), mode switching (Navigation and Object Finding), instant speech barge-in (`Space`), on-demand rationale (`R`), user correction logging (`C`), Web Audio earcons, browser TTS, optional live webcam brightness/sharpness sampling, and 7 automated unit tests.
* **Simulated:** Vision object detection and depth outputs (four reproducible indoor scenarios in `engine.py`), smart-glasses camera feed, and directional wrist haptic feedback (visual pulse indicator).
* **Planned:** On-device real-time object detection and depth estimation (e.g., YOLO + Depth Anything), Bluetooth wrist haptic actuator, and cross-session verbosity personalisation.

## Technology Stack

* **Backend (`engine.py`, `server.py`):** Python 3 standard library (`http.server`, `dataclasses`, `unittest`) with zero third-party packages and no external API keys required.
* **Frontend (`static/index.html`, `style.css`, `app.js`):** Vanilla HTML/CSS/JavaScript using the Web Audio API (earcons), Web Speech API (TTS and instant speech cancellation), and optional `getUserMedia` webcam luminance/edge-sharpness sampling.
* **Undecided Choices:** Final on-device vision-language model and wearable haptic hardware remain undecided pending latency and battery benchmarks.

## Running or Inspecting the Work

Requires Python 3.8+ and a modern desktop browser (Chrome or Edge recommended for Web Speech API).

```bash
# 1. Run all automated unit tests
python -m unittest discover -s tests -v

# 2. Start the local prototype server
python server.py