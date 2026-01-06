"""Visual regression testing utilities."""

from io import BytesIO
from pathlib import Path
from typing import Tuple

from PIL import Image


class VisualRegression:
    """Visual regression testing utilities.

    Provides methods for comparing screenshots to baseline images
    with configurable thresholds.
    """

    def __init__(self, baseline_dir: Path):
        """Initialize visual regression helper.

        Args:
            baseline_dir: Directory to store baseline screenshots
        """
        self.baseline_dir = baseline_dir
        self.baseline_dir.mkdir(parents=True, exist_ok=True)

    def compare_screenshot(
        self,
        screenshot: bytes,
        baseline_name: str,
        threshold: float = 0.05,
        update_baseline: bool = False,
    ) -> Tuple[bool, float]:
        """Compare screenshot to baseline.

        Args:
            screenshot: Screenshot bytes from Playwright
            baseline_name: Name of the baseline file (relative path)
            threshold: Acceptable difference threshold (0.0-1.0)
            update_baseline: Whether to update baseline instead of comparing

        Returns:
            Tuple[bool, float]: (matches: bool, diff_percentage: float)

        Raises:
            FileNotFoundError: If baseline doesn't exist and not updating
        """
        baseline_path = self.baseline_dir / baseline_name

        # Update mode
        if update_baseline:
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            with open(baseline_path, "wb") as f:
                f.write(screenshot)
            return (True, 0.0)

        # Baseline doesn't exist
        if not baseline_path.exists():
            raise FileNotFoundError(f"Baseline not found: {baseline_path}")

        # Load images
        baseline_img = Image.open(baseline_path)
        current_img = Image.open(BytesIO(screenshot))

        # Simple pixel comparison
        if baseline_img.size != current_img.size:
            return (False, 1.0)

        # Convert to RGB and compare
        baseline_rgb = baseline_img.convert("RGB")
        current_rgb = current_img.convert("RGB")

        diff_pixels = 0
        total_pixels = baseline_rgb.width * baseline_rgb.height

        for x in range(baseline_rgb.width):
            for y in range(baseline_rgb.height):
                if baseline_rgb.getpixel((x, y)) != current_rgb.getpixel((x, y)):
                    diff_pixels += 1

        diff_percentage = diff_pixels / total_pixels if total_pixels > 0 else 0
        matches = diff_percentage <= threshold

        return (matches, diff_percentage)

    def get_baseline_path(self, baseline_name: str) -> Path:
        """Get full path to baseline file.

        Args:
            baseline_name: Relative path to baseline

        Returns:
            Path: Full path to baseline file
        """
        return self.baseline_dir / baseline_name

    def baseline_exists(self, baseline_name: str) -> bool:
        """Check if baseline exists.

        Args:
            baseline_name: Name of the baseline

        Returns:
            bool: True if baseline file exists
        """
        return self.get_baseline_path(baseline_name).exists()

    def delete_baseline(self, baseline_name: str) -> None:
        """Delete a baseline file.

        Args:
            baseline_name: Name of the baseline to delete
        """
        baseline_path = self.get_baseline_path(baseline_name)
        if baseline_path.exists():
            baseline_path.unlink()

    def list_baselines(self) -> list:
        """List all baseline files.

        Returns:
            list: List of baseline file paths
        """
        return list(self.baseline_dir.glob("**/*.png"))
