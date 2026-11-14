# LidGuard

## Eye-state monitoring engineering prototype

LidGuard is a local engineering prototype developed for MEDATHON 2026. It estimates eyelid state from a manually selected eye region and implements an alert timer, event acknowledgment, and CSV event export.

The binary RGB model estimates **OPEN** or **CLOSED**. Input-quality checks, missing operator confirmation, and score-based abstention can return **UNKNOWN**. UNKNOWN is not a separately trained class.

## Validation status

| Area | Recorded status |
| --- | --- |
| Python logic and HTTP API | 15 automated tests passed |
| JavaScript syntax | Syntax check passed |
| Interactive browser workflow | Not yet validated |
| Windows launcher on Windows | Not yet validated |
| Live webcam and Raspberry Pi CSI camera | Not yet validated |
| NIR imaging and clinical use | Not validated |

The recorded checks are in [software_validation.json](results/software_validation.json) and [browser_validation.json](results/browser_validation.json). Implemented camera adapters are separate from demonstrated operation on physical hardware.

This is a research prototype. OPEN/CLOSED image classification does not determine corneal exposure, clinical exposure grades, or eye injury. The default **5-second** alert threshold and **0.75** model-score cutoff are demonstration settings, not clinical limits. Model scores are uncalibrated.

## Quick start on Windows

Requirements: Python 3.10 or newer and internet access for the initial dependency installation.

1. Extract the complete repository into a folder.
2. Double-click **START_WINDOWS.bat**.
3. Keep the terminal window open while using the application.
4. Open **http://localhost:8765** if the browser does not open automatically.

The launcher creates a project virtual environment, installs missing NumPy/Pillow dependencies, and starts the application. Equivalent PowerShell commands, run from the repository directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --open-browser
```

Using the virtual environment's Python directly does not require changing PowerShell's execution policy. scikit-learn is required only to repeat training.

### Troubleshooting

- **Python is not found:** install a supported Python version from [python.org](https://www.python.org/downloads/windows/), reopen the terminal, and retry.
- **Dependency installation fails:** keep the error text and check internet access. Rerun the dependency-installation command above after resolving the reported error.
- **Port 8765 is already in use:** stop the earlier LidGuard process before starting another instance.
- **The browser does not open:** enter `http://localhost:8765` manually while the server remains running.
- **A camera cannot start:** confirm browser permission for a webcam; for a CSI camera, follow the [Raspberry Pi setup guide](docs/HARDWARE.md).

## Demonstrate the alert workflow

No image dataset or camera is needed for **Simulation**. This mode uses manually selected states and is explicitly separate from image inference.

1. Select **Simulation**, then **Closed**.
2. Select **Open** and wait five seconds for **Review requested**.
3. Select **Acknowledge this event**. The event remains visible while the condition persists.
4. Select **Unable to assess**. The continuous-open timer resets and the earlier alert remains unresolved.
5. Select **Closed**. The demonstration alert clears.
6. Export the event log. These rows are labeled `simulation`.

Acknowledgment records receipt of an event; it does not establish that the underlying condition has resolved. A simulated CLOSED transition is a software state change, not confirmation of clinical protection.

## Image and camera inputs

| Source | Input and behavior |
| --- | --- |
| Simulation | Manual OPEN/CLOSED/UNKNOWN states for checking the timer and alerts |
| Image test | One RGB image, tightly cropped around one visible eye; a snapshot never accumulates exposure duration |
| Computer camera | Browser webcam, a manually drawn eye region, and explicit operator confirmation |
| Raspberry Pi camera | Optional Picamera2 adapter for a supported CSI camera on the computer running the server |

For **Image test**, select a suitable RGB eye image, confirm that one eye is visible in the selected region, and select **Classify selected eye**. Dataset images are not bundled with this repository.

For **Computer camera**, run the server on the computer with the webcam, open the interface at localhost, select the source, and press **Start camera**. Allow the browser's camera permission. Draw a tight rectangle around one eye and check **I can see one eye clearly in the selected region**. Clear the confirmation if the eye moves out of view.

There is no validated automatic eye-localization or eye-presence detector. A textured background can be misclassified if operator confirmation remains enabled. Illumination, camera properties, framing, spectacles, and makeup can differ from the evaluation data. A working camera stream does not establish classification accuracy.

For the CSI adapter and SSH port forwarding, see [docs/HARDWARE.md](docs/HARDWARE.md).

## Processing and event behavior

- Images are decoded, converted to grayscale, resized to 30 x 18 pixels, scaled using training-set statistics, and classified with logistic regression.
- The timer uses consecutive valid OPEN observations. Missing or stale observations reset continuity; an existing alert remains unresolved until a defined state transition or explicit reset.
- A single image upload never establishes a duration.
- Images are processed in memory and are not saved by the application. The runtime interface uses local assets and makes no external network calls; installing dependencies requires internet access.
- Event records remain in memory until exported and are lost when the server stops. Source labels distinguish simulation, image uploads, and camera observations.

## RGB evaluation

The evaluation uses a **100-image RT-BENE research subset**, containing 50 OPEN and 50 CLOSED images from 10 people. One fixed subject-disjoint split was used, with no hyperparameter search or selection of a favorable seed. The subset-selection method before this experiment was not documented.

| Item | Result |
| --- | --- |
| Training partition | 79 images from 8 people |
| Holdout partition | 21 images from 2 different people: s004 and s015 |
| Subject overlap | 0 |
| Split | GroupShuffleSplit, 20% of subjects, random seed 42 |
| Features | 30 x 18 grayscale pixels divided by 255; StandardScaler fitted on training images only |
| Classifier | Logistic regression, C=1, L2, balanced classes, liblinear |
| Binary classification before abstention | 20/21 correct (95.24%) |
| Runtime result with quality checks and score cutoff | 18 correct, 1 incorrect, 2 UNKNOWN |
| Accuracy among classified images | 18/19 (94.74%) |
| Classification coverage | 19/21 (90.48%) |

These results concern the recorded eye-crop experiment. A two-person holdout does not establish population, live-camera, NIR, device, or ICU performance. The quality gates are heuristic and do not provide a general occlusion or uncertainty detector.

Supporting files:

- [Metrics and recorded software versions](results/rgb_holdout_metrics.json)
- [Per-image holdout predictions](results/rgb_holdout_predictions.json)
- [Dataset filenames, hashes, and train/test membership](results/rgb_data_manifest.json)

### Earlier Orange experiment

[The archived Orange report](reports/orange_results_reported.html) records a separate 71-image, five-fold image-embedding experiment. Its reported results are not the results of the classifier loaded by this application. The corresponding Orange workflow, trained estimator, fold assignments, and full preprocessing settings are not part of this release, so that experiment has not been reproduced here. Subject separation across its folds is undocumented. The two headline accuracies do not demonstrate an improvement because their evaluation protocols differ.

## Tests and training

Run the existing Python tests from the repository directory:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The tests cover the state machine, timer continuity, stale input, unresolved alerts, acknowledgment, source isolation, stale-source request rejection, snapshots, image decoding, and heuristic quality checks. They do not substitute for interactive browser or hardware testing.

Training and evaluation scripts are included. **Reproducing the reported metrics requires the exact image subset identified by the SHA256 manifest**; dataset images are not redistributed. Source data and terms are available from the [RT-BENE authors](https://zenodo.org/records/3685316). Downloading the full source dataset alone does not recreate the selected subset automatically.

After obtaining the documented subset, replace the example archive path below with its actual location:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe train_baseline.py --zip "C:\datasets\RGB_RT-BENE_NONCOMMERCIAL_CC-BY-NC-SA-4.0.zip"
```

The training script validates the expected subset shape and writes the numeric JSON model, metrics, provenance manifest, and per-image predictions. The model is fitted only to the training partition. It is not refitted using holdout observations. Dependency ranges are specified in the requirements files; exact evaluation versions are recorded in the metrics file.

## Repository structure

| Path | Purpose |
| --- | --- |
| `app.py` | Application entry point |
| `START_WINDOWS.bat` | Windows setup and launch helper |
| `lidguard/` | Inference, state handling, HTTP service, and optional CSI capture |
| `web/` | Local browser interface |
| `models/` | Numeric JSON model and data attribution notice |
| `train_baseline.py` | Fixed baseline training and evaluation |
| `tests/` | Automated Python and API tests |
| `results/` | Evaluation, provenance, and validation records |
| `reports/` | Clearly labeled earlier experiment |
| `docs/` | Hardware setup and scientific/technical references |

## Data attribution and limitations

RT-BENE is attributed to Kevin Cortacero, Tobias Fischer, and Yiannis Demiris (2019). The source dataset uses **CC BY-NC-SA 4.0** and explicitly excludes commercial use. Preserve [models/NOTICE.txt](models/NOTICE.txt) and review the upstream terms. Availability of this repository does not establish commercial permission for the trained artifact. No project-wide reuse license has been specified.

This release does not implement or validate clinical corneal-exposure grading, partial-opening measurement, dressing assessment, or treatment decisions. It does not use the separately considered PopEYE NIR dataset. Future work includes reliable eye localization, broader evaluation with people separated between partitions, live-camera validation, and clinical definition and validation of exposure-related outputs.

Scientific and engineering sources are listed in [docs/REFERENCES.md](docs/REFERENCES.md).
