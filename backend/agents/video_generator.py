"""Agent 5 — Video Generator.
NOT an LLM agent — pure Python code.
Takes VideoScriptManifest + Figma screenshots → produces MP4 training video.
Uses: Pillow (image overlays), gTTS (text-to-speech), MoviePy (video stitching).
"""
import os
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
from moviepy import (
    ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
)
from models.schemas import VideoScriptManifest

OUTPUT_DIR = "output"
TEMP_DIR = "output/temp"
STEP_DURATION = 6  # seconds per step
FRAME_WIDTH = 1080
FRAME_HEIGHT = 1920  # phone aspect ratio


def _ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)


def _create_step_frame(step, screenshot_path: str | None, step_index: int) -> str:
    """Create a single frame image for one training step."""
    if screenshot_path and os.path.exists(screenshot_path):
        img = Image.open(screenshot_path).resize((FRAME_WIDTH, FRAME_HEIGHT))
    else:
        # Placeholder frame if no screenshot
        img = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), color=(30, 30, 50))

    draw = ImageDraw.Draw(img)

    # Try to load a font, fall back to default
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
        body_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except OSError:
        title_font = ImageFont.load_default()
        body_font = ImageFont.load_default()

    # Draw highlight ring if coordinates are available
    if step.highlight_coords:
        c = step.highlight_coords
        x, y, w, h = c.get("x", 0), c.get("y", 0), c.get("w", 200), c.get("h", 80)
        for i in range(4):
            draw.rounded_rectangle(
                [x - i, y - i, x + w + i, y + h + i],
                radius=12, outline=(255, 200, 0), width=3
            )

    # Draw instruction overlay at bottom
    overlay_y = FRAME_HEIGHT - 300
    draw.rectangle([0, overlay_y, FRAME_WIDTH, FRAME_HEIGHT], fill=(0, 0, 0, 200))
    draw.text((40, overlay_y + 20), f"Step {step.step_id}: {step.title}", fill="white", font=title_font)
    draw.text((40, overlay_y + 90), step.instruction, fill=(200, 200, 200), font=body_font)
    draw.text((40, overlay_y + 150), f"Action: {step.expected_action}", fill=(100, 255, 100), font=body_font)

    frame_path = os.path.join(TEMP_DIR, f"frame_{step_index:03d}.png")
    img.save(frame_path)
    return frame_path


def _generate_tts(text: str, filename: str) -> str:
    """Generate TTS audio file from narration text."""
    audio_path = os.path.join(TEMP_DIR, filename)
    tts = gTTS(text=text, lang="en", slow=False)
    tts.save(audio_path)
    return audio_path


def run(manifest: VideoScriptManifest, screenshots_dir: str = "screenshots") -> str:
    """Generate training video from manifest + screenshots.

    Args:
        manifest: The video script manifest from Agent 3
        screenshots_dir: Directory containing Figma screenshots named by screen id
                         e.g., screenshots/sku_search.png, screenshots/packaging_options.png

    Returns:
        Path to the generated MP4 file.
    """
    _ensure_dirs()
    clips = []

    for i, step in enumerate(manifest.steps):
        # Find screenshot for this step's screen
        screenshot_path = None
        for ext in [".png", ".jpg", ".jpeg"]:
            candidate = os.path.join(screenshots_dir, f"{step.screen}{ext}")
            if os.path.exists(candidate):
                screenshot_path = candidate
                break

        # Create the visual frame
        frame_path = _create_step_frame(step, screenshot_path, i)

        # Generate TTS narration
        audio_path = _generate_tts(step.narration, f"narration_{i:03d}.mp3")

        # Create video clip: image + audio
        audio_clip = AudioFileClip(audio_path)
        duration = max(STEP_DURATION, audio_clip.duration + 1)
        img_clip = ImageClip(frame_path, duration=duration)
        img_clip = img_clip.set_audio(audio_clip)
        clips.append(img_clip)

    # Stitch all clips together
    final = concatenate_videoclips(clips, method="compose")
    output_path = os.path.join(OUTPUT_DIR, f"{manifest.workflow_id}.mp4")
    final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")

    # Cleanup temp files
    for f in os.listdir(TEMP_DIR):
        os.remove(os.path.join(TEMP_DIR, f))

    return output_path
