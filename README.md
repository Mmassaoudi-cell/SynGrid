# IEEE Synchronic Web Analyzer v3.0

**Production-Grade IEEE 39-Bus Anomaly Detection with Synchronic Web Architecture**

Developed by **Mohamed Massaoudi, PhD** — Senior Research Engineer & Lab Manager  
Electrical and Computer Engineering, Texas A&M University  
Resilient Energy Systems Lab (RESLab) | TEES Smart Grid Center

---

## Overview

The IEEE Synchronic Web Analyzer is a desktop application that provides comprehensive monitoring and analysis of the IEEE 39-Bus (New England) power system using the Synchronic Web architecture developed at Sandia National Laboratories. It combines real-time anomaly detection, Byzantine fault-tolerant consensus, and cryptographic provenance tracking into a unified graphical interface.

The system consists of two main components:

- **`synchronic_web_enhanced_v2.py`** — The GUI application built with Tkinter and Matplotlib, providing real-time visualization of network topology, anomaly detection, consensus processes, and performance metrics.
- **`Real_SW.py`** — The backend computational engine implementing the full Synchronic Web protocol with Merkle tree entanglement, Byzantine fault tolerance, RSA-2048 cryptographic security, and WebSocket network communication.

## Repository Contents

```
├── synchronic_web_enhanced_v2.py   # Main GUI application
├── Real_SW.py                      # Backend Synchronic Web engine
├── logo.png                        # Application logo (header display)
├── logo.ico                        # Application icon (window taskbar)
├── requirements.txt                # Python package dependencies
└── README.md                       # This file
```

## System Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows 10/11, macOS, or Linux
- **RAM**: 4 GB minimum (8 GB recommended)
- **Display**: 1600x1000 resolution or higher recommended

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-folder>
```

### 2. (Recommended) Create a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `tkinter` ships with the standard Python distribution on Windows and macOS. On some Linux distributions you may need to install it separately:
> ```bash
> # Debian/Ubuntu
> sudo apt-get install python3-tk
> # Fedora
> sudo dnf install python3-tkinter
> ```

## Running the Application

### Launch the GUI

```bash
python synchronic_web_enhanced_v2.py
```

This opens the main analyzer window with five interactive tabs and a menu bar.

### Launch the Backend Engine (Optional)

The backend engine can be run independently for headless analysis:

```bash
# Basic mode (standard library + numpy only)
python Real_SW.py

# Enhanced mode (full cryptographic and network features)
python Real_SW.py --enhanced
```

You can also launch it from within the GUI by clicking **"Run Real_SW.py"** on the Main Control tab.

## Application Guide

### Tab 1 — Main Control

- **SW Network Configuration**: Set the number of nodes, Byzantine tolerance parameter (f), consensus quorum size (2f+1), and cryptographic security level.
- **Initialize SW Network**: Creates and registers all 24 Synchronic Web nodes (10 generators, 10 substations, 3 anomaly detectors, 1 control center) mapped to the IEEE 39-Bus topology.
- **Start / Stop Monitoring**: Activates real-time monitoring with live metric updates (active nodes, anomalies detected, consensus rounds, network latency).
- **Run Real_SW.py**: Launches the backend engine in a background thread with output captured in the system log.
- **System Log**: Timestamped, color-coded log with filtering by level (Info, Warning, Error, Debug). Logs can be saved to file.

### Tab 2 — Network Monitor

- Real-time Matplotlib visualization of the IEEE 39-Bus network topology showing generators (red), substations (blue), and anomaly detectors (green) with interconnection lines.
- Falls back to a text-based layout when Matplotlib is not available.

### Tab 3 — Anomaly Detection

- Four synchronized plots: **Voltage Monitoring** (per-unit with upper/lower limits), **Frequency Monitoring** (Hz with 59.5–60.5 Hz band), **Power Flow** (MW active power), and **Cumulative Anomaly Count**.
- Buttons to start/stop detection and to inject simulated anomalies of various types and severities.

### Tab 4 — Consensus Viewer

- **Consensus Time Performance**: Tracks how long each Byzantine consensus round takes relative to the SLA limit.
- **Vote Distribution**: Pie chart showing Agree / Disagree / Byzantine vote proportions in real time.
- Buttons to start/stop consensus and to simulate Byzantine fault scenarios.

### Tab 5 — Performance

- Four real-time performance charts: **CPU Usage (%)**, **Memory Usage (%)**, **Network Latency (ms)**, and **Network Throughput (msgs/sec)**, each with warning thresholds.
- Metrics can be reset at any time.

### Menu Bar

| Menu   | Item                | Description                                |
|--------|---------------------|--------------------------------------------|
| File   | New Configuration   | Reset to default parameters                |
| File   | Open Configuration  | Load a JSON configuration file             |
| File   | Save Configuration  | Export current parameters to JSON           |
| File   | Export Report       | Generate a PDF or text report              |
| Tools  | Network Diagnostic  | Run network connectivity checks            |
| Tools  | Performance Test    | Execute a performance benchmark            |
| Tools  | Security Audit      | Validate cryptographic configuration       |
| Help   | User Guide          | In-app usage documentation                 |
| Help   | IEEE Standards      | Referenced IEEE standards information       |
| Help   | About               | Developer and application information       |

## Dependency Details

| Package        | Used By           | Purpose                                   | Required? |
|----------------|-------------------|-------------------------------------------|-----------|
| `matplotlib`   | GUI               | Real-time plots and network topology       | Yes*      |
| `numpy`        | GUI + Backend     | Numerical computation                      | Yes       |
| `Pillow`       | GUI               | Logo/icon image loading                    | Yes*      |
| `networkx`     | Backend           | Graph analysis of power network            | No**      |
| `websockets`   | Backend           | WebSocket network communication            | No**      |
| `cryptography` | Backend           | RSA-2048 signing and verification          | No**      |
| `psutil`       | Backend           | System resource monitoring                 | No**      |

\* The GUI gracefully degrades to text-based displays if `matplotlib` or `Pillow` are unavailable.  
\** The backend provides built-in fallback implementations when optional packages are missing.

## Synchronic Web Architecture

This application implements the Synchronic Web paradigm as described by Sandia National Laboratories:

- **Merkle Tree Entanglement** — Nodes share cryptographic state via binary hash trees, enabling tamper-evident data provenance.
- **Byzantine Fault Tolerance** — The consensus protocol tolerates up to f < n/3 faulty or malicious nodes using a quorum-based voting mechanism.
- **Cryptographic Provenance** — RSA-2048 digital signatures combined with SHA-256 hashing provide data integrity and non-repudiation.
- **IEEE 39-Bus Integration** — The 10-generator, 39-bus New England test system serves as the physical model for voltage, frequency, and power flow monitoring.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'tkinter'` | Install tkinter for your OS (see Installation notes above) |
| Plots not displaying | Ensure `matplotlib` and `numpy` are installed: `pip install matplotlib numpy` |
| Logo/icon not showing | Verify `logo.png` and `logo.ico` are in the same directory as the script |
| `Real_SW.py` not found | Keep `Real_SW.py` in the same directory as the GUI script |
| Port conflicts in enhanced mode | The backend auto-discovers available ports; close conflicting services if needed |

## IEEE Standards Reference

- **IEEE 39-Bus Test System** — Standard benchmark for power system stability studies
- **IEEE C37.118** — Synchrophasor measurement and communication
- **IEEE 1547** — Distributed energy resource interconnection
- **IEEE 2030** — Smart grid interoperability

## License

Copyright 2025 Texas A&M University. All Rights Reserved.
