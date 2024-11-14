""" Top level run script """
from pathlib import Path
from fov_summary.utils import combine_images
from aind_data_schema.core.quality_control import (
    QCEvaluation,
    QCMetric,
    Stage
)
from aind_data_schema_models.modalities import Modality
import json
# Define a configuration for Image name and image format pattern
# Store the 
# Get images from each motion correction folder
# For each plane, sort the images
# append the images to a list
# Create the final FOV summary
{
    "Registration Summary": {
        "Average Projection": "*average_projection.png",
        "Maximum Projection": "*maximum_projection.png",
    },
    "Interictal Events": {

    }
}



if __name__ == "__main__":
    input_dir = Path("data/")
    output_dir = Path("results/")
    if len(list(input_dir.glob("*"))) == 1:
        input_dir = next(input_dir.glob("*"))
    motion_dirs = [plane for plane in input_dir.rglob("motion_correction")]
    movie_qc_dirs = [plane for plane in input_dir.rglob("movie_qc")]

    ############### REGISTRATION SUMMARY ###############
    registration_summary = []
    row_labels = []
    average_projection = "average_projection.png"
    maximum_projection = "maximum_projection.png"
    for plane in motion_dirs:
        avg_proj_fp = [i for i in plane.glob("*") if average_projection in str(i)][0]
        max_proj_fp = [i for i in plane.glob("*") if maximum_projection in str(i)][0]
        row_labels.append(plane.parent.name)
        registration_summary.append(avg_proj_fp)
        registration_summary.append(max_proj_fp)
    
    registration_dir = output_dir / "registration_summary"
    registration_dir.mkdir(exist_ok=True)
    registration_image_fp = registration_dir / "fov_summary.png"
    combine_images(registration_summary, registration_image_fp, row_labels=row_labels)
    registration_image_fp = Path(*registration_image_fp.parts[1:])

    registration_metric = QCMetric (
        name = "FOV Summary",
        reference = str(registration_image_fp),
        value = None
    )
    registation_evaluation = QCEvaluation(
        modality=Modality.from_abbreviation("pophys"),
        stage = Stage.PROCESSING,
        name = "Registration Summary",
        metrics = [registration_metric],
        allow_failed_metrics = False
    )
    with open(registration_dir / "quality_evaluation.json", "w") as f:
        json.dump(registation_evaluation.model_dump(), f, indent=4)
    ############### INTERICTAL REF SUMMARY ###############

    event_pattern = "registered_epilepsy_probability.png"
    row_labels = []
    epilepsy_summary = []
    for plane in movie_qc_dirs:
        event_fp = [i for i in plane.glob("*") if event_pattern in str(i)][0]
        row_labels.append(plane.parent.name)
        epilepsy_summary.append(event_fp)
    
    epilepsy_dir = output_dir / "epilepsy_ref_summary"
    epilepsy_dir.mkdir(exist_ok=True)
    epilepsy_image_fp = epilepsy_dir / "epilepsy.png"
    combine_images(epilepsy_summary, epilepsy_image_fp, row_labels=row_labels)
    epilepsy_image_fp = Path(*epilepsy_image_fp.parts[1:])
    
    epilepsy_references = QCMetric (
        name = "Interictal Event Images",
        reference = str(epilepsy_image_fp),
        value = None
    )
    epilepsy_ref_evaluation = QCEvaluation(
        modality=Modality.from_abbreviation("pophys"),
        stage = Stage.PROCESSING,
        name = "Interictal Events",
        metrics = [epilepsy_references],
        allow_failed_metrics = False
    )
    with open(epilepsy_dir / "quality_evaluation.json", "w") as f:
        json.dump(epilepsy_ref_evaluation.model_dump(), f, indent=4)
    ############### INTERICTAL METRIC SUMMARY ###############

    event_pattern = "registered_metrics.json"
    epilepsy_metric_summary = {}
    for plane in movie_qc_dirs:
        event_fp = [i for i in plane.glob("*") if event_pattern in str(i)][0]
        with open(event_fp) as f:
            data = json.load(f)
        epilepsy_metric_summary[plane.parent.name] = data["epilepsy_probability"]
    
    epilepsy_dir = output_dir / "epilepsy_metric_summary"
    epilepsy_dir.mkdir(exist_ok=True)
    
    epilepsy_metrics = QCMetric (
        name = "Interictal Metrics",
        value = epilepsy_metric_summary
    )
    epilepsy_metric_evaluation = QCEvaluation(
        modality=Modality.from_abbreviation("pophys"),
        stage = Stage.PROCESSING,
        name = "Epilepsy Probability, %",
        metrics = [epilepsy_metrics],
        allow_failed_metrics = False
    )
    with open(epilepsy_dir / "quality_evaluation.json", "w") as f:
        json.dump(epilepsy_metric_evaluation.model_dump(), f, indent=4)