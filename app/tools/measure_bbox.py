"""Interactive helper to capture bounding boxes from template images."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2


def measure_bbox(image_path: str) -> None:
    """Display an image and print bounding boxes for drag selections."""
    img = cv2.imread(image_path)
    if img is None:
        print(f"Cannot read image: {image_path}")
        return

    clone = img.copy()
    ref_point: list[tuple[int, int]] = []

    def click_and_crop(event, x, y, _flags, _param):
        nonlocal ref_point, img
        if event == cv2.EVENT_LBUTTONDOWN:
            ref_point = [(x, y)]
        elif event == cv2.EVENT_LBUTTONUP:
            ref_point.append((x, y))
            cv2.rectangle(img, ref_point[0], ref_point[1], (0, 255, 0), 2)
            cv2.imshow("Measure BBox", img)

            x1, y1 = ref_point[0]
            x2, y2 = ref_point[1]
            x_min, x_max = sorted((x1, x2))
            y_min, y_max = sorted((y1, y2))
            width = x_max - x_min
            height = y_max - y_min

            print(f'"px": [{x_min}, {y_min}, {width}, {height}],')

    window_name = "Measure BBox"
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, click_and_crop)

    print("Instructions:")
    print("- Click and drag to draw a bounding box.")
    print("- Press 'r' to reset annotations.")
    print("- Press 'q' to quit.")

    while True:
        cv2.imshow(window_name, img)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("r"):
            img = clone.copy()
        elif key == ord("q"):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python app/tools/measure_bbox.py <image_path>")
        sys.exit(1)

    target = Path(sys.argv[1]).expanduser()
    measure_bbox(str(target))

