import argparse
from pathlib import Path

from freewili import FreeWili
from freewili.types import FileType, FreeWiliProcessorType

from src.game.audio import CANONICAL_SFX_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SOUND_FILES = sorted(path.name for path in CANONICAL_SFX_DIR.glob("*.wav"))

TEMP_AUDIO_FILES = {
    "tone.wav",
    "tts.wav",
    "test_tts.wav",
    "tts_a.wav",
    "tts_b.wav",
}


def log(message: str) -> None:
    print(f"[HW] {message}")


def list_directory(fw: FreeWili, directory: str) -> list:
    fw.change_directory(directory, processor=FreeWiliProcessorType.Display).expect(f"Failed to cd {directory}")
    return fw.list_current_directory(processor=FreeWiliProcessorType.Display).expect(f"Failed to list {directory}").contents


def audit_directory(fw: FreeWili, directory: str) -> None:
    log(f"Listing {directory}")
    for item in list_directory(fw, directory):
        if item.name in {".", ".."}:
            continue
        suffix = "/" if item.file_type == FileType.Directory else f" ({item.size} bytes)"
        print(f"  - {directory.rstrip('/')}/{item.name}{suffix}")


def purge_temp_audio(fw: FreeWili) -> None:
    log("Purging temporary audio files from /sounds")
    for item in list_directory(fw, "/sounds"):
        if item.file_type != FileType.File:
            continue
        if item.name in TEMP_AUDIO_FILES or item.name.startswith("s_"):
            log(f"  removing /sounds/{item.name}")
            fw.remove_directory_or_file(item.name, processor=FreeWiliProcessorType.Display).expect(
                f"Failed to remove {item.name}"
            )


def refresh_assets(fw: FreeWili) -> None:
    log("Refreshing canonical SFX assets into /sounds")
    for filename in CANONICAL_SOUND_FILES:
        local_path = CANONICAL_SFX_DIR / filename
        if not local_path.exists():
            log(f"  skipping missing local asset {local_path}")
            continue
        log(f"  uploading {filename}")
        fw.send_file(str(local_path), f"/sounds/{filename}", processor=FreeWiliProcessorType.Display).expect(
            f"Failed to upload {filename}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit and clean FREE-WILi display filesystem")
    parser.add_argument("--purge-temp-audio", action="store_true", help="Remove tone/tts scratch files from /sounds")
    parser.add_argument("--refresh-assets", action="store_true", help="Re-upload canonical SFX assets into /sounds")
    args = parser.parse_args()

    fw = None
    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found")
        fw.open().expect("Failed to open connection")
        log(f"Connected to {fw}")

        audit_directory(fw, "/")
        audit_directory(fw, "/sounds")
        audit_directory(fw, "/images")

        if args.purge_temp_audio:
            purge_temp_audio(fw)
            audit_directory(fw, "/sounds")

        if args.refresh_assets:
            refresh_assets(fw)
            audit_directory(fw, "/sounds")

    except Exception as exc:
        log(f"FATAL: {exc}")
    finally:
        if fw is not None:
            try:
                fw.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
