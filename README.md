# SynGrid v4.0 — Generalized Synchronic Web Analyzer

**Production-Grade Power System Anomaly Detection with Synchronic Web Architecture and PyPower Integration**


---

## Overview

SynGrid is a generalized, open-source Python platform implementing the Synchronic Web (SW) architecture — developed at Sandia National Laboratories — for distributed anomaly detection and cryptographic provenance across arbitrary IEEE test systems.

**What's new in v4.0** (compared to v3.0):

| Feature | v3.0 | v4.0 |
|---|---|---|
| Network topology | Hardcoded 24-node IEEE 39-Bus | Dynamic from PyPower |
| Supported cases | IEEE 39-Bus only | 7 IEEE cases (14, 24, 30, 39, 57, 118, 300-bus) |
| Measurements | Random noise | Real AC power flow results via PyPower |
| Anomaly thresholds | Fixed per bus | Derived from case data |
| Node count | Fixed 24 | Scales automatically to loaded case |
| Byzantine tolerance *f* | Fixed 7 | Auto-computed: ⌊(n−1)/3⌋ |
| Case switching | Not supported | Runtime hot-swap via dropdown |

The system consists of three source files:

- **`synchronic_web_enhanced_v2.py`** — The GUI application (Tkinter + Matplotlib) with five tabs: Main Control, Network Monitor, Anomaly Detection, Consensus Viewer, and Performance Metrics.
- **`pypower_bridge.py`** *(new in v4.0)* — The generalization layer that dynamically loads any PyPower case, runs AC power flow, extracts per-bus measurements, performs physics-based anomaly detection, and provides plot data helpers. Includes a NumPy ≥ 2.0 compatibility shim.
- **`Real_SW.py`** — The backend engine implementing the full SW protocol stack: Merkle tree construction, Byzantine consensus (PBFT-style), RSA-2048 cryptographic operations, and WebSocket peer-to-peer communication.

## Repository Contents

```
├── synchronic_web_enhanced_v2.py   # Main GUI application (v4.0)
├── pypower_bridge.py               # PyPower integration bridge (NEW)
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
- **Display**: 1600×1000 resolution or higher recommended

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Mmassaoudi-cell/SynGrid.git
cd SynGrid
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

## Supported IEEE Test Cases

| Case | Buses | Generators | Branches | SW Nodes (approx.) | *f* / *q* |
|---|---|---|---|---|---|
| IEEE 14-Bus | 14 | 5 | 20 | ~16 | 5 / 11 |
| IEEE 24-Bus RTS | 24 | 33 | 38 | ~39 | 12 / 25 |
| IEEE 30-Bus | 30 | 6 | 41 | ~28 | 9 / 19 |
| IEEE 39-Bus (default) | 39 | 10 | 46 | ~33 | 10 / 21 |
| IEEE 57-Bus | 57 | 7 | 80 | ~50 | 16 / 33 |
| IEEE 118-Bus | 118 | 54 | 186 | ~120 | 39 / 79 |
| IEEE 300-Bus | 300 | 69 | 411 | ~260 | 86 / 173 |

Byzantine tolerance *f* = ⌊(n−1)/3⌋ and consensus quorum *q* = 2*f*+1 are auto-computed from the loaded case.

## Application Guide

### Tab 1 — Main Control

- **Power System Case selector** *(new in v4.0)*: Dropdown to select any IEEE test case. Parameters auto-update from PyPower results.
- **SW Network Configuration**: Total SW Nodes, Byzantine tolerance (*f*), consensus quorum (2*f*+1), and cryptographic security level — all auto-filled when a case is selected.
- **Initialize SW Network**: Creates and registers SW nodes dynamically from power flow results — one Control Center on the slack bus, one Generator node per generator bus, one Substation node per load bus, and Anomaly Detector nodes at a ratio of 1 per 8 power nodes.
- **Start / Stop Monitoring**: Activates real-time monitoring with live metric updates.
- **Run Real_SW.py**: Launches the backend engine in a background thread.
- **System Log**: Timestamped, color-coded log with filtering by level (Info, Warning, Error, Debug).

### Tab 2 — Network Monitor

- Real-time Matplotlib visualization of the network topology showing generators (red), substations (blue), and anomaly detectors (green) with interconnection lines.
- Topology scales dynamically to the loaded case (from 14-bus to 300-bus).
- Falls back to a text-based layout when Matplotlib is not available.

### Tab 3 — Anomaly Detection

- Four synchronized plots: **Voltage Monitoring** (per-unit with threshold bands), **Frequency Monitoring** (Hz with 59.5–60.5 Hz band), **Power Flow** (MW active power from PyPower), and **Cumulative Anomaly Count**.
- When PyPower is available, all traces are driven by real AC power flow solutions.
- Physics-based detection modes:
  - **Threshold violations**: Voltage V ∉ [0.94, 1.06] p.u., frequency f ∉ [59.5, 60.5] Hz
  - **Generator power limits**: P_gen ∉ [P_min, P_max] from case data
  - **Temporal consistency**: Sliding window (50 samples) detects sudden voltage changes > 10% of baseline
  - **Kirchhoff power balance**: System-wide |P_gen − P_load| / P_load > 5%

### Tab 4 — Consensus Viewer

- **Consensus Time Performance**: Tracks how long each Byzantine consensus round takes relative to the SLA limit.
- **Vote Distribution**: Pie chart showing Agree / Disagree / Byzantine vote proportions in real time.
- Buttons to start/stop consensus and to simulate Byzantine fault scenarios.

### Tab 5 — Performance

- Four real-time performance charts: **CPU Usage (%)**, **Memory Usage (%)**, **Network Latency (ms)**, and **Network Throughput (msgs/sec)**, each with warning thresholds.
- Metrics can be reset at any time.

### Menu Bar

| Menu | Item | Description |
|---|---|---|
| File | New Configuration | Reset to default parameters |
| File | Open Configuration | Load a JSON configuration file |
| File | Save Configuration | Export current parameters to JSON |
| File | Export Report | Generate a PDF or text report |
| Tools | Network Diagnostic | Run power balance checks (PyPower-driven) |
| Tools | Performance Test | Execute a performance benchmark |
| Tools | Security Audit | Validate cryptographic configuration |
| Help | User Guide | In-app usage documentation |
| Help | IEEE Standards | Referenced IEEE standards information |
| Help | About | Developer and application information |

## Architecture

SynGrid v4.0 is organized in five layers:

1. **Application Layer** — GUI dashboards (5 tabs), logging, configuration management, and report export.
2. **Power System Layer** *(new in v4.0)* — `PowerSystemBridge` class providing dynamic case loading, perturbed power flow simulation via PyPower's `runpf()`, measurement extraction, and physics-based anomaly detection.
3. **Synchronic Web / Provenance Layer** — Merkle tree management (`SynchronicMerkleTree`), cryptographic entanglement of node states via `SWExpression` objects, and provenance chain tracking through `SWStateMachine`.
4. **Consensus Layer** — PBFT-style three-phase voting protocol (`ByzantineConsensus`) with configurable quorum *q* = 2*f*+1.
5. **Crypto & Network Layer** — RSA-2048 signing/verification (`SWCryptographicSecurity`), SHA-256 hashing, and asynchronous WebSocket communication (`SWNetworkLayer`) with simulation fallbacks.

**Anomaly Detection** spans Layers 2–4 as a cross-cutting concern, combining physics-based checks from the bridge with provenance-based validation from the SW layer and consensus-based cross-node verification.

A key design principle is **graceful degradation**: if PyPower is unavailable, the GUI falls back to random data generation; if optional dependencies (Matplotlib, websockets, cryptography) are missing, integrated fallbacks ensure the software runs on a minimal Python installation with only NumPy required.

## Dependency Details

| Package | Used By | Purpose | Required? |
|---|---|---|---|
| `matplotlib` | GUI | Real-time plots and network topology | Yes* |
| `numpy` | GUI + Bridge + Backend | Numerical computation | Yes |
| `Pillow` | GUI | Logo/icon image loading | Yes* |
| `pypower` | Bridge | AC power flow solver (IEEE test cases) | Yes** |
| `networkx` | Backend | Graph analysis of power network | No*** |
| `websockets` | Backend | WebSocket network communication | No*** |
| `cryptography` | Backend | RSA-2048 signing and verification | No*** |
| `psutil` | Backend | System resource monitoring | No*** |

\* The GUI gracefully degrades to text-based displays if `matplotlib` or `Pillow` are unavailable.  
\** Without PyPower, the GUI falls back to simulated random data (IEEE 39-Bus only).  
\*** The backend provides built-in fallback implementations when optional packages are missing.

## Quick Start Example

```python
from pypower_bridge import PowerSystemBridge, CASES

# Initialize with IEEE 39-Bus (default)
bridge = PowerSystemBridge('case39')

# Hot-swap to IEEE 118-Bus at runtime
bridge.switch_case('case118')

# Build SW node list with auto-computed f, q
nodes, n, f, q = bridge.build_node_list()
# n ≈ 120, f = 39, q = 79 for IEEE 118-Bus

# Run one perturbed power flow step
net_entry, anomalies, measurements = bridge.step(
    noise=0.02,
    attack_overrides={31: {'voltage': 1.30}}
)

# Get case summary from power flow results
summary = bridge.get_case_summary()
# {'num_buses': 118, 'num_gens': 54, ...}
```

## Synchronic Web Architecture

This application implements the Synchronic Web paradigm as described by Sandia National Laboratories:

- **Merkle Tree Entanglement** — Nodes share cryptographic state via binary hash trees, enabling tamper-evident data provenance with O(log n) verification.
- **Byzantine Fault Tolerance** — The consensus protocol tolerates up to *f* < *n*/3 faulty or malicious nodes using a PBFT-style quorum-based voting mechanism.
- **Cryptographic Provenance** — RSA-2048 digital signatures combined with SHA-256 hashing provide data integrity and non-repudiation.
- **Generalized Power System Integration** *(new in v4.0)* — Dynamic loading of any PyPower IEEE test case replaces hardcoded topology, with all parameters derived from AC power flow solutions.

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError: No module named 'tkinter'` | Install tkinter for your OS (see Installation notes above) |
| `ModuleNotFoundError: No module named 'pypower'` | Run `pip install pypower` — the GUI will fall back to simulated data without it |
| Plots not displaying | Ensure `matplotlib` and `numpy` are installed: `pip install matplotlib numpy` |
| Logo/icon not showing | Verify `logo.png` and `logo.ico` are in the same directory as the script |
| `Real_SW.py` not found | Keep `Real_SW.py` in the same directory as the GUI script |
| `pypower_bridge.py` not found | Keep `pypower_bridge.py` in the same directory as the GUI script |
| Port conflicts in enhanced mode | The backend auto-discovers available ports; close conflicting services if needed |
| NumPy ≥ 2.0 compatibility errors | `pypower_bridge.py` includes an automatic compatibility shim — no action needed |

## IEEE Standards Reference

- **IEEE Test Systems** (14, 24, 30, 39, 57, 118, 300-bus) — Standard benchmarks for power system studies
- **IEEE 3333** — Synchronic Web Architecture
- **IEEE C37.118** — Synchrophasor measurement and communication
- **IEEE 1547** — Distributed energy resource interconnection
- **IEEE 2030** — Smart grid interoperability

## Citation

If you use SynGrid in your research, please cite:

```bibtex
@article{massaoudi2026syngrid,
  title={SynGrid: A Generalized Distributed Anomaly Detection Platform for Power Systems Based on Synchronic Web Architecture},
  author={Massaoudi, Mohamed and Haque, Khandaker Akramul and Davis, Katherine and Cordeiro, Patricia and Chavez, Adrian and Hossain-McKenzie, Shamina},
  journal={SoftwareX},
  year={2026},
  publisher={Elsevier}
}
```

## License

MIT License — Copyright © 2025 Texas A&M University. See [LICENSE](LICENSE) for details.

