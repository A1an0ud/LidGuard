# Raspberry Pi camera setup

LidGuard includes an optional Picamera2 adapter for a supported Raspberry Pi CSI camera. Physical hardware validation has not been recorded for this release.

## Requirements

- A Raspberry Pi running a compatible Raspberry Pi OS.
- A supported CSI camera and the correct ribbon cable for the board.
- A suitable power supply and an installed operating system.
- A local display, or an established SSH connection with port forwarding.

The camera model, sensor, and IR-filter configuration must be identified from the actual hardware. A resolution label such as 5 MP does not establish NoIR capability.

## Connect and verify the camera

Shut down the Raspberry Pi and disconnect power before connecting or adjusting the CSI ribbon cable. Follow the [official installation guide](https://www.raspberrypi.com/documentation/accessories/camera-software.html) for the board's connector and cable orientation.

Install the system-managed packages:

```bash
sudo apt update
sudo apt install python3-numpy python3-pil python3-picamera2 rpicam-apps
```

Verify detection and capture:

```bash
rpicam-hello --list-cameras
rpicam-still -n -o test.jpg
```

Confirm that a camera is listed and that `test.jpg` contains a current image. This diagnostic command deliberately saves a test image; the LidGuard application's frame processing does not save camera images.

## Run LidGuard locally

From the repository directory:

```bash
/usr/bin/python3 app.py --open-browser
```

Open **http://localhost:8765**, select **Raspberry Pi camera**, and press **Start camera**. Select one eye manually and confirm its visibility. Clear the confirmation if the eye leaves the selected region.

**Computer camera** requests the browser's webcam. When using a Windows browser to access a Pi-hosted server, that source would use the Windows webcam, not the Pi CSI adapter.

Picamera2 and libcamera should remain managed by Raspberry Pi OS. If a virtual environment is used on Pi, create it with `--system-site-packages` so it can access the OS camera packages. The `/usr/bin/python3` command above avoids this additional setup.

## Access from Windows through SSH

The application binds to localhost. With SSH already configured, open PowerShell on Windows and replace the example user and hostname with the Pi's actual values:

```powershell
ssh -L 8765:127.0.0.1:8765 pi-user@pi-host.local
```

In the resulting Pi terminal, navigate to the project directory and start the server:

```bash
/usr/bin/python3 app.py
```

Keep the SSH session open. Open **http://localhost:8765** in the Windows browser and select **Raspberry Pi camera**. Do not start a second local LidGuard server on port 8765 at the same time.

## Troubleshooting and validation

If the camera is not detected, power down before checking connectors and cable seating. Identify third-party sensors and follow their manufacturer's configuration instructions. This adapter targets the modern Picamera2/libcamera stack.

Record the board, sensor model, OS version, lighting, capture result, and observed classification errors when evaluating the integration. A working stream does not establish classification accuracy. Missing operator confirmation and heuristic image-quality rejection are not validated automatic eye-presence detection.

Use ordinary room light for initial evaluation. NIR performance and the safety of eye-directed IR illumination require separate validation. The binary model does not establish corneal exposure or clinical protection.

See [the main README](../README.md) for inference behavior and [the references](REFERENCES.md) for primary engineering and clinical sources.
