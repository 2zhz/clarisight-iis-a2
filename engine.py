"""
ClariSight Core Interaction Engine
----------------------------------
Implements the adaptive verbosity state machine, uncertainty & image-quality gate,
explanation ("Why?") generator, user correction log, and simulated sensor scenarios
for a wearable multimodal visual assistant.

Implementation boundaries:
- IMPLEMENTED: Adaptive verbosity tiers (Tier 0 Earcon / Tier 1 Concise / Tier 2 Detailed),
  confidence & image-quality uncertainty gate, mode switching (Navigation / Object Finding),
  barge-in interruption, rationale generation, and session correction tracking.
- SIMULATED: Object detection & depth estimates (structured scenario feeds), wearable camera
  and wrist haptic feedback (mirrored via browser UI/webcam metrics).
- PLANNED: On-device real-time object detection + depth estimation, BLE haptic wristband,
  cross-session user verbosity personalisation.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


CONFIDENCE_THRESHOLD = 0.65
MIN_BRIGHTNESS = 0.30
MIN_SHARPNESS = 0.35
URGENT_DISTANCE_M = 1.5


@dataclass
class DetectedObject:
    label: str
    distance_m: float
    clock_direction: str
    confidence: float
    hazard: bool = False
    dynamic: bool = False
    description: str = ""


@dataclass
class FrameInput:
    scenario_id: str
    scene_title: str
    brightness: float          # 0.0 (dark) to 1.0 (bright)
    sharpness: float           # 0.0 (blurry) to 1.0 (sharp)
    target_query: Optional[str]
    detections: List[DetectedObject]
    source: str = "simulated_vision_stream"  # or "live_webcam_metrics"


@dataclass
class SystemResponse:
    tier: int                  # 0 = Earcon only, 1 = Concise speech, 2 = Detailed speech
    earcon: str                # "none", "chime", "sonar", "urgent_double", "uncertainty_low"
    haptic_pattern: str        # "none", "soft_pulse", "strong_left", "strong_right", "warning_buzz"
    speech_text: str
    status: str                # "ok", "uncertain", "interrupted", "corrected"
    uncertainty_flag: bool
    confidence_shown: float
    explanation: str
    suppressed_count: int
    guidance_hint: Optional[str] = None
    can_correct: bool = True
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%H:%M:%S"))


SCENARIOS: Dict[str, Dict[str, Any]] = {
    "hallway_nav": {
        "id": "hallway_nav",
        "title": "Scenario 1: Indoor Corridor Navigation (Normal)",
        "summary": "Walking down an unfamiliar university corridor with one close obstacle and distant clutter.",
        "mode_default": "navigation",
        "brightness": 0.78,
        "sharpness": 0.86,
        "target_query": None,
        "detections": [
            {
                "label": "chair",
                "distance_m": 1.2,
                "clock_direction": "11 o'clock",
                "confidence": 0.91,
                "hazard": True,
                "dynamic": False,
                "description": "A wooden chair pulled slightly into the left walking lane."
            },
            {
                "label": "notice board",
                "distance_m": 3.4,
                "clock_direction": "2 o'clock",
                "confidence": 0.88,
                "hazard": False,
                "dynamic": False,
                "description": "Wall-mounted corridor notice board with paper flyers."
            },
            {
                "label": "potted plant",
                "distance_m": 4.1,
                "clock_direction": "1 o'clock",
                "confidence": 0.84,
                "hazard": False,
                "dynamic": False,
                "description": "Decorative plant placed beside the right-hand doorway."
            }
        ]
    },
    "low_light_failure": {
        "id": "low_light_failure",
        "title": "Scenario 2: Low-Light Blur Uncertainty (Failure & Recovery)",
        "summary": "Searching for a medicine bottle on a dim, cluttered counter while the camera moves.",
        "mode_default": "object_finding",
        "brightness": 0.21,
        "sharpness": 0.24,
        "target_query": "medicine bottle",
        "detections": [
            {
                "label": "water bottle",
                "distance_m": 0.6,
                "clock_direction": "2 o'clock",
                "confidence": 0.41,
                "hazard": False,
                "dynamic": False,
                "description": "Uncertain cylindrical object partially obscured by shadow."
            },
            {
                "label": "coffee mug",
                "distance_m": 0.8,
                "clock_direction": "10 o'clock",
                "confidence": 0.52,
                "hazard": False,
                "dynamic": False,
                "description": "Dark ceramic mug near the left edge of the frame."
            }
        ]
    },
    "low_light_recovered": {
        "id": "low_light_recovered",
        "title": "Scenario 2 (Recovered): Stabilised & Re-lit Counter",
        "summary": "After following the camera guidance hint, lighting and focus improve.",
        "mode_default": "object_finding",
        "brightness": 0.72,
        "sharpness": 0.85,
        "target_query": "medicine bottle",
        "detections": [
            {
                "label": "medicine bottle",
                "distance_m": 0.5,
                "clock_direction": "2 o'clock",
                "confidence": 0.92,
                "hazard": False,
                "dynamic": False,
                "description": "Small white prescription bottle with an orange cap."
            },
            {
                "label": "coffee mug",
                "distance_m": 0.8,
                "clock_direction": "10 o'clock",
                "confidence": 0.89,
                "hazard": False,
                "dynamic": False,
                "description": "Ceramic mug placed behind the bottle."
            }
        ]
    },
    "busy_kitchen": {
        "id": "busy_kitchen",
        "title": "Scenario 3: Cluttered Kitchen Search (Secondary / Hands-Busy User)",
        "summary": "Locating keys on a busy kitchen counter while a boiling kettle sits nearby.",
        "mode_default": "object_finding",
        "brightness": 0.81,
        "sharpness": 0.88,
        "target_query": "keys",
        "detections": [
            {
                "label": "kettle",
                "distance_m": 0.7,
                "clock_direction": "10 o'clock",
                "confidence": 0.94,
                "hazard": True,
                "dynamic": False,
                "description": "Hot electric kettle close to the user's left hand."
            },
            {
                "label": "keys",
                "distance_m": 0.9,
                "clock_direction": "1 o'clock",
                "confidence": 0.89,
                "hazard": False,
                "dynamic": False,
                "description": "Set of silver keys resting next to a chopping board."
            },
            {
                "label": "toaster",
                "distance_m": 1.3,
                "clock_direction": "12 o'clock",
                "confidence": 0.87,
                "hazard": False,
                "dynamic": False,
                "description": "Two-slice stainless steel toaster against the back wall."
            },
            {
                "label": "spice jar",
                "distance_m": 1.1,
                "clock_direction": "3 o'clock",
                "confidence": 0.83,
                "hazard": False,
                "dynamic": False,
                "description": "Small glass jar on the right edge."
            }
        ]
    }
}


class ClariSightEngine:
    """Stateful interaction engine enforcing adaptive verbosity and calibrated uncertainty."""

    def __init__(self) -> None:
        self.mode: str = "navigation"       # "navigation" or "object_finding"
        self.verbosity_preference: str = "adaptive"  # "adaptive", "minimal", "detailed"
        self.target_query: str = "medicine bottle"
        self.speaking_active: bool = False
        self.last_frame: Optional[FrameInput] = None
        self.last_response: Optional[SystemResponse] = None
        self.correction_log: List[Dict[str, Any]] = []
        self.event_log: List[Dict[str, Any]] = []
        self.confidence_threshold: float = CONFIDENCE_THRESHOLD

    def set_mode(self, mode: str, target_query: Optional[str] = None) -> Dict[str, Any]:
        if mode not in ("navigation", "object_finding"):
            raise ValueError(f"Unsupported mode: {mode}")
        self.mode = mode
        if target_query is not None and target_query.strip():
            self.target_query = target_query.strip().lower()
        self._log("mode_change", f"Switched mode to {self.mode}" + (f" (target: {self.target_query})" if self.mode == "object_finding" else ""))
        return self.get_state()

    def set_verbosity(self, level: str) -> Dict[str, Any]:
        if level not in ("adaptive", "minimal", "detailed"):
            raise ValueError(f"Unsupported verbosity level: {level}")
        self.verbosity_preference = level
        self._log("verbosity_change", f"Verbosity preference set to {level}")
        return self.get_state()

    def load_scenario(self, scenario_id: str, live_brightness: Optional[float] = None, live_sharpness: Optional[float] = None) -> SystemResponse:
        if scenario_id not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_id}")
        raw = SCENARIOS[scenario_id]
        detections = [DetectedObject(**d) for d in raw["detections"]]

        brightness = raw["brightness"] if live_brightness is None else max(0.0, min(1.0, float(live_brightness)))
        sharpness = raw["sharpness"] if live_sharpness is None else max(0.0, min(1.0, float(live_sharpness)))
        source = "live_webcam_metrics" if (live_brightness is not None or live_sharpness is not None) else "simulated_vision_stream"

        target = self.target_query if self.mode == "object_finding" else raw.get("target_query")
        if raw.get("target_query") and self.mode == "object_finding":
            # Keep user target if explicitly set, else adopt scenario target
            target = raw["target_query"]
            self.target_query = target

        frame = FrameInput(
            scenario_id=scenario_id,
            scene_title=raw["title"],
            brightness=brightness,
            sharpness=sharpness,
            target_query=target,
            detections=detections,
            source=source
        )
        return self.process_frame(frame, requested_detail=False)

    def process_frame(self, frame: FrameInput, requested_detail: bool = False) -> SystemResponse:
        self.last_frame = frame
        self.speaking_active = True

        # Step 1: Image-Quality Gate (Amershi G2 - Make clear how well the system can do)
        quality_issues = []
        if frame.brightness < MIN_BRIGHTNESS:
            quality_issues.append("low lighting")
        if frame.sharpness < MIN_SHARPNESS:
            quality_issues.append("motion blur")

        top_conf = max((d.confidence for d in frame.detections), default=0.0)

        if quality_issues or top_conf < self.confidence_threshold:
            issue_str = " and ".join(quality_issues) if quality_issues else "low visual confidence"
            top_guess = max(frame.detections, key=lambda d: d.confidence) if frame.detections else None
            guess_note = f" (weak match: {top_guess.label} at {int(top_guess.confidence * 100)}%)" if top_guess else ""
            hint = "Hold the camera steady, step closer, or improve lighting before acting."
            speech = f"Uncertain view due to {issue_str}. Confidence is {int(top_conf * 100)} percent. {hint}"
            explanation = (
                f"Uncertainty Gate triggered: brightness={frame.brightness:.2f} (min {MIN_BRIGHTNESS}), "
                f"sharpness={frame.sharpness:.2f} (min {MIN_SHARPNESS}), max confidence={top_conf:.2f} "
                f"(threshold {self.confidence_threshold}){guess_note}. Suppressed assertive guidance to prevent hallucination."
            )
            resp = SystemResponse(
                tier=1,
                earcon="uncertainty_low",
                haptic_pattern="warning_buzz",
                speech_text=speech,
                status="uncertain",
                uncertainty_flag=True,
                confidence_shown=round(top_conf, 2),
                explanation=explanation,
                suppressed_count=len(frame.detections),
                guidance_hint=hint,
                can_correct=True
            )
            self.last_response = resp
            self._log("uncertainty_gate", explanation)
            return resp

        # Step 2: Priority & Mode Filtering (Adaptive Verbosity / Selective Attention)
        if self.mode == "navigation":
            resp = self._handle_navigation(frame, requested_detail)
        else:
            resp = self._handle_object_finding(frame, requested_detail)

        self.last_response = resp
        self._log("guidance_output", f"Tier {resp.tier} [{resp.earcon}]: {resp.speech_text}")
        return resp

    def _handle_navigation(self, frame: FrameInput, requested_detail: bool) -> SystemResponse:
        urgent = [d for d in frame.detections if d.hazard or d.distance_m <= URGENT_DISTANCE_M]
        urgent.sort(key=lambda d: d.distance_m)
        non_urgent = [d for d in frame.detections if d not in urgent]

        if requested_detail or self.verbosity_preference == "detailed":
            parts = [f"{d.label} at {d.distance_m:.1f} metres, {d.clock_direction} ({d.description})" for d in frame.detections]
            speech = "Detailed scene: " + " ".join(parts)
            explanation = (
                f"User requested Tier 2 detailed scene description. Included all {len(frame.detections)} "
                f"detected items (confidence >= {self.confidence_threshold})."
            )
            return SystemResponse(
                tier=2,
                earcon="chime",
                haptic_pattern="soft_pulse",
                speech_text=speech,
                status="ok",
                uncertainty_flag=False,
                confidence_shown=round(max(d.confidence for d in frame.detections), 2),
                explanation=explanation,
                suppressed_count=0
            )

        if not urgent:
            # Tier 0: Earcon only to avoid auditory cognitive overload
            explanation = (
                f"No obstacles within {URGENT_DISTANCE_M}m. Delivered Tier 0 clear-path earcon only "
                f"and suppressed {len(non_urgent)} distant background objects to minimise auditory load."
            )
            return SystemResponse(
                tier=0,
                earcon="sonar",
                haptic_pattern="none",
                speech_text="Path clear (earcon only — press D for full scene).",
                status="ok",
                uncertainty_flag=False,
                confidence_shown=round(max((d.confidence for d in frame.detections), default=1.0), 2),
                explanation=explanation,
                suppressed_count=len(non_urgent)
            )

        primary = urgent[0]
        haptic = "strong_left" if any(h in primary.clock_direction for h in ("9", "10", "11")) else "strong_right"
        if self.verbosity_preference == "minimal":
            speech = f"{primary.label}, {primary.distance_m:.1f}m, {primary.clock_direction}."
        else:
            speech = f"{primary.label.capitalize()} ahead, {primary.distance_m:.1f} metres, {primary.clock_direction}."

        explanation = (
            f"Prioritised '{primary.label}' (hazard={primary.hazard}, distance={primary.distance_m}m, "
            f"conf={int(primary.confidence * 100)}%). Suppressed {len(non_urgent)} distant background "
            f"items to keep speech brief during movement."
        )
        return SystemResponse(
            tier=1,
            earcon="urgent_double",
            haptic_pattern=haptic,
            speech_text=speech,
            status="ok",
            uncertainty_flag=False,
            confidence_shown=round(primary.confidence, 2),
            explanation=explanation,
            suppressed_count=len(non_urgent)
        )

    def _handle_object_finding(self, frame: FrameInput, requested_detail: bool) -> SystemResponse:
        target = (frame.target_query or self.target_query or "").lower()
        matches = [d for d in frame.detections if target and target in d.label.lower()]
        hazards = [d for d in frame.detections if d.hazard and d not in matches and d.distance_m <= 1.0]

        if requested_detail or self.verbosity_preference == "detailed":
            parts = [f"{d.label} at {d.distance_m:.1f} metres, {d.clock_direction} ({d.description})" for d in frame.detections]
            speech = "Detailed workspace view: " + " ".join(parts)
            explanation = f"Tier 2 detailed view triggered in Object-Finding mode for target '{target}'."
            return SystemResponse(
                tier=2,
                earcon="chime",
                haptic_pattern="soft_pulse",
                speech_text=speech,
                status="ok",
                uncertainty_flag=False,
                confidence_shown=round(max((d.confidence for d in frame.detections), default=0.0), 2),
                explanation=explanation,
                suppressed_count=0
            )

        if matches:
            found = max(matches, key=lambda d: d.confidence)
            suppressed = len(frame.detections) - 1 - len(hazards)
            hazard_prefix = ""
            earcon = "chime"
            haptic = "soft_pulse"
            if hazards:
                h = hazards[0]
                hazard_prefix = f"Caution: {h.label} at {h.clock_direction}. "
                earcon = "urgent_double"
                haptic = "strong_left"
            speech = f"{hazard_prefix}Found {found.label}, {found.distance_m:.1f} metres, {found.clock_direction}."
            explanation = (
                f"Matched target '{found.label}' ({int(found.confidence * 100)}% confidence). "
                + (f"Added close-range safety warning for '{hazards[0].label}'. " if hazards else "")
                + f"Filtered out {max(0, suppressed)} unrelated background items."
            )
            return SystemResponse(
                tier=1,
                earcon=earcon,
                haptic_pattern=haptic,
                speech_text=speech,
                status="ok",
                uncertainty_flag=False,
                confidence_shown=round(found.confidence, 2),
                explanation=explanation,
                suppressed_count=max(0, suppressed)
            )

        # Target not found despite clear view
        hint = "Pan slowly left or right, or press D to hear all visible items."
        speech = f"'{target}' not visible in current frame. {hint}"
        explanation = f"High-confidence frame ({len(frame.detections)} items seen), but none matched target '{target}'."
        return SystemResponse(
            tier=1,
            earcon="sonar",
            haptic_pattern="none",
            speech_text=speech,
            status="ok",
            uncertainty_flag=False,
            confidence_shown=round(max((d.confidence for d in frame.detections), default=0.0), 2),
            explanation=explanation,
            suppressed_count=len(frame.detections),
            guidance_hint=hint
        )

    def request_detail(self) -> SystemResponse:
        if not self.last_frame:
            return self.load_scenario("hallway_nav")
        return self.process_frame(self.last_frame, requested_detail=True)

    def barge_in_interrupt(self) -> SystemResponse:
        self.speaking_active = False
        resp = SystemResponse(
            tier=0,
            earcon="none",
            haptic_pattern="none",
            speech_text="Speech interrupted by user (Barge-in).",
            status="interrupted",
            uncertainty_flag=False,
            confidence_shown=self.last_response.confidence_shown if self.last_response else 1.0,
            explanation="User triggered immediate barge-in (Spacebar). Active audio halted immediately to preserve user agency (Amershi G8).",
            suppressed_count=0
        )
        self.last_response = resp
        self._log("barge_in", "User halted active audio output via immediate barge-in.")
        return resp

    def report_correction(self, user_note: str = "Misidentified or unhelpful alert") -> SystemResponse:
        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "scenario_id": self.last_frame.scenario_id if self.last_frame else "none",
            "previous_speech": self.last_response.speech_text if self.last_response else "",
            "user_note": user_note
        }
        self.correction_log.append(entry)
        self._log("user_correction", f"User corrected output: {user_note}")
        resp = SystemResponse(
            tier=1,
            earcon="chime",
            haptic_pattern="soft_pulse",
            speech_text="Correction logged. Re-scan when ready or press D for full scene.",
            status="corrected",
            uncertainty_flag=False,
            confidence_shown=self.last_response.confidence_shown if self.last_response else 0.0,
            explanation=(
                f"Recorded user correction ('{user_note}'). Supports Amershi G9 (efficient correction); "
                f"in planned deployments, repeated corrections raise the local confidence threshold."
            ),
            suppressed_count=0,
            guidance_hint="Adjust camera angle or switch scenario to re-scan."
        )
        self.last_response = resp
        return resp

    def _log(self, event_type: str, detail: str) -> None:
        self.event_log.insert(0, {
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "event": event_type,
            "detail": detail
        })
        self.event_log = self.event_log[:30]

    def get_state(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "verbosity_preference": self.verbosity_preference,
            "target_query": self.target_query,
            "speaking_active": self.speaking_active,
            "confidence_threshold": self.confidence_threshold,
            "last_frame": asdict(self.last_frame) if self.last_frame else None,
            "last_response": asdict(self.last_response) if self.last_response else None,
            "corrections_count": len(self.correction_log),
            "correction_log": self.correction_log[-5:],
            "event_log": self.event_log[:12],
            "scenarios": [
                {"id": k, "title": v["title"], "summary": v["summary"], "mode_default": v["mode_default"]}
                for k, v in SCENARIOS.items()
            ]
        }
