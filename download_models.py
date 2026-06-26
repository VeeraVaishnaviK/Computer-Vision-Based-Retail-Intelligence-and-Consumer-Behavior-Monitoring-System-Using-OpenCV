"""
download_models.py
==================
Downloads the YOLOv4-tiny model files required for person detection.

Files downloaded:
    1. yolov4-tiny.cfg     — Network architecture (Darknet format)
    2. yolov4-tiny.weights — Pre-trained weights (~23 MB)
    3. coco.names          — COCO dataset class labels (80 classes)

All files are saved to the models/ directory.

Source: AlexeyAB/darknet GitHub repository (open-source, free).

Usage:
    python download_models.py
"""

import os
import sys
import urllib.request
import hashlib

# Project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")


def download_file(url, filepath, description=""):
    """
    Download a file from a URL with progress reporting.

    Args:
        url:         URL to download from.
        filepath:    Local path to save the file.
        description: Human-readable file description for progress messages.
    """
    filename = os.path.basename(filepath)

    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        print(f"  [SKIP] {filename} already exists ({file_size:,} bytes)")
        return

    print(f"  [DOWNLOADING] {filename} — {description}")
    print(f"  [URL] {url}")

    try:
        def progress_hook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                percent = min(100, downloaded * 100 / total_size)
                mb_down = downloaded / (1024 * 1024)
                mb_total = total_size / (1024 * 1024)
                sys.stdout.write(
                    f"\r  [PROGRESS] {percent:.1f}% "
                    f"({mb_down:.1f}/{mb_total:.1f} MB)"
                )
                sys.stdout.flush()

        urllib.request.urlretrieve(url, filepath, reporthook=progress_hook)
        print()  # New line after progress

        file_size = os.path.getsize(filepath)
        print(f"  [DONE] {filename} saved ({file_size:,} bytes)")

    except Exception as e:
        print(f"\n  [ERROR] Failed to download {filename}: {e}")
        print(f"  [INFO] You can manually download from: {url}")
        print(f"  [INFO] Save to: {filepath}")
        if os.path.exists(filepath):
            os.remove(filepath)


def create_coco_names(filepath):
    """
    Create the coco.names file with all 80 COCO class labels.

    The file contains one class name per line. The 'person' class
    is at index 0, which is what we filter for in the detector.

    Args:
        filepath: Path to save coco.names.
    """
    if os.path.exists(filepath):
        print(f"  [SKIP] coco.names already exists")
        return

    coco_classes = [
        "person", "bicycle", "car", "motorbike", "aeroplane",
        "bus", "train", "truck", "boat", "traffic light",
        "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow",
        "elephant", "bear", "zebra", "giraffe", "backpack",
        "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat",
        "baseball glove", "skateboard", "surfboard", "tennis racket",
        "bottle", "wine glass", "cup", "fork", "knife",
        "spoon", "bowl", "banana", "apple", "sandwich",
        "orange", "broccoli", "carrot", "hot dog", "pizza",
        "donut", "cake", "chair", "sofa", "pottedplant",
        "bed", "diningtable", "toilet", "tvmonitor", "laptop",
        "mouse", "remote", "keyboard", "cell phone", "microwave",
        "oven", "toaster", "sink", "refrigerator", "book",
        "clock", "vase", "scissors", "teddy bear", "hair drier",
        "toothbrush",
    ]

    with open(filepath, "w", encoding="utf-8") as f:
        for cls in coco_classes:
            f.write(cls + "\n")

    print(f"  [DONE] coco.names created ({len(coco_classes)} classes)")


def main():
    """Download all required model files."""
    print("=" * 60)
    print("  RETAIL INTELLIGENCE — Model Downloader")
    print("=" * 60)
    print()

    # Ensure models directory exists
    os.makedirs(MODELS_DIR, exist_ok=True)
    print(f"[INFO] Models directory: {MODELS_DIR}")
    print()

    # File 1: YOLOv4-tiny config
    print("[1/3] YOLOv4-tiny Configuration")
    download_file(
        url="https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg",
        filepath=os.path.join(MODELS_DIR, "yolov4-tiny.cfg"),
        description="Network architecture definition (~3 KB)",
    )
    print()

    # File 2: YOLOv4-tiny weights
    print("[2/3] YOLOv4-tiny Weights")
    download_file(
        url="https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4-tiny.weights",
        filepath=os.path.join(MODELS_DIR, "yolov4-tiny.weights"),
        description="Pre-trained weights (~23 MB)",
    )
    print()

    # File 3: COCO class names
    print("[3/3] COCO Class Names")
    create_coco_names(os.path.join(MODELS_DIR, "coco.names"))
    print()

    # Verify
    print("=" * 60)
    print("  VERIFICATION")
    print("=" * 60)
    all_good = True
    for fname in ["yolov4-tiny.cfg", "yolov4-tiny.weights", "coco.names"]:
        fpath = os.path.join(MODELS_DIR, fname)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print(f"  [OK] {fname} ({size:,} bytes)")
        else:
            print(f"  [MISSING] {fname}")
            all_good = False

    print()
    if all_good:
        print("  All model files are ready! You can now run main.py")
    else:
        print("  Some files are missing. Check errors above.")
        print("  You can also download manually from:")
        print("  https://github.com/AlexeyAB/darknet")

    print("=" * 60)


if __name__ == "__main__":
    main()
