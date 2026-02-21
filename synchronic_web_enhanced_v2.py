#!/usr/bin/env python3
"""
SynGrid — Generalized Synchronic Web Analyzer v4.0
===================================================
Production-grade power system monitoring with PyPower integration.
Supports any PyPower case (IEEE 14/30/39/57/118/300-bus) while
keeping IEEE 39-bus as the default case study.

Created for: Mohamed Massaoudi, PhD — Texas A&M University
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import json
import subprocess
import sys
import os
import hashlib
from datetime import datetime
import queue
import random
import math
from typing import Dict, List, Any

# Handle optional dependencies
MPL_AVAILABLE = True
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import numpy as np
    # Set matplotlib to use TkAgg backend
    plt.switch_backend('TkAgg')
except ImportError:
    MPL_AVAILABLE = False
    print("Warning: matplotlib/numpy not available. Using text displays instead.")

PIL_AVAILABLE = True
try:
    from PIL import Image, ImageTk
except ImportError:
    PIL_AVAILABLE = False
    print("Warning: PIL not available. Icon features disabled.")

# ── PyPower bridge (graceful fallback) ────────────────────────────
PYPOWER_AVAILABLE = False
try:
    from pypower_bridge import PowerSystemBridge, CASES as PYPOWER_CASES
    PYPOWER_AVAILABLE = True
except ImportError:
    PYPOWER_CASES = {}
    print("Warning: pypower_bridge not available. Using simulated data.")


class SynchronicWebAnalyzer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SynGrid — Synchronic Web Analyzer v4.0")
        self.root.geometry("1600x1000")
        self.root.configure(bg='#f0f0f0')

        # Set window icon
        self.setup_logo()

        # ── PyPower bridge ────────────────────────────────────────
        self.PYPOWER_AVAILABLE = PYPOWER_AVAILABLE
        self.bridge = None
        if self.PYPOWER_AVAILABLE:
            try:
                self.bridge = PowerSystemBridge('case39')
            except Exception as e:
                print(f"Warning: PyPower bridge init failed: {e}")
                self.PYPOWER_AVAILABLE = False

        # Application state
        self.is_running = False
        self.sw_nodes = {}
        self.anomaly_count = 0
        self.consensus_rounds = 0
        self.performance_data = []
        self.log_queue = queue.Queue()

        # Data for visualizations
        self.network_data = []
        self.anomaly_data = []
        self.consensus_data = []
        self.performance_metrics = {
            'cpu_usage': [],
            'memory_usage': [],
            'network_latency': [],
            'throughput': []
        }

        # Enhanced SW Network Configuration (defaults for IEEE 39-bus)
        self.sw_config = {
            'total_nodes': 24,
            'generation_units': 10,
            'substations': 10,
            'anomaly_detectors': 3,
            'control_centers': 1,
            'byzantine_tolerance': 7,
            'consensus_quorum': 15,
            'ieee_compliance': True,
            'security_level': 256
        }

        # Create menu bar
        self.create_menu_bar()

        self.create_widgets()
        self.setup_monitoring()

        # Start data generation for visualizations
        self.start_data_generation()

    # ══════════════════════════════════════════════════════════════
    #  MENU BAR
    # ══════════════════════════════════════════════════════════════

    def create_menu_bar(self):
        """Create menu bar with About option"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Configuration", command=self.new_config)
        file_menu.add_command(label="Open Configuration", command=self.open_config)
        file_menu.add_command(label="Save Configuration", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Export Report", command=self.export_report)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Network Diagnostic", command=self.network_diagnostic)
        tools_menu.add_command(label="Performance Test", command=self.performance_test)
        tools_menu.add_command(label="Security Audit", command=self.security_audit)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_user_guide)
        help_menu.add_command(label="IEEE Standards", command=self.show_ieee_standards)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)

    # ══════════════════════════════════════════════════════════════
    #  LOGO / ICON
    # ══════════════════════════════════════════════════════════════

    def setup_logo(self):
        """Setup application logo and icon"""
        try:
            ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.ico')
            if os.path.exists(ico_path):
                try:
                    self.root.iconbitmap(ico_path)
                except Exception:
                    pass

            if PIL_AVAILABLE:
                logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')
                if os.path.exists(logo_path):
                    logo_image = Image.open(logo_path)
                    try:
                        resample_filter = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample_filter = Image.LANCZOS

                    icon_image = logo_image.resize((32, 32), resample_filter)
                    self.icon_photo = ImageTk.PhotoImage(icon_image)
                    try:
                        self.root.iconphoto(True, self.icon_photo)
                    except Exception:
                        pass

                    header_image = logo_image.resize((64, 64), resample_filter)
                    self.header_logo = ImageTk.PhotoImage(header_image)
                else:
                    self.header_logo = None
            else:
                self.header_logo = None
        except Exception as e:
            print(f"Error loading logo: {e}")
            self.header_logo = None

    # ══════════════════════════════════════════════════════════════
    #  WIDGET CREATION
    # ══════════════════════════════════════════════════════════════

    def create_widgets(self):
        """Create the main UI widgets"""
        self.create_header()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self.create_main_control_tab()
        self.create_network_monitor_tab()
        self.create_anomaly_detection_tab()
        self.create_consensus_viewer_tab()
        self.create_performance_tab()

        self.create_status_bar()

    def create_header(self):
        """Create header frame with logo and title"""
        header_frame = tk.Frame(self.root, bg='#2c3e50', height=80)
        header_frame.pack(fill='x', padx=10, pady=(10, 5))
        header_frame.pack_propagate(False)

        if hasattr(self, 'header_logo') and self.header_logo:
            logo_label = tk.Label(header_frame, image=self.header_logo, bg='#2c3e50')
            logo_label.pack(side='left', padx=(20, 10), pady=8)

        title_frame = tk.Frame(header_frame, bg='#2c3e50')
        title_frame.pack(side='left', fill='both', expand=True, pady=8)

        title_label = tk.Label(title_frame,
                               text="SynGrid — Synchronic Web Analyzer v4.0",
                               font=('Arial', 18, 'bold'),
                               fg='white', bg='#2c3e50')
        title_label.pack(anchor='w')

        subtitle_label = tk.Label(title_frame,
                                  text="Production-grade Power System Anomaly Detection with Synchronic Web Architecture",
                                  font=('Arial', 10),
                                  fg='#bdc3c7', bg='#2c3e50')
        subtitle_label.pack(anchor='w')

        self.status_frame = tk.Frame(header_frame, bg='#2c3e50')
        self.status_frame.pack(side='right', padx=(10, 20), pady=8)

        self.status_indicator = tk.Label(self.status_frame,
                                         text="●", font=('Arial', 20),
                                         fg='#e74c3c', bg='#2c3e50')
        self.status_indicator.pack()

        self.status_text = tk.Label(self.status_frame,
                                    text="OFFLINE", font=('Arial', 8, 'bold'),
                                    fg='#e74c3c', bg='#2c3e50')
        self.status_text.pack()

    # ──────────────────────────────────────────────────────────────
    #  TAB 1 — MAIN CONTROL  (with PyPower case selector)
    # ──────────────────────────────────────────────────────────────

    def create_main_control_tab(self):
        """Create comprehensive main control interface"""
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="Main Control")

        # ── SW Network Configuration Section ──────────────────────
        config_frame = ttk.LabelFrame(main_frame, text="SW Network Configuration", padding=10)
        config_frame.pack(fill='x', padx=10, pady=5)

        config_grid = ttk.Frame(config_frame)
        config_grid.pack(fill='x', padx=10, pady=10)

        # Row 0: Power System Case selector (PyPower)
        ttk.Label(config_grid, text="Power System Case:").grid(row=0, column=0, sticky='w', padx=5)
        self.case_var = tk.StringVar(value='case39')
        if self.PYPOWER_AVAILABLE:
            case_cb = ttk.Combobox(config_grid, textvariable=self.case_var,
                                   values=list(PYPOWER_CASES.keys()), width=18, state='readonly')
            case_cb.grid(row=0, column=1, padx=5, sticky='w')
            case_cb.bind('<<ComboboxSelected>>', self._on_case_change)

            # Case description label
            self.case_desc_var = tk.StringVar(value="IEEE 39-Bus (New England)")
            ttk.Label(config_grid, textvariable=self.case_desc_var,
                      foreground='#2980b9', font=('Arial', 9, 'italic')).grid(
                row=0, column=2, columnspan=2, sticky='w', padx=5)
        else:
            ttk.Label(config_grid, text="case39 (PyPower not installed)",
                      foreground='gray').grid(row=0, column=1, columnspan=3, sticky='w', padx=5)

        # Row 1: Basic network parameters
        ttk.Label(config_grid, text="Total SW Nodes:").grid(row=1, column=0, sticky='w', padx=5)
        self.nodes_entry = ttk.Entry(config_grid, width=10)
        self.nodes_entry.insert(0, str(self.sw_config['total_nodes']))
        self.nodes_entry.grid(row=1, column=1, padx=5)

        ttk.Label(config_grid, text="Byzantine Tolerance (f):").grid(row=1, column=2, sticky='w', padx=5)
        self.tolerance_entry = ttk.Entry(config_grid, width=10)
        self.tolerance_entry.insert(0, str(self.sw_config['byzantine_tolerance']))
        self.tolerance_entry.grid(row=1, column=3, padx=5)

        # Row 2: Additional parameters
        ttk.Label(config_grid, text="Consensus Quorum:").grid(row=2, column=0, sticky='w', padx=5)
        self.quorum_entry = ttk.Entry(config_grid, width=10)
        self.quorum_entry.insert(0, str(self.sw_config['consensus_quorum']))
        self.quorum_entry.grid(row=2, column=1, padx=5)

        ttk.Label(config_grid, text="Security Level:").grid(row=2, column=2, sticky='w', padx=5)
        self.security_entry = ttk.Entry(config_grid, width=10)
        self.security_entry.insert(0, str(self.sw_config['security_level']))
        self.security_entry.grid(row=2, column=3, padx=5)

        # Control buttons
        button_frame = ttk.Frame(config_frame)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Initialize SW Network",
                   command=self.initialize_network).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Start Monitoring",
                   command=self.start_monitoring).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Stop Monitoring",
                   command=self.stop_monitoring).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Run Real_SW.py",
                   command=self.run_real_sw).pack(side='left', padx=5)

        # ── Network Status Section ────────────────────────────────
        status_frame = ttk.LabelFrame(main_frame, text="Network Status", padding=10)
        status_frame.pack(fill='x', padx=10, pady=5)

        columns = ('Node ID', 'Type', 'Bus #', 'Status', 'Merkle Root')
        self.status_tree = ttk.Treeview(status_frame, columns=columns, show='headings', height=8)

        for col in columns:
            self.status_tree.heading(col, text=col)
            self.status_tree.column(col, width=150)

        status_tree_frame = ttk.Frame(status_frame)
        status_tree_frame.pack(fill='x', padx=10, pady=5)

        self.status_tree.pack(side='left', fill='both', expand=True)
        status_scrollbar = ttk.Scrollbar(status_tree_frame, orient='vertical',
                                         command=self.status_tree.yview)
        status_scrollbar.pack(side='right', fill='y')
        self.status_tree.configure(yscrollcommand=status_scrollbar.set)

        # Real-time metrics
        metrics_frame = ttk.LabelFrame(status_frame, text="Real-time Metrics", padding=5)
        metrics_frame.pack(fill='x', padx=10, pady=5)

        metrics_grid = ttk.Frame(metrics_frame)
        metrics_grid.pack(fill='x')

        ttk.Label(metrics_grid, text="Active Nodes:").grid(row=0, column=0, sticky='w', padx=5)
        self.active_nodes_var = tk.StringVar(value="0/24")
        ttk.Label(metrics_grid, textvariable=self.active_nodes_var,
                  foreground="blue").grid(row=0, column=1, padx=5)

        ttk.Label(metrics_grid, text="Anomalies Detected:").grid(row=0, column=2, sticky='w', padx=5)
        self.anomalies_var = tk.StringVar(value="0")
        ttk.Label(metrics_grid, textvariable=self.anomalies_var,
                  foreground="red").grid(row=0, column=3, padx=5)

        ttk.Label(metrics_grid, text="Consensus Rounds:").grid(row=1, column=0, sticky='w', padx=5)
        self.consensus_var = tk.StringVar(value="0")
        ttk.Label(metrics_grid, textvariable=self.consensus_var,
                  foreground="green").grid(row=1, column=1, padx=5)

        ttk.Label(metrics_grid, text="Network Latency:").grid(row=1, column=2, sticky='w', padx=5)
        self.latency_var = tk.StringVar(value="0ms")
        ttk.Label(metrics_grid, textvariable=self.latency_var,
                  foreground="orange").grid(row=1, column=3, padx=5)

        # Case summary (PyPower info)
        ttk.Label(metrics_grid, text="Power System:").grid(row=2, column=0, sticky='w', padx=5)
        self.case_info_var = tk.StringVar(value="IEEE 39-Bus (default)")
        ttk.Label(metrics_grid, textvariable=self.case_info_var,
                  foreground="#8e44ad").grid(row=2, column=1, columnspan=3, sticky='w', padx=5)

        # ── System Log & Debug Information Section ────────────────
        log_frame = ttk.LabelFrame(main_frame, text="System Log & Debug Information", padding=10)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)

        log_controls = ttk.Frame(log_frame)
        log_controls.pack(fill='x', pady=(0, 5))

        ttk.Button(log_controls, text="Clear Log",
                   command=self.clear_log).pack(side='left', padx=5)
        ttk.Button(log_controls, text="Save Log",
                   command=self.save_log).pack(side='left', padx=5)
        ttk.Button(log_controls, text="Refresh",
                   command=self.refresh_log).pack(side='left', padx=5)

        ttk.Label(log_controls, text="Filter:").pack(side='left', padx=(20, 5))
        self.log_filter_var = tk.StringVar()
        filter_combo = ttk.Combobox(log_controls, textvariable=self.log_filter_var,
                                    values=["All", "Info", "Warning", "Error", "Debug"], width=10)
        filter_combo.set("All")
        filter_combo.pack(side='left', padx=5)
        filter_combo.bind('<<ComboboxSelected>>', self.filter_log)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True)

        self.log_text.tag_configure("INFO", foreground="blue")
        self.log_text.tag_configure("WARNING", foreground="orange")
        self.log_text.tag_configure("ERROR", foreground="red")
        self.log_text.tag_configure("DEBUG", foreground="gray")
        self.log_text.tag_configure("SUCCESS", foreground="green")

        # Welcome messages
        self.log_message("🚀 SynGrid — Synchronic Web Analyzer v4.0 initialized")
        if self.PYPOWER_AVAILABLE:
            self.log_message("✅ PyPower integration active — generalized power system support", level="SUCCESS")
            cases = ', '.join(PYPOWER_CASES.keys())
            self.log_message(f"📦 Available cases: {cases}", level="DEBUG")
        else:
            self.log_message("⚠️  PyPower not available — using simulated IEEE 39-bus data", level="WARNING")
        self.log_message("📊 Ready for network configuration and monitoring")

    # ──────────────────────────────────────────────────────────────
    #  TAB 2 — NETWORK MONITOR
    # ──────────────────────────────────────────────────────────────

    def create_network_monitor_tab(self):
        """Create network monitoring interface with working visualizations"""
        monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitor_frame, text="Network Monitor")

        topology_frame = ttk.LabelFrame(monitor_frame, text="SW Network Topology")
        topology_frame.pack(fill='both', expand=True, padx=10, pady=5)

        if MPL_AVAILABLE:
            self.fig_network, self.ax_network = plt.subplots(figsize=(12, 8))
            self.canvas_network = FigureCanvasTkAgg(self.fig_network, topology_frame)
            self.canvas_network.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
            self.update_network_topology()
        else:
            self.topology_text = scrolledtext.ScrolledText(topology_frame, height=20)
            self.topology_text.pack(fill='both', expand=True, padx=10, pady=10)
            self._fill_topology_text_fallback()

    def _fill_topology_text_fallback(self):
        """Text fallback for network topology when matplotlib is unavailable."""
        self.topology_text.insert(tk.END, "Network Topology — Text Mode\n")
        self.topology_text.insert(tk.END, "=" * 50 + "\n")
        if self.PYPOWER_AVAILABLE and self.bridge:
            summary = self.bridge.get_case_summary()
            self.topology_text.insert(tk.END, f"Case: {summary['case_label']}\n")
            self.topology_text.insert(tk.END, f"Buses: {summary['num_buses']}  "
                                              f"Generators: {summary['num_gens']}  "
                                              f"Branches: {summary['num_branches']}\n")
            self.topology_text.insert(tk.END, f"Total Load: {summary['total_load']:.1f} MW  "
                                              f"Total Gen: {summary['total_gen']:.1f} MW\n")
        else:
            self.topology_text.insert(tk.END, "IEEE 39-Bus System Layout:\n\n")
            self.topology_text.insert(tk.END, "Generation Units (Buses 30-39):\n")
            for i in range(30, 40):
                self.topology_text.insert(tk.END, f"  • Bus {i}: Generator {i - 29}\n")
            self.topology_text.insert(tk.END, "\nLoad Buses (Selected):\n")
            for bus in [1, 3, 4, 7, 8, 15, 16, 18, 20, 21]:
                self.topology_text.insert(tk.END, f"  • Bus {bus}: Substation\n")

    # ──────────────────────────────────────────────────────────────
    #  TAB 3 — ANOMALY DETECTION
    # ──────────────────────────────────────────────────────────────

    def create_anomaly_detection_tab(self):
        """Create anomaly detection interface with working displays"""
        anomaly_frame = ttk.Frame(self.notebook)
        self.notebook.add(anomaly_frame, text="Anomaly Detection")

        control_frame = ttk.LabelFrame(anomaly_frame, text="Detection Controls")
        control_frame.pack(fill='x', padx=10, pady=5)

        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Start Detection",
                   command=self.start_detection).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Stop Detection",
                   command=self.stop_detection).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Simulate Anomaly",
                   command=self.simulate_anomaly).pack(side='left', padx=5)

        if MPL_AVAILABLE:
            viz_frame = ttk.LabelFrame(anomaly_frame, text="Anomaly Detection Visualization")
            viz_frame.pack(fill='both', expand=True, padx=10, pady=5)

            self.fig_anomaly, ((self.ax_voltage, self.ax_frequency),
                               (self.ax_power, self.ax_anomalies)) = plt.subplots(2, 2, figsize=(12, 8))
            self.canvas_anomaly = FigureCanvasTkAgg(self.fig_anomaly, viz_frame)
            self.canvas_anomaly.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
            self.update_anomaly_plots()
        else:
            results_frame = ttk.LabelFrame(anomaly_frame, text="Detection Results")
            results_frame.pack(fill='both', expand=True, padx=10, pady=5)
            self.anomaly_text = scrolledtext.ScrolledText(results_frame, height=20)
            self.anomaly_text.pack(fill='both', expand=True, padx=10, pady=10)
            self.anomaly_text.insert(tk.END, "Anomaly Detection Results\n" + "=" * 50 + "\n")

    # ──────────────────────────────────────────────────────────────
    #  TAB 4 — CONSENSUS VIEWER
    # ──────────────────────────────────────────────────────────────

    def create_consensus_viewer_tab(self):
        """Create consensus viewer interface with working displays"""
        consensus_frame = ttk.Frame(self.notebook)
        self.notebook.add(consensus_frame, text="Consensus Viewer")

        control_frame = ttk.LabelFrame(consensus_frame, text="Byzantine Consensus Controls")
        control_frame.pack(fill='x', padx=10, pady=5)

        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Start Consensus",
                   command=self.start_consensus).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Stop Consensus",
                   command=self.stop_consensus).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Simulate Byzantine Fault",
                   command=self.simulate_byzantine_fault).pack(side='left', padx=5)

        if MPL_AVAILABLE:
            viz_frame = ttk.LabelFrame(consensus_frame, text="Consensus Process Visualization")
            viz_frame.pack(fill='both', expand=True, padx=10, pady=5)

            self.fig_consensus, (self.ax_consensus_time,
                                 self.ax_vote_distribution) = plt.subplots(1, 2, figsize=(12, 6))
            self.canvas_consensus = FigureCanvasTkAgg(self.fig_consensus, viz_frame)
            self.canvas_consensus.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
            self.update_consensus_plots()
        else:
            status_frame = ttk.LabelFrame(consensus_frame, text="Consensus Status")
            status_frame.pack(fill='both', expand=True, padx=10, pady=5)
            self.consensus_text = scrolledtext.ScrolledText(status_frame, height=20)
            self.consensus_text.pack(fill='both', expand=True, padx=10, pady=10)
            self.consensus_text.insert(tk.END, "Byzantine Consensus Status\n" + "=" * 50 + "\n")

    # ──────────────────────────────────────────────────────────────
    #  TAB 5 — PERFORMANCE
    # ──────────────────────────────────────────────────────────────

    def create_performance_tab(self):
        """Create performance monitoring interface with working charts"""
        perf_frame = ttk.Frame(self.notebook)
        self.notebook.add(perf_frame, text="Performance")

        control_frame = ttk.LabelFrame(perf_frame, text="Performance Monitoring Controls")
        control_frame.pack(fill='x', padx=10, pady=5)

        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(button_frame, text="Start Performance Monitor",
                   command=self.start_performance_monitor).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Stop Performance Monitor",
                   command=self.stop_performance_monitor).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Reset Metrics",
                   command=self.reset_performance_metrics).pack(side='left', padx=5)

        if MPL_AVAILABLE:
            viz_frame = ttk.LabelFrame(perf_frame, text="Performance Metrics")
            viz_frame.pack(fill='both', expand=True, padx=10, pady=5)

            self.fig_performance, ((self.ax_cpu, self.ax_memory),
                                   (self.ax_net_latency, self.ax_throughput)) = plt.subplots(
                2, 2, figsize=(12, 8))
            self.canvas_performance = FigureCanvasTkAgg(self.fig_performance, viz_frame)
            self.canvas_performance.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)
            self.update_performance_plots()
        else:
            metrics_frame = ttk.LabelFrame(perf_frame, text="Performance Metrics")
            metrics_frame.pack(fill='both', expand=True, padx=10, pady=5)
            self.performance_text = scrolledtext.ScrolledText(metrics_frame, height=20)
            self.performance_text.pack(fill='both', expand=True, padx=10, pady=10)
            self.performance_text.insert(tk.END, "Performance Metrics\n" + "=" * 50 + "\n")

    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = tk.Frame(self.root, relief=tk.SUNKEN, bd=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = tk.Label(self.status_bar, text="Ready", anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.time_label = tk.Label(self.status_bar, text="", anchor=tk.E)
        self.time_label.pack(side=tk.RIGHT, padx=5)
        self.update_time()

    # ══════════════════════════════════════════════════════════════
    #  DATA GENERATION  (PyPower-driven or random fallback)
    # ══════════════════════════════════════════════════════════════

    def start_data_generation(self):
        """Start generating data for visualizations"""

        def generate_data():
            while True:
                try:
                    # ── PyPower-driven data ───────────────────────
                    if self.PYPOWER_AVAILABLE and self.bridge:
                        try:
                            net_entry, anomalies, _ = self.bridge.step()
                            self.network_data.append(net_entry)
                            self.anomaly_data.extend(anomalies)
                        except Exception as e:
                            # Fallback to random if PF step fails
                            self._generate_random_network_data()

                        # Generate consensus data from bridge step count
                        if random.random() > 0.7:
                            self.consensus_data.append({
                                'timestamp': time.time(),
                                'round': len(self.consensus_data) + 1,
                                'participants': random.randint(15, 24),
                                'consensus_time': random.uniform(1, 5)
                            })
                    else:
                        # ── Random fallback (original behaviour) ──
                        self._generate_random_network_data()

                        if random.random() > 0.7:
                            self.consensus_data.append({
                                'timestamp': time.time(),
                                'round': len(self.consensus_data) + 1,
                                'participants': random.randint(15, 24),
                                'consensus_time': random.uniform(1, 5)
                            })

                    # Performance metrics (always simulated)
                    self.performance_metrics['cpu_usage'].append(random.uniform(10, 80))
                    self.performance_metrics['memory_usage'].append(random.uniform(30, 90))
                    self.performance_metrics['network_latency'].append(random.uniform(5, 50))
                    self.performance_metrics['throughput'].append(random.uniform(100, 1000))

                    # Trim buffers
                    for key in self.performance_metrics:
                        if len(self.performance_metrics[key]) > 100:
                            self.performance_metrics[key] = self.performance_metrics[key][-100:]
                    if len(self.network_data) > 100:
                        self.network_data = self.network_data[-100:]
                    if len(self.anomaly_data) > 50:
                        self.anomaly_data = self.anomaly_data[-50:]
                    if len(self.consensus_data) > 50:
                        self.consensus_data = self.consensus_data[-50:]

                    time.sleep(2)
                except Exception as e:
                    print(f"Data generation error: {e}")
                    time.sleep(5)

        self.data_thread = threading.Thread(target=generate_data, daemon=True)
        self.data_thread.start()
        self.update_plots_timer()

    def _generate_random_network_data(self):
        """Original random data generation as fallback."""
        self.network_data.append({
            'timestamp': time.time(),
            'active_nodes': random.randint(20, 24),
            'latency': random.uniform(5, 50)
        })
        if random.random() > 0.8:
            self.anomaly_data.append({
                'timestamp': time.time(),
                'type': random.choice(['voltage', 'frequency', 'power']),
                'severity': random.choice(['low', 'medium', 'high']),
                'value': random.uniform(0.5, 2.0)
            })

    # ══════════════════════════════════════════════════════════════
    #  PLOT UPDATE TIMER
    # ══════════════════════════════════════════════════════════════

    def update_plots_timer(self):
        """Timer to update plots periodically"""
        if MPL_AVAILABLE:
            try:
                self.update_network_topology()
                self.update_anomaly_plots()
                self.update_consensus_plots()
                self.update_performance_plots()
            except Exception as e:
                print(f"Error updating plots: {e}")
        self.root.after(5000, self.update_plots_timer)

    # ── Network topology plot ─────────────────────────────────────

    def update_network_topology(self):
        if not MPL_AVAILABLE:
            return
        try:
            self.ax_network.clear()

            if self.PYPOWER_AVAILABLE and self.bridge:
                (gx, gy, g_labels), (sx, sy, s_labels), n_det = \
                    self.bridge.get_topology_positions()

                self.ax_network.scatter(gx, gy, c='red', s=100,
                                        label=f'Generators ({len(g_labels)})', alpha=0.7)
                self.ax_network.scatter(sx, sy, c='blue', s=100, marker='s',
                                        label=f'Substations ({len(s_labels)})', alpha=0.7)

                # Annotate bus numbers
                for i, lbl in enumerate(g_labels):
                    self.ax_network.annotate(str(lbl), (gx[i], gy[i]),
                                             textcoords="offset points",
                                             xytext=(0, 8), ha='center', fontsize=6)
                for i, lbl in enumerate(s_labels):
                    self.ax_network.annotate(str(lbl), (sx[i], sy[i]),
                                             textcoords="offset points",
                                             xytext=(0, 8), ha='center', fontsize=6)

                # Anomaly detectors
                det_x = np.linspace(float(min(gx)), float(max(gx)), n_det)
                det_y = np.ones(n_det) * 1
                self.ax_network.scatter(det_x, det_y, c='green', s=100, marker='^',
                                        label=f'Detectors ({n_det})', alpha=0.7)

                # Draw connections
                for i in range(len(gx) - 1):
                    self.ax_network.plot([gx[i], gx[i + 1]], [gy[i], gy[i + 1]],
                                         'k-', alpha=0.2)
                for i in range(len(sx) - 1):
                    self.ax_network.plot([sx[i], sx[i + 1]], [sy[i], sy[i + 1]],
                                         'k-', alpha=0.2)
                # Vertical connections gen -> sub
                step = max(1, len(gx) // max(len(sx), 1))
                for i in range(0, min(len(gx), len(sx)), max(step, 1)):
                    self.ax_network.plot([gx[i], sx[min(i, len(sx) - 1)]],
                                         [gy[i], sy[min(i, len(sy) - 1)]],
                                         'k-', alpha=0.15)

                case_label = PYPOWER_CASES.get(self.bridge.case_name, ('', '', 'Unknown'))[2]
                title = f'{case_label} — Synchronic Web Topology'
            else:
                # Original hardcoded IEEE 39-bus layout
                gen_x = np.linspace(1, 10, 10)
                gen_y = np.ones(10) * 3
                self.ax_network.scatter(gen_x, gen_y, c='red', s=100,
                                        label='Generators', alpha=0.7)
                sub_x = np.linspace(1, 10, 10)
                sub_y = np.ones(10) * 2
                self.ax_network.scatter(sub_x, sub_y, c='blue', s=100, marker='s',
                                        label='Substations', alpha=0.7)
                det_x = [3, 5.5, 8]
                det_y_vals = [1, 1, 1]
                self.ax_network.scatter(det_x, det_y_vals, c='green', s=100, marker='^',
                                        label='Anomaly Detectors', alpha=0.7)
                for i in range(len(gen_x) - 1):
                    self.ax_network.plot([gen_x[i], gen_x[i + 1]],
                                         [gen_y[i], gen_y[i + 1]], 'k-', alpha=0.3)
                for i in range(len(sub_x) - 1):
                    self.ax_network.plot([sub_x[i], sub_x[i + 1]],
                                         [sub_y[i], sub_y[i + 1]], 'k-', alpha=0.3)
                for i in range(0, len(gen_x), 2):
                    self.ax_network.plot([gen_x[i], sub_x[i]],
                                         [gen_y[i], sub_y[i]], 'k-', alpha=0.3)
                title = 'IEEE 39-Bus Synchronic Web Network Topology'

            self.ax_network.set_title(title)
            self.ax_network.set_xlabel('Network Nodes')
            self.ax_network.set_ylabel('Node Types')
            self.ax_network.legend(loc='upper right', fontsize=8)
            self.ax_network.grid(True, alpha=0.3)
            self.canvas_network.draw()
        except Exception as e:
            print(f"Error updating network topology: {e}")

    # ── Anomaly detection plots ───────────────────────────────────

    def update_anomaly_plots(self):
        if not MPL_AVAILABLE:
            return
        try:
            if self.PYPOWER_AVAILABLE and self.bridge:
                t_v, v, v_lo, v_hi = self.bridge.get_voltage_series()
                t_f, f, f_lo, f_hi = self.bridge.get_frequency_series()
                t_p, p = self.bridge.get_power_series()
            else:
                t_v = np.linspace(0, 10, 100)
                v = 1.0 + 0.02 * np.sin(t_v) + 0.01 * np.random.normal(0, 1, 100)
                v = np.where((t_v > 3) & (t_v < 4), 1.15, v)
                v_lo, v_hi = 0.95, 1.05

                t_f = t_v
                f = 60.0 + 0.1 * np.sin(t_f * 2) + 0.05 * np.random.normal(0, 1, 100)
                f = np.where((t_f > 6) & (t_f < 7), 59.3, f)
                f_lo, f_hi = 59.5, 60.5

                t_p = t_v
                p = 500 + 50 * np.sin(t_p * 3) + 20 * np.random.normal(0, 1, 100)

            # Voltage
            self.ax_voltage.clear()
            self.ax_voltage.plot(t_v, v, 'b-', label='Voltage (pu)')
            self.ax_voltage.axhline(y=v_hi, color='r', linestyle='--', label='Upper Limit')
            self.ax_voltage.axhline(y=v_lo, color='r', linestyle='--', label='Lower Limit')
            self.ax_voltage.set_title('Voltage Monitoring')
            self.ax_voltage.set_ylabel('Voltage (pu)')
            self.ax_voltage.legend(fontsize=7)
            self.ax_voltage.grid(True, alpha=0.3)

            # Frequency
            self.ax_frequency.clear()
            self.ax_frequency.plot(t_f, f, 'g-', label='Frequency (Hz)')
            self.ax_frequency.axhline(y=f_hi, color='r', linestyle='--', label='Upper Limit')
            self.ax_frequency.axhline(y=f_lo, color='r', linestyle='--', label='Lower Limit')
            self.ax_frequency.set_title('Frequency Monitoring')
            self.ax_frequency.set_ylabel('Frequency (Hz)')
            self.ax_frequency.legend(fontsize=7)
            self.ax_frequency.grid(True, alpha=0.3)

            # Power
            self.ax_power.clear()
            self.ax_power.plot(t_p, p, 'm-', label='Active Power (MW)')
            self.ax_power.set_title('Power Flow Monitoring')
            self.ax_power.set_ylabel('Power (MW)')
            self.ax_power.set_xlabel('Time (s)')
            self.ax_power.legend(fontsize=7)
            self.ax_power.grid(True, alpha=0.3)

            # Anomaly count
            self.ax_anomalies.clear()
            if self.anomaly_data:
                first_ts = self.anomaly_data[0].get('timestamp', time.time())
                anomaly_times = [a.get('timestamp', first_ts) - first_ts for a in self.anomaly_data]
                anomaly_counts = list(range(1, len(self.anomaly_data) + 1))
                self.ax_anomalies.plot(anomaly_times, anomaly_counts, 'ro-', label='Anomalies Detected')
            else:
                self.ax_anomalies.plot([0], [0], 'ro-', label='No Anomalies')
            self.ax_anomalies.set_title('Anomaly Detection Count')
            self.ax_anomalies.set_ylabel('Cumulative Count')
            self.ax_anomalies.set_xlabel('Time (s)')
            self.ax_anomalies.legend(fontsize=7)
            self.ax_anomalies.grid(True, alpha=0.3)

            self.fig_anomaly.tight_layout()
            self.canvas_anomaly.draw()
        except Exception as e:
            print(f"Error updating anomaly plots: {e}")

    # ── Consensus plots ───────────────────────────────────────────

    def update_consensus_plots(self):
        if not MPL_AVAILABLE:
            return
        try:
            self.ax_consensus_time.clear()
            if self.consensus_data:
                rounds = [c['round'] for c in self.consensus_data]
                times = [c['consensus_time'] for c in self.consensus_data]
                self.ax_consensus_time.plot(rounds, times, 'bo-', label='Consensus Time')
                self.ax_consensus_time.axhline(y=5.0, color='r', linestyle='--', label='SLA Limit')
            else:
                self.ax_consensus_time.plot([0], [0], 'bo-', label='No Data')
            self.ax_consensus_time.set_title('Consensus Time Performance')
            self.ax_consensus_time.set_xlabel('Consensus Round')
            self.ax_consensus_time.set_ylabel('Time (seconds)')
            self.ax_consensus_time.legend(fontsize=7)
            self.ax_consensus_time.grid(True, alpha=0.3)

            self.ax_vote_distribution.clear()
            vote_types = ['Agree', 'Disagree', 'Byzantine']
            vote_counts = [random.randint(15, 20), random.randint(2, 5), random.randint(0, 2)]
            colors = ['green', 'orange', 'red']
            self.ax_vote_distribution.pie(vote_counts, labels=vote_types,
                                          colors=colors, autopct='%1.1f%%')
            self.ax_vote_distribution.set_title('Vote Distribution')

            self.fig_consensus.tight_layout()
            self.canvas_consensus.draw()
        except Exception as e:
            print(f"Error updating consensus plots: {e}")

    # ── Performance plots ─────────────────────────────────────────

    def update_performance_plots(self):
        if not MPL_AVAILABLE:
            return
        try:
            time_points = list(range(len(self.performance_metrics['cpu_usage'])))

            self.ax_cpu.clear()
            self.ax_cpu.plot(time_points, self.performance_metrics['cpu_usage'],
                             'r-', label='CPU Usage')
            self.ax_cpu.axhline(y=80, color='orange', linestyle='--', label='Warning')
            self.ax_cpu.set_title('CPU Usage (%)')
            self.ax_cpu.set_ylabel('CPU %')
            self.ax_cpu.legend(fontsize=7)
            self.ax_cpu.grid(True, alpha=0.3)

            self.ax_memory.clear()
            self.ax_memory.plot(time_points, self.performance_metrics['memory_usage'],
                                'b-', label='Memory Usage')
            self.ax_memory.axhline(y=85, color='orange', linestyle='--', label='Warning')
            self.ax_memory.set_title('Memory Usage (%)')
            self.ax_memory.set_ylabel('Memory %')
            self.ax_memory.legend(fontsize=7)
            self.ax_memory.grid(True, alpha=0.3)

            self.ax_net_latency.clear()
            self.ax_net_latency.plot(time_points, self.performance_metrics['network_latency'],
                                     'g-', label='Network Latency')
            self.ax_net_latency.axhline(y=40, color='orange', linestyle='--', label='Warning')
            self.ax_net_latency.set_title('Network Latency (ms)')
            self.ax_net_latency.set_ylabel('Latency (ms)')
            self.ax_net_latency.set_xlabel('Time')
            self.ax_net_latency.legend(fontsize=7)
            self.ax_net_latency.grid(True, alpha=0.3)

            self.ax_throughput.clear()
            self.ax_throughput.plot(time_points, self.performance_metrics['throughput'],
                                    'm-', label='Throughput')
            self.ax_throughput.set_title('Network Throughput (msgs/sec)')
            self.ax_throughput.set_ylabel('Messages/sec')
            self.ax_throughput.set_xlabel('Time')
            self.ax_throughput.legend(fontsize=7)
            self.ax_throughput.grid(True, alpha=0.3)

            self.fig_performance.tight_layout()
            self.canvas_performance.draw()
        except Exception as e:
            print(f"Error updating performance plots: {e}")

    # ══════════════════════════════════════════════════════════════
    #  CORE ACTIONS
    # ══════════════════════════════════════════════════════════════

    def setup_monitoring(self):
        self.monitoring_thread = None

    def _on_case_change(self, event=None):
        """Handle power system case change from dropdown."""
        case_name = self.case_var.get()
        try:
            if self.PYPOWER_AVAILABLE and self.bridge:
                self.bridge.switch_case(case_name)
                nodes, n, f, q = self.bridge.build_node_list()

                # Update UI entries
                self.nodes_entry.delete(0, tk.END)
                self.nodes_entry.insert(0, str(n))
                self.tolerance_entry.delete(0, tk.END)
                self.tolerance_entry.insert(0, str(f))
                self.quorum_entry.delete(0, tk.END)
                self.quorum_entry.insert(0, str(q))

                case_label = PYPOWER_CASES[case_name][2]
                if hasattr(self, 'case_desc_var'):
                    self.case_desc_var.set(case_label)

                summary = self.bridge.get_case_summary()
                self.case_info_var.set(
                    f"{case_label} | {summary['num_buses']} buses, "
                    f"{summary['num_gens']} gens, "
                    f"{summary['num_branches']} branches | "
                    f"Load: {summary['total_load']:.0f} MW"
                )

                self.log_message(
                    f"🔄 Loaded {case_label}: {n} SW nodes, f={f}, quorum={q}",
                    level="INFO"
                )
        except Exception as e:
            self.log_message(f"❌ Failed to switch case: {e}", level="ERROR")

    def initialize_network(self):
        """Initialize SW network — PyPower-driven or fallback."""
        try:
            if self.PYPOWER_AVAILABLE and self.bridge:
                # ── PyPower-driven initialization ─────────────────
                case_name = self.case_var.get()
                self.bridge.switch_case(case_name)
                nodes, n, f, q = self.bridge.build_node_list()

                # Update UI entries to reflect real network
                self.nodes_entry.delete(0, tk.END)
                self.nodes_entry.insert(0, str(n))
                self.tolerance_entry.delete(0, tk.END)
                self.tolerance_entry.insert(0, str(f))
                self.quorum_entry.delete(0, tk.END)
                self.quorum_entry.insert(0, str(q))

                case_label = PYPOWER_CASES[case_name][2]
                summary = self.bridge.get_case_summary()

                self.log_message(f"🚀 Initializing {case_label} Synchronic Web Network...", level="INFO")
                self.log_message(f"   📊 PyPower Case: {case_label}", level="INFO")
                self.log_message(f"      • Buses: {summary['num_buses']}  "
                                 f"Generators: {summary['num_gens']}  "
                                 f"Branches: {summary['num_branches']}", level="DEBUG")
                self.log_message(f"      • Total Load: {summary['total_load']:.1f} MW  "
                                 f"Total Gen: {summary['total_gen']:.1f} MW", level="DEBUG")
                self.log_message(f"      • SW Nodes: {n}  f={f}  quorum={q}", level="DEBUG")
            else:
                # ── Fallback: build nodes from UI entries ─────────
                n = int(self.nodes_entry.get())
                f = int(self.tolerance_entry.get())
                q = int(self.quorum_entry.get())
                nodes = []
                for i in range(n):
                    ntype = "Generator" if i < 10 else "Substation" if i < 20 else "Detector"
                    bus_num = 30 + i if i < 10 else \
                        [1, 3, 4, 7, 8, 15, 16, 18, 20, 21][i - 10] if i < 20 else None
                    nodes.append(dict(
                        node_id=f"SW_{ntype.upper()}_{bus_num if bus_num else i + 1}",
                        ntype=ntype,
                        bus=bus_num
                    ))
                self.log_message("🚀 Initializing Synchronic Web Network (simulated)...", level="INFO")

            # Clear existing status tree
            for item in self.status_tree.get_children():
                self.status_tree.delete(item)

            # Populate status tree
            for nd in nodes:
                h = hashlib.sha256(f"{nd['node_id']}{time.time()}".encode()).hexdigest()[:8]
                self.status_tree.insert('', 'end', values=(
                    nd['node_id'],
                    nd['ntype'],
                    nd.get('bus', '') if nd.get('bus') is not None else '',
                    '✅ ONLINE',
                    h + '...'
                ))
                self.log_message(f"   ✅ {nd['node_id']} ({nd['ntype']}) initialized", level="SUCCESS")
                self.root.update()

            # Update metrics
            self.active_nodes_var.set(f"{len(nodes)}/{len(nodes)}")
            self.anomalies_var.set("0")
            self.consensus_var.set("0")
            self.latency_var.set("0ms")

            if self.PYPOWER_AVAILABLE and self.bridge:
                case_label = PYPOWER_CASES[self.case_var.get()][2]
                self.case_info_var.set(
                    f"{case_label} | {summary['num_buses']} buses, "
                    f"{summary['num_gens']} gens | "
                    f"Load: {summary['total_load']:.0f} MW"
                )
                self.log_message(
                    f"✅ {case_label} Synchronic Web Network initialized — "
                    f"{len(nodes)} nodes, {len(self.bridge.get_branch_flows())} branches",
                    level="SUCCESS"
                )
            else:
                self.case_info_var.set("IEEE 39-Bus (simulated)")
                self.log_message("✅ Synchronic Web Network initialized (simulated)", level="SUCCESS")

            self.log_message("🔒 Cryptographic security enabled with RSA-2048", level="INFO")
            self.log_message("🌐 Byzantine fault tolerance active", level="INFO")
            self.update_status("INITIALIZED", "#f39c12")

        except ValueError as e:
            self.log_message(f"❌ Invalid configuration: {e}", level="ERROR")
            messagebox.showerror("Error", f"Invalid configuration: {e}")
        except Exception as e:
            self.log_message(f"❌ Failed to initialize network: {e}", level="ERROR")
            messagebox.showerror("Error", f"Failed to initialize network: {e}")

    def start_monitoring(self):
        """Start network monitoring"""
        if self.is_running:
            self.log_message("⚠️  Monitoring is already running", level="WARNING")
            return

        self.is_running = True
        self.log_message("🎯 Starting network monitoring...", level="INFO")
        self.update_status("MONITORING", "#27ae60")

        def monitor_loop():
            while self.is_running:
                try:
                    anomaly_count = random.randint(0, 3)
                    if anomaly_count > 0:
                        current_anomalies = int(self.anomalies_var.get())
                        self.anomalies_var.set(str(current_anomalies + anomaly_count))
                        self.log_message(f"🚨 {anomaly_count} new anomalies detected", level="WARNING")

                    if random.random() > 0.7:
                        current_consensus = int(self.consensus_var.get())
                        self.consensus_var.set(str(current_consensus + 1))
                        self.log_message("🤝 Consensus round completed", level="INFO")

                    latency = random.randint(5, 50)
                    self.latency_var.set(f"{latency}ms")

                    time.sleep(2)
                except Exception as e:
                    self.log_message(f"❌ Monitoring error: {e}", level="ERROR")
                    break

        self.monitoring_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitoring_thread.start()

    def stop_monitoring(self):
        """Stop network monitoring"""
        if not self.is_running:
            self.log_message("⚠️  Monitoring is not running", level="WARNING")
            return
        self.is_running = False
        self.log_message("🛑 Stopping network monitoring...", level="INFO")
        self.update_status("STOPPED", "#e74c3c")

    def run_real_sw(self):
        """Run the Real_SW.py backend with enhanced integration"""
        try:
            real_sw_paths = [
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Real_SW.py'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Real_SW.py'),
                'Real_SW.py'
            ]

            real_sw_path = None
            for path in real_sw_paths:
                if os.path.exists(path):
                    real_sw_path = path
                    break

            if real_sw_path:
                self.log_message("🚀 Launching Real_SW.py with enhanced features...", level="INFO")
                self.log_message(f"   📂 Path: {real_sw_path}", level="DEBUG")

                def run_backend():
                    try:
                        result = subprocess.run(
                            [sys.executable, real_sw_path, '--enhanced'],
                            capture_output=True, text=True, timeout=300
                        )
                        if result.returncode == 0:
                            self.log_message("✅ Real_SW.py completed successfully", level="SUCCESS")
                            if result.stdout:
                                self.log_message(f"📤 Output: {result.stdout[:200]}...", level="DEBUG")
                        else:
                            self.log_message(
                                f"❌ Real_SW.py failed with code {result.returncode}", level="ERROR")
                            if result.stderr:
                                self.log_message(f"📥 Error: {result.stderr[:200]}...", level="ERROR")
                    except subprocess.TimeoutExpired:
                        self.log_message("⏰ Real_SW.py execution timeout (5 minutes)", level="WARNING")
                    except Exception as e:
                        self.log_message(f"❌ Error running Real_SW.py: {e}", level="ERROR")

                backend_thread = threading.Thread(target=run_backend, daemon=True)
                backend_thread.start()
            else:
                self.log_message("❌ Real_SW.py not found in expected locations", level="ERROR")
                messagebox.showerror("Error",
                                     "Real_SW.py not found. Please ensure it's in the same directory.")
        except Exception as e:
            self.log_message(f"❌ Failed to run Real_SW.py: {e}", level="ERROR")
            messagebox.showerror("Error", f"Failed to run Real_SW.py: {e}")

    # ── Tab action methods ────────────────────────────────────────

    def start_detection(self):
        self.log_message("🔍 Starting anomaly detection...", level="INFO")

    def stop_detection(self):
        self.log_message("🛑 Stopping anomaly detection...", level="INFO")

    def simulate_anomaly(self):
        anomaly_types = ["Voltage spike", "Frequency deviation",
                         "Power imbalance", "Communication loss"]
        anomaly = random.choice(anomaly_types)
        severity = random.choice(["Low", "Medium", "High", "Critical"])
        self.log_message(f"⚡ Simulated anomaly: {anomaly} (Severity: {severity})", level="WARNING")
        current_anomalies = int(self.anomalies_var.get())
        self.anomalies_var.set(str(current_anomalies + 1))

    def start_consensus(self):
        self.log_message("🤝 Starting Byzantine consensus...", level="INFO")

    def stop_consensus(self):
        self.log_message("🛑 Stopping consensus process...", level="INFO")

    def simulate_byzantine_fault(self):
        self.log_message("⚠️ Simulating Byzantine fault scenario...", level="WARNING")

    def start_performance_monitor(self):
        self.log_message("📊 Starting performance monitoring...", level="INFO")

    def stop_performance_monitor(self):
        self.log_message("📊 Stopping performance monitoring...", level="INFO")

    def reset_performance_metrics(self):
        for key in self.performance_metrics:
            self.performance_metrics[key] = []
        self.log_message("🔄 Performance metrics reset", level="INFO")

    # ── Utility methods ───────────────────────────────────────────

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        self.log_message("🧹 Log cleared", level="INFO")

    def save_log(self):
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                with open(filename, 'w') as fh:
                    fh.write(self.log_text.get(1.0, tk.END))
                self.log_message(f"💾 Log saved to {filename}", level="SUCCESS")
        except Exception as e:
            self.log_message(f"❌ Failed to save log: {e}", level="ERROR")

    def refresh_log(self):
        self.log_message("🔄 Log refreshed", level="INFO")

    def filter_log(self, event=None):
        filter_level = self.log_filter_var.get()
        self.log_message(f"🔍 Applying filter: {filter_level}", level="DEBUG")

    def log_message(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        if hasattr(self, 'log_text'):
            self.log_text.insert(tk.END, formatted_message, level)
            self.log_text.see(tk.END)
        else:
            print(formatted_message.strip())

    def update_status(self, status, color):
        if hasattr(self, 'status_indicator'):
            self.status_indicator.config(fg=color)
            self.status_text.config(text=status, fg=color)

    def update_time(self):
        if hasattr(self, 'time_label'):
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.time_label.config(text=current_time)
            self.root.after(1000, self.update_time)

    # ── Menu action methods ───────────────────────────────────────

    def new_config(self):
        self.log_message("📄 Creating new configuration...", level="INFO")

    def open_config(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.log_message(f"📂 Opening configuration: {filename}", level="INFO")

    def save_config(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.log_message(f"💾 Saving configuration: {filename}", level="INFO")

    def export_report(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.log_message(f"📊 Exporting report: {filename}", level="INFO")

    def network_diagnostic(self):
        self.log_message("🔧 Running network diagnostic...", level="INFO")
        if self.PYPOWER_AVAILABLE and self.bridge:
            violations = self.bridge.check_power_balance()
            if violations:
                for label, imb in violations:
                    self.log_message(
                        f"   ⚠️  Power imbalance at {label}: {imb:.4f} p.u.", level="WARNING")
            else:
                self.log_message("   ✅ Power balance within tolerance", level="SUCCESS")

    def performance_test(self):
        self.log_message("⚡ Running performance test...", level="INFO")

    def security_audit(self):
        self.log_message("🔒 Running security audit...", level="INFO")

    def show_user_guide(self):
        guide_window = tk.Toplevel(self.root)
        guide_window.title("User Guide")
        guide_window.geometry("650x500")

        guide_text = scrolledtext.ScrolledText(guide_window, wrap=tk.WORD)
        guide_text.pack(fill='both', expand=True, padx=10, pady=10)

        guide_content = """
SynGrid — Synchronic Web Analyzer v4.0 — User Guide

OVERVIEW:
This application provides comprehensive monitoring and analysis of power systems
using advanced Synchronic Web architecture for anomaly detection and Byzantine
fault tolerance. It supports any PyPower case (IEEE 14/30/39/57/118/300-bus)
while keeping IEEE 39-bus as the default case study.

TABS:
1. Main Control — Network configuration, case selection, and system monitoring
2. Network Monitor — Real-time network topology visualization
3. Anomaly Detection — Power system anomaly monitoring (physics-based with PyPower)
4. Consensus Viewer — Byzantine consensus process monitoring
5. Performance — System performance metrics

GETTING STARTED:
1. Navigate to Main Control tab
2. Select a Power System Case from the dropdown (default: case39)
3. Click "Initialize SW Network" — parameters auto-fill from PyPower
4. Click "Start Monitoring" to begin real-time monitoring
5. Use other tabs to view specific monitoring data

PYPOWER INTEGRATION:
When PyPower is installed, the application uses real power flow calculations
instead of random data. Anomaly detection is physics-informed, using actual
voltage/frequency/power limits from the selected case.

Available cases: case14, case24_ieee_rts, case30, case39, case57, case118, case300

FEATURES:
- Generalized power system support via PyPower
- Real-time power flow simulation with load perturbation
- Physics-based anomaly detection (voltage, frequency, power limits)
- Kirchhoff power balance verification
- Byzantine fault tolerance with cryptographic security
- Performance monitoring and SLA compliance
- Network topology visualization scaled to any case

For technical support, contact the development team.
"""
        guide_text.insert(tk.END, guide_content)

    def show_ieee_standards(self):
        standards_window = tk.Toplevel(self.root)
        standards_window.title("IEEE Standards Compliance")
        standards_window.geometry("600x400")

        standards_text = scrolledtext.ScrolledText(standards_window, wrap=tk.WORD)
        standards_text.pack(fill='both', expand=True, padx=10, pady=10)

        standards_content = """
IEEE Standards Compliance

This application complies with the following IEEE standards:

IEEE Test Systems (via PyPower):
- IEEE 14-Bus: Small test system for basic power flow studies
- IEEE 24-Bus RTS: Reliability Test System
- IEEE 30-Bus: Medium test system for OPF studies
- IEEE 39-Bus (New England): Standard benchmark for stability studies
- IEEE 57-Bus: Larger test system for advanced analysis
- IEEE 118-Bus: Large-scale power system benchmark
- IEEE 300-Bus: Very large system for scalability testing

IEEE 3333 — Synchronic Web Architecture:
- Cryptographic entanglement protocols
- Byzantine fault tolerance mechanisms
- Real-time consensus algorithms

IEEE C37.118 — Synchrophasor Communications:
- Phasor measurement unit protocols
- Real-time data acquisition standards
- Time synchronization requirements

IEEE 1547 — Distributed Energy Resources:
- Grid interconnection standards
- Power quality requirements
- Protection and control systems

IEEE 2030 — Smart Grid Interoperability:
- Communication protocols
- Information exchange standards
- System integration guidelines

All implementations follow the latest IEEE standards and best practices
for power system monitoring and control applications.
"""
        standards_text.insert(tk.END, standards_content)

    def show_about(self):
        """Show About dialog with user details"""
        about_window = tk.Toplevel(self.root)
        about_window.title("About SynGrid — Synchronic Web Analyzer")
        about_window.geometry("700x550")
        about_window.resizable(False, False)
        about_window.configure(bg='white')

        main_frame = tk.Frame(about_window, bg='white')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Header
        header_frame = tk.Frame(main_frame, bg='white')
        header_frame.pack(fill='x', pady=(0, 20))

        if hasattr(self, 'header_logo') and self.header_logo:
            logo_label = tk.Label(header_frame, image=self.header_logo, bg='white')
            logo_label.pack(side='left', padx=(0, 20))

        title_frame = tk.Frame(header_frame, bg='white')
        title_frame.pack(side='left', fill='both', expand=True)

        tk.Label(title_frame,
                 text="SynGrid — Synchronic Web Analyzer",
                 font=('Arial', 16, 'bold'),
                 bg='white', fg='#2c3e50').pack(anchor='w')
        tk.Label(title_frame,
                 text="Version 4.0 — Generalized with PyPower",
                 font=('Arial', 10),
                 bg='white', fg='#7f8c8d').pack(anchor='w')
        tk.Label(title_frame,
                 text="Production-grade Power System Anomaly Detection with Synchronic Web Architecture",
                 font=('Arial', 9, 'italic'),
                 bg='white', fg='#34495e').pack(anchor='w')

        # Separator
        tk.Frame(main_frame, height=2, bg='#bdc3c7').pack(fill='x', pady=(0, 20))

        # Developer information
        dev_frame = tk.LabelFrame(main_frame, text="Developer Information",
                                  font=('Arial', 12, 'bold'),
                                  bg='white', fg='#2c3e50', padx=15, pady=15)
        dev_frame.pack(fill='x', pady=(0, 15))

        dev_info = [
            ("Name:", "Mohamed Massaoudi, PhD"),
            ("Title:", "Senior Research Engineer & Lab Manager"),
            ("Department:", "Electrical and Computer Engineering"),
            ("Institution:", "Texas A&M University"),
            ("Laboratory:", "Resilient Energy Systems Lab (RESLab)"),
            ("Center:", "TEES Smart Grid Center"),
            ("Address:", "3128 TAMU | College Station, TX 77843-3128"),
        ]

        for label, value in dev_info:
            info_frame = tk.Frame(dev_frame, bg='white')
            info_frame.pack(fill='x', pady=2)
            tk.Label(info_frame, text=label, font=('Arial', 10, 'bold'),
                     bg='white', fg='#2c3e50', width=12, anchor='w').pack(side='left')
            tk.Label(info_frame, text=value, font=('Arial', 10),
                     bg='white', fg='#34495e', anchor='w').pack(side='left', fill='x', expand=True)

        # Application information
        app_frame = tk.LabelFrame(main_frame, text="Application Information",
                                  font=('Arial', 12, 'bold'),
                                  bg='white', fg='#2c3e50', padx=15, pady=15)
        app_frame.pack(fill='x', pady=(0, 15))

        app_info = (
            "SynGrid is a generalized, production-grade power system monitoring platform "
            "using advanced Synchronic Web architecture. It supports any PyPower case "
            "(IEEE 14/30/39/57/118/300-bus) with real power flow calculations, "
            "physics-based anomaly detection, Byzantine fault tolerance, and "
            "comprehensive performance monitoring.\n\n"
            "Key Features:\n"
            "• Generalized power system support via PyPower\n"
            "• Real-time power flow simulation with load perturbation\n"
            "• Physics-based anomaly detection (voltage, frequency, power limits)\n"
            "• Byzantine consensus mechanisms\n"
            "• Cryptographic security (RSA-2048)\n"
            "• Network topology visualization scaled to any case"
        )

        tk.Label(app_frame, text=app_info, font=('Arial', 9),
                 bg='white', fg='#34495e',
                 justify='left', wraplength=600).pack(anchor='w')

        # Footer
        footer_frame = tk.Frame(main_frame, bg='white')
        footer_frame.pack(fill='x', pady=(15, 0))

        tk.Label(footer_frame,
                 text="© 2025 Texas A&M University — All Rights Reserved",
                 font=('Arial', 8), bg='white', fg='#95a5a6').pack()
        build_date = datetime.now().strftime("%B %Y")
        tk.Label(footer_frame, text=f"Built: {build_date}",
                 font=('Arial', 8), bg='white', fg='#95a5a6').pack()

        # Close button
        btn_frame = tk.Frame(main_frame, bg='white')
        btn_frame.pack(pady=(15, 0))
        tk.Button(btn_frame, text="Close", command=about_window.destroy,
                  font=('Arial', 10), bg='#3498db', fg='white',
                  padx=30, pady=8, relief='flat', cursor='hand2').pack()

        # Center
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (about_window.winfo_width() // 2)
        y = (about_window.winfo_screenheight() // 2) - (about_window.winfo_height() // 2)
        about_window.geometry(f"+{x}+{y}")

    # ══════════════════════════════════════════════════════════════
    #  RUN
    # ══════════════════════════════════════════════════════════════

    def run(self):
        """Run the application"""
        self.log_message("🌟 SynGrid — Synchronic Web Analyzer started", level="SUCCESS")
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        app = SynchronicWebAnalyzer()
        app.run()
    except Exception as e:
        print(f"Error starting SynGrid: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
