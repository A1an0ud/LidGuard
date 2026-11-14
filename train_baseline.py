"""Train one fixed baseline on the supplied RT-BENE RGB subset.

Usage: python train_baseline.py --zip /path/to/RGB_RT-BENE_NONCOMMERCIAL_CC-BY-NC-SA-4.0.zip
No hyperparameter search or seed selection. Held-out subjects never enter fitting.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import platform
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import numpy as np
import PIL
import sklearn
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

from lidguard.inference import EyeBaseline, FEATURE_SIZE, features


ROOT = Path(__file__).resolve().parent
SEED = 42


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT)
    args = parser.parse_args()
    if not args.zip.is_file():
        parser.error("Dataset ZIP not found")
    items, images, labels, groups = [], [], [], []
    with zipfile.ZipFile(args.zip) as archive:
        names = sorted(n for n in archive.namelist() if n.lower().endswith(".png") and not n.startswith("__MACOSX/"))
        for name in names:
            label_name = PurePosixPath(name).parent.name
            if label_name not in {"open", "closed"}:
                continue
            match = re.search(r"__s(\d+)_", name)
            if not match:
                raise ValueError("Subject ID is required for every image: " + name)
            info = archive.getinfo(name)
            if info.file_size > 2 * 1024 * 1024:
                raise ValueError("Unexpected image size: " + name)
            raw = archive.read(name)
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            image.load()
            if image.size != (60, 36):
                raise ValueError("Expected RT-BENE 60x36 eye crops: " + name)
            subject = "s" + match.group(1)
            items.append({"archive_path": name, "sha256": hashlib.sha256(raw).hexdigest(), "label": label_name.upper(), "subject": subject})
            images.append(image)
            labels.append(1 if label_name == "open" else 0)
            groups.append(subject)
    if len(items) != 100 or len(set(groups)) != 10 or labels.count(1) != 50:
        raise ValueError("This version expects the supplied 100-image, 10-subject, balanced RGB subset. Do not silently substitute another dataset.")
    X = np.stack([features(image) for image in images])
    y = np.array(labels, dtype=int)
    groups = np.array(groups)
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    train, test = next(splitter.split(X, y, groups))
    assert not set(groups[train]) & set(groups[test])
    scaler = StandardScaler().fit(X[train])
    model = LogisticRegression(C=1.0, solver="liblinear", penalty="l2", class_weight="balanced", max_iter=2000, random_state=SEED)
    model.fit(scaler.transform(X[train]), y[train])
    probability = model.predict_proba(scaler.transform(X[test]))[:, 1]
    predictions = (probability >= 0.5).astype(int)
    precision, recall, f1, support = precision_recall_fscore_support(y[test], predictions, labels=[0, 1], zero_division=0)
    metrics = {
        "evaluation_name": "One fixed subject-held-out RGB baseline evaluation",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dataset": "User-supplied 100-image RT-BENE RGB subset; 50 open, 50 closed",
        "split": {"method": "GroupShuffleSplit", "random_state": SEED, "test_fraction_of_subjects": 0.2, "train_subjects": sorted(set(groups[train])), "test_subjects": sorted(set(groups[test])), "train_images": int(len(train)), "test_images": int(len(test)), "subject_overlap": 0},
        "model": {"classifier": "LogisticRegression", "features": "30x18 grayscale pixels divided by 255, StandardScaler fitted on training images only", "C": 1.0, "solver": "liblinear", "penalty": "l2", "class_weight": "balanced", "max_iter": 2000, "random_state": SEED, "hyperparameter_search": False},
        "binary_holdout": {"accuracy": float(accuracy_score(y[test], predictions)), "balanced_accuracy": float(balanced_accuracy_score(y[test], predictions)), "auc_open": float(roc_auc_score(y[test], probability)), "confusion_matrix_order": ["CLOSED", "OPEN"], "confusion_matrix_rows_true_columns_predicted": confusion_matrix(y[test], predictions, labels=[0, 1]).tolist(), "per_class": {name: {"precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]), "support": int(support[i])} for i, name in enumerate(["CLOSED", "OPEN"])}, "correct": int(np.sum(predictions == y[test])), "total": int(len(test))},
        "limitations": ["Only 100 selected images from 10 people; held-out sample is very small.", "No cross-camera, NIR, ICU-patient or clinical validation.", "Subject-independent within this subset does not establish population generalization.", "This baseline differs from the previously reported Orange image-embedding experiment on 71 images.", "No segmentation, partial-opening or clinical corneal-exposure labels.", "Model score and alert timing are uncalibrated engineering demonstration settings."],
        "runtime_versions": {"python": platform.python_version(), "numpy": np.__version__, "scikit_learn": sklearn.__version__, "Pillow": PIL.__version__},
    }
    output = args.output.resolve()
    (output / "models").mkdir(parents=True, exist_ok=True)
    (output / "results").mkdir(parents=True, exist_ok=True)
    model_data = {"schema_version": 1, "name": "LidGuard RGB pixel logistic baseline v0.1", "feature_size": list(FEATURE_SIZE), "feature_transform": "grayscale_bilinear_30x18_div255_standard_scale", "classes": ["CLOSED", "OPEN"], "scaler_mean": scaler.mean_.tolist(), "scaler_scale": scaler.scale_.tolist(), "weights": model.coef_[0].tolist(), "intercept": float(model.intercept_[0]), "training_source": {"name": "RT-BENE subset", "source_url": "https://zenodo.org/records/3685316", "license": "CC-BY-NC-SA-4.0", "commercial_use_permitted": False, "raw_images_included": False}, "evaluation": {"split": metrics["split"], "binary_holdout": metrics["binary_holdout"], "claim_scope": "RGB eye-crop classification only; not clinical/device/NIR performance"}}
    model_path = output / "models" / "rgb_lr.json"
    model_path.write_text(json.dumps(model_data, indent=2) + "\n", encoding="utf-8")
    runtime = EyeBaseline(model_path)
    runtime_predictions = [runtime.predict(images[i], roi_confirmed=True) for i in test]
    evaluated = [j for j, result in enumerate(runtime_predictions) if result["state"] != "UNKNOWN"]
    runtime_correct = sum(runtime_predictions[j]["state"] == ("OPEN" if y[test[j]] else "CLOSED") for j in evaluated)
    metrics["runtime_abstention_holdout"] = {"minimum_score": 0.75, "manual_roi_confirmed_for_dataset_crops": True, "classified_images": len(evaluated), "unknown_images": len(test) - len(evaluated), "coverage": len(evaluated) / len(test), "correct_among_classified": int(runtime_correct), "accuracy_among_classified": None if not evaluated else runtime_correct / len(evaluated), "note": "Quality gates and score abstention are heuristic; this is not a clinical uncertainty validation."}
    heldout = []
    for j, idx in enumerate(test):
        heldout.append({"archive_path": items[idx]["archive_path"], "subject": items[idx]["subject"], "actual": items[idx]["label"], "binary_prediction": "OPEN" if predictions[j] else "CLOSED", "p_open_uncalibrated": float(probability[j]), "runtime_state": runtime_predictions[j]["state"], "runtime_quality": runtime_predictions[j]["quality"]})
    for idx, item in enumerate(items):
        item["split"] = "train" if idx in set(train.tolist()) else "test"
    manifest = {"archive_name": args.zip.name, "archive_sha256": hashlib.sha256(args.zip.read_bytes()).hexdigest(), "total_images": len(items), "raw_images_included": False, "source_url": "https://zenodo.org/records/3685316", "license": "CC-BY-NC-SA-4.0", "selection_before_upload": "Not documented in supplied archive", "files": items}
    (output / "results" / "rgb_holdout_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (output / "results" / "rgb_holdout_predictions.json").write_text(json.dumps(heldout, indent=2) + "\n", encoding="utf-8")
    (output / "results" / "rgb_data_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    model_data["evaluation"]["runtime_abstention_holdout"] = metrics["runtime_abstention_holdout"]
    model_path.write_text(json.dumps(model_data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"split": metrics["split"], "binary_holdout": metrics["binary_holdout"], "runtime_abstention_holdout": metrics["runtime_abstention_holdout"]}, indent=2))


if __name__ == "__main__":
    main()
