import json
import operator
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from aind_data_schema.core.quality_control import QCEvaluation, QCMetric, QCStatus, Stage
from aind_data_schema_models.modalities import Modality
from pydantic import BaseModel, Field
import math
from PIL import Image, ImageDraw, ImageFont


class EvaluationSettings(BaseModel):
    """Settings for the evaluation of the registration."""

    # Path to the reference image
    input_directory: Path = Field(..., description="Input directory containing the data")
    output_directory: Path = Field(
        ..., description="Output directory to store the results"
    )
    pattern: Optional[List] = Field(
        default=[], description="Pattern to match in file search"
    )
    folder_name: str = Field(..., description="Name of the folder to search for files")
    metric_name: str = Field(..., description="Name of the metric")
    metric_status_history: list[QCStatus] = Field(
        default=[], description="Status history for the metric"
    )
    stage: Stage = Field(..., description="Stage of the evaluation")
    modality: Modality.ONE_OF = Field(..., description="Modality of the data")
    evaluations_name: str = Field(..., description="Name of the evaluation")
    allow_failed_metrics: bool = Field(..., description="Allow failed metrics")


class Evaluation:
    """Build evaluation from provided settings."""

    OPERATORS = {
        "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
    }

    def __init__(self, settings: EvaluationSettings):
        self.settings = settings
        self.initalize_evaluation()

    def initalize_evaluation(self):
        """Initialize the evaluation."""
        self.directories = self._get_directories()
        self.output_directory = self._make_directory(self.settings.output_directory)

    def _get_directories(self) -> list:
        """Get directories containing the data.

        Returns
        -------
        list
            List of directories containing the data
        """
        input_dir = self.settings.input_directory
        if len(list(input_dir.glob("*"))) == 1:
            return [plane for plane in input_dir.glob("*/*")]
        return [plane for plane in input_dir.rglob("*")]

    def _make_directory(self, directory: Path) -> Path:
        """
        Make a directory if it does not exist.

        Parameters
        ----------
        directory : Path
            Directory path

        Returns
        -------
        Path
            Directory path
        """
        directory.mkdir(exist_ok=True)
        return directory

    def collect_pattern_files(self) -> tuple[List[str], List[Path]]:
        """Collect files matching the pattern in the directories.

        Parameters
        ----------
        pattern1 : str
            Pattern to match in file search
        pattern2 : Optional[str], optional
            Second pattern to match in file search, by default None

        Returns
        -------
        tuple[List[str], List[Path]]
            List of file paths matching the pattern
        """

        if not self.directories:
            raise ValueError("No directories provided.")
        if not self.settings.pattern:
            raise ValueError("No pattern provided.")

        row_labels: List[str] = []
        matched_files: List[Path] = []

        for directory in self.directories:
            for pattern in self.settings.pattern:
                pattern_matches = [
                    i for i in directory.rglob("*") if pattern in str(i) and i.is_file()
                ]
                if pattern_matches:
                    matched_files.extend(pattern_matches)
            row_labels.append(directory.parent.name)

        return row_labels, matched_files

    def combine_images(
        self,
        image_paths,
        image_output_name,
        num_columns=2,
        spacing=10,
        row_labels=None,
        label_width=200,
    ) -> Path:
        """
        Combine multiple PNG images into a matrix layout with row labels.

        Parameters
        ----------
        image_paths : List[str]
            List of paths to PNG images
        output_path : str
            Path where the combined image will be saved
        num_columns : int, optional
            Number of columns in the matrix, by default 2
        spacing : int, optional
            Pixels of spacing between images, by default 10
        row_labels : List[str], optional
            List of labels for each row. If None, no labels are added, by default None
        label_width : int, optional
            Width in pixels reserved for labels, by default 200

        Returns
        -------
        None
            Saves the combined image to output_path
        """
        images = [Image.open(path).convert("RGBA") for path in image_paths]

        num_images = len(images)
        num_rows = math.ceil(num_images / num_columns)

        widths, heights = zip(*(i.size for i in images))
        max_width = max(widths)
        max_height = max(heights)

        total_width = (max_width * num_columns) + (spacing * (num_columns - 1))
        if row_labels:
            total_width += label_width + spacing  # Add space for labels
        total_height = (max_height * num_rows) + (spacing * (num_rows - 1))

        new_image = Image.new("RGBA", (total_width, total_height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(new_image)

        try:
            if sys.platform == "win32":
                font_path = "C:/Windows/Fonts/arial.ttf"
            elif sys.platform == "darwin":  # macOS
                font_path = "/System/Library/Fonts/Helvetica.ttc"
            else:  # Linux
                font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

            font = ImageFont.truetype(font_path, size=100)
        except Exception:
            font = ImageFont.load_default()

        label_offset = label_width + spacing if row_labels else 0

        for idx, img in enumerate(images):
            row = idx // num_columns
            col = idx % num_columns

            x = label_offset + col * (max_width + spacing)
            y = row * (max_height + spacing)

            x_center = x + (max_width - img.size[0]) // 2
            y_center = y + (max_height - img.size[1]) // 2

            new_image.paste(img, (x_center, y_center))

            if col == 0 and row_labels and row < len(row_labels):
                # Calculate vertical center of the current row
                text_y = y + (max_height // 2)

                # Get the size of the text
                text = str(row_labels[row])
                try:
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_height = bbox[3] - bbox[1]
                except AttributeError:  # For older Pillow versions
                    text_height = font.getsize(text)[1]

                # Draw the label vertically centered with the row
                draw.text(
                    (spacing, text_y - text_height // 2),
                    text,
                    fill=(0, 0, 0, 255),  # Black text
                    font=font,
                )

        # Save combined image
        new_image.save(self.output_directory / image_output_name, "PNG")

        # Close all images
        for img in images:
            img.close()
        return self.output_directory / image_output_name

    def build_qc_metric(self, value: Any, reference: List[Path] = None) -> QCMetric:
        """Build a quality control metric from the provided settings.

        Parameters
        ----------
        value : Any
            Value of the metric
        """
        return QCMetric(
            name=self.settings.metric_name,
            value=value,
            reference=reference,
            status_history=self.settings.metric_status_history,
        )

    def build_qc_evaluation(self, metrics: List[QCMetric]) -> QCEvaluation:
        """Build a quality control evaluation from the provided settings.

        Parameters
        ----------
        metrics : List[QCMetric]
            List of metrics
        """
        return QCEvaluation(
            name=self.settings.evaluations_name,
            stage=self.settings.stage,
            modality=self.settings.modality,
            metrics=metrics,
        )

    def write_evaluation_to_json(self, evaluation: QCEvaluation):
        """Write the evaluation to a JSON file.

        Parameters
        ----------
        evaluation : QCEvaluation
            Evaluation object
        """
        with open(self.output_directory / "quality_evaluation.json", "w") as f:
            json.dump(json.loads(evaluation.model_dump_json()), f, indent=4)

    def evaluate_metrics(
        self,
        metrics: Dict[str, float],
        threshold: float,
        operation: Union[str, Callable] = ">",
    ) -> bool:
        """Flexible threshold-based evaluation of metrics

        Parameters
        ----------
        metrics : dict
            Dictionary of metrics where values are numeric
        threshold : float
            Threshold value for comparison
        operation : str or Callable
            Comparison operation to use. Can be one of '==', '!=', '<', '<=', '>', '>='
            or a custom comparison function that takes two arguments

        Returns
        -------
        bool
            True if any value in metrics satisfies the comparison with threshold

        Raises
        ------
        ValueError
            If operation string is not recognized
        TypeError
            If operation is neither a string nor a callable
        """
        if isinstance(operation, str):
            if operation not in Evaluation.OPERATORS:
                raise ValueError(
                    f"Unknown operation '{operation}'. "
                    f"Must be one of {list(Evaluation.OPERATORS.keys())}"
                )
            compare_func = Evaluation.OPERATORS[operation]

        elif callable(operation):
            compare_func = operation

        else:
            raise TypeError(
                "Operation must be either a string or a callable, "
                f"got {type(operation)}"
            )

        return any(compare_func(value, threshold) for value in metrics.values())

    def evaluate_metrics_all(
        self,
        metrics: Dict[str, float],
        threshold: float,
        operation: Union[str, Callable] = ">",
    ) -> bool:
        """Similar to evaluate_metrics but requires all values to satisfy the condition"""
        if isinstance(operation, str):
            if operation not in cls.OPERATORS:
                raise ValueError(
                    f"Unknown operation '{operation}'. "
                    f"Must be one of {list(cls.OPERATORS.keys())}"
                )
            compare_func = cls.OPERATORS[operation]
        elif callable(operation):
            compare_func = operation
        else:
            raise TypeError(
                "Operation must be either a string or a callable, "
                f"got {type(operation)}"
            )

        return all(compare_func(value, threshold) for value in metrics.values())
