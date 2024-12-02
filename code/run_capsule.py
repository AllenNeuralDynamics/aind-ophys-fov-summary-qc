""" Top level run script """

import argparse
import json
from datetime import datetime as dt
from pathlib import Path
import os

from aind_data_schema.core.quality_control import (QCEvaluation, QCStatus,
                                                   QualityControl, Stage,
                                                   Status)
from aind_data_schema_models.modalities import Modality
from aind_qcportal_schema.metric_value import CheckboxMetric
from fov_summary.session_evaluation import Evaluation, EvaluationSettings
from aind_data_schema.core.processing import Processing, DataProcess, PipelineProcess

# Define a configuration for Image name and image format pattern
# Store the
# Get images from each motion correction folder
# For each plane, sort the images
# append the images to a list
# Create the final FOV summary


def write_fov_summary(input_dir: Path, output_dir: Path):
    """Write FOV summary to quality evaluation json file"""
    fov_evaluation_settings = EvaluationSettings(
        input_directory=input_dir,
        output_directory=output_dir / "registration_summary",
        folder_name="motion_correction",
        pattern=["average_projection.png", "maximum_projection.png"],
        metric_name="Field of view summary",
        metric_status_history=[
            QCStatus(
                evaluator="Pending review", timestamp=dt.now(), status=Status.PENDING
            )
        ],
        stage=Stage.PROCESSING,
        modality=Modality.from_abbreviation("pophys"),
        evaluations_name="Registration Summary",
        allow_failed_metrics=True,
    )

    fov_evaluation = Evaluation(fov_evaluation_settings)
    row_labels, matched_files = fov_evaluation.collect_pattern_files()
    reference_image = fov_evaluation.combine_images(
        matched_files, "fov_summary.png", row_labels=row_labels
    )
    metric = fov_evaluation.build_qc_metric(
        value=CheckboxMetric(
            value="Field of view integrity",
            options=[
                "Timeseries shuffled between planes",
                "Field of view associated with incorrect area and/or depth",
                "Paired plane cross talk: Extreme",
                "Paired plane cross-talk: Moderate",
            ],
            status=[Status.PASS, Status.FAIL, Status.FAIL, Status.PASS],
        ),
        reference=str(reference_image),
    )
    evaluation = fov_evaluation.build_qc_evaluation([metric])
    fov_evaluation.write_evaluation_to_json(evaluation)


def write_interictal_summary(input_dir: Path, output_dir: Path):
    """Write the interictal summary to a combined image and json file"""
    interictal_evaluation_settings = EvaluationSettings(
        input_directory=input_dir,
        output_directory=output_dir / "interictal_summary",
        folder_name="movie_qc",
        pattern=["registered_epilepsy_probability.png"],
        metric_name="Interictal Event Images",
        metric_status_history=[
            QCStatus(
                evaluator="Pending review", timestamp=dt.now(), status=Status.PENDING
            )
        ],
        stage=Stage.PROCESSING,
        modality=Modality.from_abbreviation("pophys"),
        evaluations_name="Interictal Event Images",
        allow_failed_metrics=True,
    )
    interictal_evaluation = Evaluation(interictal_evaluation_settings)
    row_labels, matched_files = interictal_evaluation.collect_pattern_files()
    reference_image = interictal_evaluation.combine_images(
        matched_files, "interictal_summary.png", row_labels=row_labels
    )
    metric = interictal_evaluation.build_qc_metric(
        value=CheckboxMetric(
            value="Field of view integrity",
            options=[
                "Interictal events confirmed by manual inspection",
                "Interictal events contravened by manual inspection",
            ],
            status=[Status.PASS, Status.FAIL],
        ),
        reference=str(reference_image),
    )
    evaluation = interictal_evaluation.build_qc_evaluation([metric])
    interictal_evaluation.write_evaluation_to_json(evaluation)


def write_event_probability(input_dir: Path, output_dir: Path):
    """Writes the epilepsy probability summary to a json file"""
    event_probability = EvaluationSettings(
        input_directory=input_dir,
        output_directory=output_dir / "epilepsy_probability",
        folder_name="movie_qc",
        pattern=["registered_metrics.json"],
        metric_name="Epilepsy Probability",
        metric_status_history=[
            QCStatus(
                evaluator="Pending review", timestamp=dt.now(), status=Status.PENDING
            )
        ],
        stage=Stage.PROCESSING,
        modality=Modality.from_abbreviation("pophys"),
        evaluations_name="Epilepsy Probability",
        allow_failed_metrics=False,
    )
    event_probability_evaluation = Evaluation(event_probability)
    row_labels, matched_files = event_probability_evaluation.collect_pattern_files()
    epilepsy_metric_summary = {}
    for label, file in zip(row_labels, matched_files):
        with open(file) as f:
            data = json.load(f)
        epilepsy_metric_summary[label] = data["epilepsy_probability"]
    evaluation_metric = event_probability_evaluation.evaluate_metrics(
        epilepsy_metric_summary, 0.5
    )
    metric = event_probability_evaluation.build_qc_metric(
        value=evaluation_metric
    )
    evaluation = event_probability_evaluation.build_qc_evaluation([metric])
    event_probability_evaluation.write_evaluation_to_json(evaluation)

def write_core_metadata(input_dir: Path, output_dir: Path, **kwargs):
    """Writes final quality control json by aggregating evaluations"""
    for data_type in kwargs.values():
        if "evaluation" in data_type.lower():
            file_path = output_dir.rglob(f"*{data_type}*")
        elif "data_process" in data_type.lower():
            file_path = input_dir.rglob(f"*{data_type}*")
    metadata = []
    for file in file_path:
        with open(file) as j:
            data = json.load(j)
        if "evaluation" in str(file):
            metadata.append(QCEvaluation(**data))
        elif "data_process" in str(file):
            metadata.append(DataProcess(**data))
    if "evaluation" in kwargs["data_type"]:
        core_metadata = QualityControl(evaluations=metadata)
    elif "data_process" in kwargs["data_type"]:
        core_metadata = Processing(
            processing_pipeline=PipelineProcess(
            processor_full_name="Multplane Ophys Processing Pipeline",
            pipeline_url=os.getenv("PIPELINE_URL", ""),
            pipeline_version=os.getenv("PIPELINE_VERSION", ""),
            data_processes=metadata
        )
    )
    core_metadata.write_standard_file(output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a quality control report for a pophys dataset"
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default="../data/",
        help="Path to the input directory containing the data",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="../results/",
        help="Path to the output directory to store the results",
    )
    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    # Buile the fov summary metric
    write_fov_summary(input_dir, output_dir)
    # Build the interictal summary images
    write_interictal_summary(input_dir, output_dir)
    # Build the epilepsy probability metric
    write_event_probability(input_dir, output_dir)
    # Write quality control json    # Aggregate data procs and build processing json
    write_core_metadata(input_dir, output_dir, data_type = "evaluation")
    # Write processing json
    write_core_metadata(input_dir, output_dir, data_type = "data_process")