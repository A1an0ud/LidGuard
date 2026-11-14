# LidGuard

## Eye-state monitoring engineering prototype for MEDATHON 2026

This repository contains a working local application, a small RGB eye-state classifier, a demonstration alert workflow, and reproducible evaluation outputs. It supports image upload, a browser camera, and an optional Raspberry Pi CSI camera adapter. An explicitly labeled simulation mode can be used to test the timer and alert behavior without a camera.

**Current scope:** manually select one eye, estimate OPEN / CLOSED / UNKNOWN, track continuous detected opening, show a review alert, acknowledge an event, and export a CSV log. A person must confirm that the selected region actually contains a visible eye.

**Not established:** automated eye localization or eye-presence detection, partial-opening measurement, corneal visibility, clinical exposure grades, NIR performance, protection from dressings, or performance in ICU patients. OPEN is an image category, not a diagnosis of corneal exposure. The default 5-second alert threshold and 0.75 model-score threshold are demonstration settings, not clinical limits.

The application processes images in memory and does not save them or make external network calls. Installing dependencies requires internet access. Events are held in memory until exported, and are lost when the server stops.

## Start on Windows

1. Extract the entire project folder. Do not run it inside the ZIP archive.
2. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/windows/) if Python is not already available.
3. Double-click **START_WINDOWS.bat**. The launcher creates a local virtual environment, installs missing runtime dependencies, and opens the interface.
4. Keep the terminal window open while using the application. The interface is at **http://localhost:8765**.

Equivalent commands from the project folder:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py --open-browser
```

Calling the virtual environment's Python directly avoids changing PowerShell's execution policy. Runtime dependencies are NumPy and Pillow; scikit-learn is needed only to repeat training.

## Run a two-minute software check

1. Open **Simulation** and choose **Closed**. The state should become CLOSED.
2. Choose **Open** and wait five seconds. A review alert should appear.
3. Acknowledge the alert. It must remain visible while the condition persists.
4. Choose **Unable to assess**. The timer resets, while the previous alert remains visibly unresolved.
5. Choose **Closed**. The observation changes and the demo alert clears. This is not confirmation of medical protection.
6. Export the event log. Its source column must say `simulation` for these events.
7. Switch to **Image test**. Choose one of the RGB eye images already supplied to the team, confirm the visible eye region, and click **Classify selected eye**. One image never starts the duration timer.

## Live camera modes

### Computer camera

Run the server on the same computer whose webcam you intend to use. Open the app at localhost, select **Computer camera**, and press **Start camera**. Allow the browser's camera permission.

Drag a tight rectangle around one eye and check **I can see one eye clearly in the selected region**. Keep the eye in that region. Clear the checkbox when the eye moves out of view. The app sends selected crops to the local server approximately twice per second.

The classifier has been evaluated only on the small provided RGB dataset. Webcam lighting, scale, framing, makeup, spectacles, and camera properties can differ. A functioning live image stream is not evidence that live classification is accurate. Record what happens on the actual camera, including errors and UNKNOWN outputs.

### Raspberry Pi CSI camera

The team's previously recorded board is Raspberry Pi 4 Model B, 2 GB, with a 5 MP CSI camera. The sensor model and NoIR status need to be identified from the actual part. The hardware was not available in the environment where this package was prepared.

First complete OS setup and verify camera capture separately. See the Arabic [hardware and filming guide](docs/HARDWARE_AND_FILMING_AR.md).

On a supported current Raspberry Pi OS, use OS-managed camera dependencies:

```bash
sudo apt update
sudo apt install python3-numpy python3-pil python3-picamera2 rpicam-apps
rpicam-hello --list-cameras
rpicam-still -n -o test.jpg
/usr/bin/python3 app.py --open-browser
```

Select **Raspberry Pi camera**, then **Start camera**. The adapter starts Picamera2 only after this explicit action, captures frames in memory, and does not require the CSI camera to appear in browser webcam permissions. It returns a readable error if Picamera2 or the camera is unavailable.

If using a virtual environment on Pi, create it with `--system-site-packages` to retain access to OS-managed Picamera2/libcamera. Do not replace camera packages with arbitrary pip versions. The direct `/usr/bin/python3` path above avoids that extra setup.

The server listens on localhost. If the Pi has no display but SSH is already configured, forward its local app port from Windows:

```powershell
ssh -L 8765:127.0.0.1:8765 YOUR_PI_USERNAME@YOUR_PI_ADDRESS
```

Use the real Pi username/address. Keep this SSH session open, run the app on the Pi, and open `http://localhost:8765` on Windows. Select **Raspberry Pi camera** for CSI images. Selecting **Computer camera** would instead request the Windows computer's webcam. Do not run a second local app on the same port simultaneously.

## Measured results

The evaluation used the supplied **100-image RT-BENE RGB subset** (50 OPEN, 50 CLOSED). It used one fixed subject-disjoint split, with no hyperparameter search or choice of a favorable test seed.

| Item | Result |
|---|---|
| Training | 79 images from 8 people |
| Holdout test | 21 images from 2 different people (`s004`, `s015`) |
| Subject overlap | 0 |
| Fixed split | GroupShuffleSplit, 20% of subjects, seed 42 |
| Features | 30 × 18 grayscale pixels, normalized to 0–1; StandardScaler fitted only on training images |
| Classifier | Logistic regression, C=1, L2, balanced classes, liblinear |
| Binary classification before abstention | 20 / 21 correct (95.24%) |
| Runtime behavior with quality checks and score cutoff | **18 correct, 1 incorrect, 2 UNKNOWN** across all 21 test images |
| Accuracy among the 19 classified images | 18 / 19 (94.74%) |
| Classification coverage | 19 / 21 (90.48%) |

The two-person holdout is very small. These numbers do not establish performance on another camera, under NIR illumination, or in patients. The heuristic quality gates do not detect every missing-eye or occluded-eye situation.

The earlier Orange results page is preserved under `reports/orange_results_reported.html`. It describes a **different** 71-image, five-fold evaluation. Its workflow and trained model were not included in the provided files, so those figures were not reproduced here. Do not compare the two headline accuracies as an improvement claim.

### Reproduce training

Training data are not redistributed in this repository. Use the team's original `RGB_RT-BENE_NONCOMMERCIAL_CC-BY-NC-SA-4.0.zip` and preserve its filename or pass its actual location:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-training.txt
.\.venv\Scripts\python.exe train_baseline.py --zip "PATH_TO_RGB_ZIP"
```

Run `python train_baseline.py --help` for the exact output arguments. The script produces the JSON model, metrics, file manifest with SHA256 hashes, and individual holdout predictions. The supplied model remains fitted to the training partition; holdout data are not used to refit it.

The current inference model uses JSON numeric arrays, not executable pickle objects. Model scores are uncalibrated and must not be read as clinical probabilities.

## Software verification

```bash
python -m unittest discover -s tests -v
```

The software tests cover timer continuity, stale camera input, unresolved alerts, acknowledgment, snapshot behavior, source separation, stale response rejection, image decoding, and basic quality rejection. See `results/software_validation.json` for the exact test count and execution record. Browser checks, when present, are documented separately in `results/browser_validation.json`.

Automated software checks do not establish performance of a real webcam or a Raspberry Pi camera. The team's hardware integration, Windows environment, and live camera behavior require checks on the actual equipment.

## Project map

| Path | Purpose |
|---|---|
| `app.py` | Application entry point |
| `START_WINDOWS.bat` | Windows setup and launch helper |
| `web/` | Local browser interface |
| `lidguard/` | Inference, state handling, HTTP service, optional Pi capture |
| `models/` | JSON model and data-use notice |
| `train_baseline.py` | Reproducible baseline training |
| `tests/` | Meaningful software checks |
| `results/` | Evaluation, provenance manifest, validation outputs |
| `reports/` | Previously reported Orange results, separated from the new baseline |
| `docs/` | Arabic setup, submission, filming, and scientific references |

## Data and reuse

RT-BENE is attributed to Kevin Cortacero, Tobias Fischer and Yiannis Demiris (2019). Its source explicitly uses **CC BY-NC-SA 4.0** and prohibits commercial use. Preserve `models/NOTICE.txt` and consult the [original dataset page](https://zenodo.org/records/3685316) before reuse. This prototype is for research evaluation. Do not infer commercial permission for the trained model from the availability of this repository.

The separately supplied PopEYE NIR archive is **not used by this RGB model**. Its locally labeled partial-opening subset is not a verified clinical ground truth. Dataset permissions, image labeling, and future commercial development need their own review.

No general open-source license is assigned here to the team's earlier work, branding, photographs, or supplied materials. The team controls its repository and submission. No raw patient data or credentials are needed to operate this demo.

## Next validation steps

1. Run and record the actual camera and Raspberry Pi integration, including failure cases.
2. Collect consented, separately labeled development and test observations under the intended imaging conditions, with people separated between splits.
3. Define partial opening and corneal visibility with clinical collaborators, then evaluate those outputs separately from OPEN/CLOSED image classification.
4. Assess missing-eye detection, dressings and occlusion, false alerts, latency, and practical positioning.
5. Evaluate NIR illumination and its safety before eye-directed use; then validate NIR data independently.
6. Plan usability and prospective clinical evaluation with the required institutional approvals.

References and the limits of each source are in [docs/REFERENCES.md](docs/REFERENCES.md).
