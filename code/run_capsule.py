""" Top level run script """
from pathlib import Path
from fov_summary.utils import combine_images
from datetime import datetime as dt
from aind_data_schema.core.quality_control import (
    QCEvaluation,
    QCMetric,
    Stage,
    QualityControl,
    Status,
    QCStatus
)
from aind_data_schema_models.modalities import Modality
import json
from aind_qcportal_schema.metric_value import (
    CheckboxMetric,
    RulebasedMetric
)
# Define a configuration for Image name and image format pattern
# Store the 
# Get images from each motion correction folder
# For each plane, sort the images
# append the images to a list
# Create the final FOV summary

def evaluate_metrics(d: dict, threshold: float) -> bool:
    return any(value > threshold for value in d.values())

if __name__ == "__main__":
    input_dir = Path("../data/")
    output_dir = Path("../results/")
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
    registration_image_fp = Path(*registration_image_fp.parts[2:])

    registration_metric = QCMetric(
        name = "Field of view summary",
        reference = str(registration_image_fp),
        status_history = [
            QCStatus(
                evaluator = "Pending review",
                timestamp = dt.now(),
                status = Status.PENDING
            )
        ],
        value = CheckboxMetric(
            value = "Field of view integrity",
            options = [
                "Timeseries shuffled between planes",
                "Field of view associated with incorrect area and/or depth",
                "Paired plane cross talk: Extreme",
                "Paired plane cross-talk: Moderate",
            ],
            status = [
                Status.PASS,
                Status.FAIL,
                Status.FAIL,
                Status.PASS
            ],
        ),
    )

    registation_evaluation = QCEvaluation(
        modality=Modality.from_abbreviation("pophys"),
        stage = Stage.PROCESSING,
        name = "Registration Summary",
        metrics = [registration_metric],
        allow_failed_metrics = False
    )
    with open(registration_dir / "quality_evaluation.json", "w") as f:
        json.dump(json.loads(registation_evaluation.model_dump_json()), f, indent=4)
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
    epilepsy_image_fp = Path(*epilepsy_image_fp.parts[2:])
    
    epilepsy_references = QCMetric(
       name = "Interictal Event Images",
       reference = str(epilepsy_image_fp),
       status_history=[                                
            QCStatus(
                evaluator='Pending review',
                timestamp=dt.now(),
                status=Status.PENDING
            )
        ],
        value = CheckboxMetric(
            value = "Field of view integrity",
            options = [
                "Interictal events confirmed by manual inspection",
                "Interictal events contravened by manual inspection"
            ],
            status = [
                Status.PASS,
                Status.FAIL
            ]
        )

    )
    epilepsy_ref_evaluation = QCEvaluation(
        modality=Modality.from_abbreviation("pophys"),
        stage = Stage.PROCESSING,
        name = "Interictal Events",
        metrics = [epilepsy_references],
        allow_failed_metrics = False
    )
    with open(epilepsy_dir / "quality_evaluation.json", "w") as f:
        json.dump(json.loads(epilepsy_ref_evaluation.model_dump_json()), f, indent=4)
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
    
    epilepsy_metric = QCMetric(
        name = "Interictal Metrics",
        value = RulebasedMetric(
            value=evaluate_metrics(epilepsy_metric_summary, 0.5),
            rule="Fail for epilepsy probablity > 0.5",
        ),
    status_history=[                                
        QCStatus(
            evaluator='Pending status',
            timestamp=dt.now(), #TODO: Use same timestamp for all metrics?
            # Requires manual annotation
            status=Status.PENDING
        )
    ]
    )
    epilepsy_metric_evaluation = QCEvaluation(
        modality=Modality.from_abbreviation("pophys"),
        stage = Stage.PROCESSING,
        name = "Epilepsy Probability, %",
        metrics = [epilepsy_metric],
        allow_failed_metrics = False
        
    )
    with open(epilepsy_dir / "quality_evaluation.json", "w") as f:
        json.dump(json.loads(epilepsy_metric_evaluation.model_dump_json()), f, indent=4)

    quality_evaluation_fp = output_dir.rglob("*quality_evaluation.json")
    quality_evaluations = []
    for qual_eval in quality_evaluation_fp:
        with open(qual_eval) as j:
            evaluation = json.load(j)
        quality_evaluations.append(QCEvaluation(**evaluation))
    quality_evaluation_fp = input_dir.rglob("*quality_evaluation.json")
    for qual_eval in quality_evaluation_fp:
        with open(qual_eval) as j:
            evaluation = json.load(j)
        quality_evaluations.append(QCEvaluation(**evaluation))
    quality_control = QualityControl(
        evaluations = quality_evaluations
    )
    print("Writing output file")
    quality_control.write_standard_file()




