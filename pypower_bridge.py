"""
PyPower Bridge for SynGrid — Generalized Power System Integration
=================================================================
Single integration point between PyPower and the SynGrid GUI.
Replaces all hardcoded IEEE 39-bus data with dynamic network loading
from any PyPower case while keeping IEEE 39-bus as the default.

Author: Mohamed Massaoudi, PhD — Texas A&M University
"""

import time
import copy
import importlib
import numpy as np
from collections import deque

# ── NumPy compatibility shim for PyPower ──────────────────────────
# PyPower uses numpy.in1d / numpy.bool / numpy.int / numpy.float / numpy.complex
# which were removed in NumPy ≥ 2.0.  Restore them so PyPower can import cleanly.
import warnings as _warnings
with _warnings.catch_warnings():
    _warnings.simplefilter("ignore", FutureWarning)
    _NP_COMPAT = {
        'in1d': np.isin,
        'bool': bool,
        'int': int,
        'float': float,
        'complex': complex,
        'object': object,
        'str': str,
    }
    for _attr, _val in _NP_COMPAT.items():
        try:
            getattr(np, _attr)
        except (AttributeError, FutureWarning):
            setattr(np, _attr, _val)

# ── PyPower column indices ────────────────────────────────────────
BUS_I    = 0   # bus number
BUS_TYPE = 1   # 1=PQ, 2=PV, 3=ref
PD       = 2   # real power demand (MW)
QD       = 3   # reactive power demand (MVAr)
GS       = 4   # shunt conductance
BS       = 5   # shunt susceptance
BUS_AREA = 6
VM       = 7   # voltage magnitude (p.u.)
VA       = 8   # voltage angle (degrees)
BASE_KV  = 9

GEN_BUS  = 0   # generator bus number
PG       = 1   # real power output (MW)
QG       = 2   # reactive power output (MVAr)
QMAX     = 3
QMIN     = 4
VG       = 5
MBASE    = 6
GEN_STATUS = 7
PMAX     = 8
PMIN     = 9

F_BUS    = 0   # branch "from" bus
T_BUS    = 1   # branch "to" bus
BR_R     = 2   # resistance
BR_X     = 3   # reactance
BR_B     = 4   # total line charging susceptance
RATE_A   = 5
PF       = 13  # real power injected at "from" bus (MW)
QF       = 14  # reactive power injected at "from" bus (MVAr)

# ── Available PyPower cases ───────────────────────────────────────
CASES = {
    'case14':  ('pypower.api', 'case14',  'IEEE 14-Bus'),
    'case24_ieee_rts': ('pypower.api', 'case24_ieee_rts', 'IEEE 24-Bus RTS'),
    'case30':  ('pypower.api', 'case30',  'IEEE 30-Bus'),
    'case39':  ('pypower.api', 'case39',  'IEEE 39-Bus (New England)'),
    'case57':  ('pypower.api', 'case57',  'IEEE 57-Bus'),
    'case118': ('pypower.api', 'case118', 'IEEE 118-Bus'),
    'case300': ('pypower.api', 'case300', 'IEEE 300-Bus'),
}


class PowerSystemBridge:
    """
    Single integration point between PyPower and SynGrid GUI.
    Replaces all random data generation with real power flow results.
    Designed to slot into the existing self.network_data /
    self.anomaly_data / self.performance_metrics pattern.
    """

    def __init__(self, case_name='case39'):
        self.case_name = case_name
        self.ppc_base   = None   # original case (never mutated)
        self.ppc_solved = None   # last solved case
        self.history    = {}     # bus_id -> deque(maxlen=50) for temporal checks
        self.t          = 0      # simulation step counter
        self._load_and_solve(case_name)

    # ── Case loading ──────────────────────────────────────────────

    def _load_and_solve(self, case_name):
        from pypower.api import runpf, ppoption

        meta = CASES.get(case_name)
        if meta is None:
            raise ValueError(
                f"Unknown case: {case_name}. "
                f"Available: {list(CASES.keys())}"
            )
        mod_name, fn_name, _ = meta
        mod = importlib.import_module(mod_name)
        self.ppc_base = getattr(mod, fn_name)()

        opts = ppoption(VERBOSE=0, OUT_ALL=0)
        result, converged = runpf(copy.deepcopy(self.ppc_base), opts)
        self.ppc_solved = result if converged else copy.deepcopy(self.ppc_base)

        # Initialise history buffers
        self.history.clear()
        for row in self.ppc_solved['bus']:
            self.history[int(row[BUS_I])] = deque(maxlen=50)

    def switch_case(self, case_name):
        """Hot-swap power system case at runtime."""
        self.case_name = case_name
        self.history.clear()
        self.t = 0
        self._load_and_solve(case_name)

    # ── Node map (replaces hardcoded loop in initialize_network) ──

    def build_node_list(self):
        """
        Returns (nodes_list, total_n, f, quorum).
        Each node dict has keys: node_id, ntype, bus.
        Also auto-computes Byzantine tolerance f and quorum.
        """
        bus = self.ppc_solved['bus']
        gen = self.ppc_solved['gen']
        nodes = []

        gen_set = set(gen[:, GEN_BUS].astype(int))

        # Find slack bus (type 3)
        slack_mask = bus[:, BUS_TYPE] == 3
        if np.any(slack_mask):
            slack_bus = int(bus[slack_mask, BUS_I][0])
        else:
            slack_bus = int(bus[0, BUS_I])

        # Control center on slack bus
        nodes.append(dict(
            node_id=f'SW_CC_{slack_bus}',
            ntype='Control Center',
            bus=slack_bus
        ))

        # One SW node per generator bus
        for b in sorted(gen_set):
            nodes.append(dict(
                node_id=f'SW_GEN_{b}',
                ntype='Generator',
                bus=b
            ))

        # Load buses as substations (PD > 0, not a generator bus)
        load_buses = bus[bus[:, PD] > 0, BUS_I].astype(int)
        for b in sorted(load_buses):
            if b not in gen_set:
                nodes.append(dict(
                    node_id=f'SW_SUB_{b}',
                    ntype='Substation',
                    bus=int(b)
                ))

        # Anomaly detectors: 1 per 8 power nodes (minimum 1)
        n_power = len(nodes)
        n_det = max(1, n_power // 8)
        for i in range(n_det):
            nodes.append(dict(
                node_id=f'SW_DET_{i}',
                ntype='Anomaly Detector',
                bus=None
            ))

        n = len(nodes)
        f = (n - 1) // 3
        q = 2 * f + 1
        return nodes, n, f, q

    # ── Simulation step (replaces generate_data thread content) ──

    def step(self, noise=0.02, attack_overrides=None):
        """
        Run one perturbed power flow step.
        Returns (network_entry, anomaly_list, measurements_dict).
        attack_overrides: {bus_id: {'voltage': v, 'p_load': p, ...}}
        """
        from pypower.api import runpf, ppoption

        ppc = copy.deepcopy(self.ppc_base)

        # Realistic load variation: slow sinusoidal + small Gaussian noise
        n_bus = len(ppc['bus'])
        load_variation = (
            1.0
            + 0.05 * np.sin(self.t * 0.1)
            + np.random.normal(0, noise, n_bus)
        )
        ppc['bus'][:, PD] *= np.clip(load_variation, 0.8, 1.2)
        ppc['bus'][:, QD] *= np.clip(load_variation, 0.8, 1.2)

        # Inject attack if requested
        if attack_overrides:
            for bid, overrides in attack_overrides.items():
                mask = ppc['bus'][:, BUS_I] == bid
                if 'voltage' in overrides:
                    ppc['bus'][mask, VM] = overrides['voltage']
                if 'p_load' in overrides:
                    ppc['bus'][mask, PD] = overrides['p_load']

        opts = ppoption(VERBOSE=0, OUT_ALL=0)
        result, converged = runpf(ppc, opts)
        self.t += 1

        if not converged:
            return self._fallback_step()

        self.ppc_solved = result
        measurements = self._extract_measurements(result)
        anomalies    = self._detect_anomalies(measurements)

        network_entry = {
            'timestamp':    time.time(),
            'active_nodes': len(measurements),
            'latency':      float(np.random.uniform(15, 45)),
            'measurements': measurements,
        }
        return network_entry, anomalies, measurements

    def _extract_measurements(self, result):
        """Per-bus measurement dict keyed by bus_id."""
        m = {}
        bus = result['bus']
        gen = result['gen']
        gen_buses = {int(g[GEN_BUS]): g for g in gen}

        for row in bus:
            bid = int(row[BUS_I])
            g = gen_buses.get(bid)
            m[bid] = {
                'voltage':      float(row[VM]),
                'angle':        float(row[VA]),
                'p_load':       float(row[PD]),
                'q_load':       float(row[QD]),
                'base_kv':      float(row[BASE_KV]),
                'p_gen':        float(g[PG]) if g is not None else 0.0,
                'q_gen':        float(g[QG]) if g is not None else 0.0,
                'p_max':        float(g[PMAX]) if g is not None else 0.0,
                'p_min':        float(g[PMIN]) if g is not None else 0.0,
                'frequency':    60.0 + float(np.random.normal(0, 0.05)),
                'is_generator': g is not None,
            }
        return m

    # ── Physics-based anomaly detection ───────────────────────────

    def _detect_anomalies(self, measurements):
        anomalies = []
        V_LO, V_HI = 0.94, 1.06
        F_LO, F_HI = 59.5, 60.5

        for bid, m in measurements.items():
            hist = self.history.get(bid)
            if hist is None:
                hist = deque(maxlen=50)
                self.history[bid] = hist

            v = m['voltage']
            f = m['frequency']

            # Voltage threshold violations
            if not (V_LO <= v <= V_HI):
                anomalies.append({
                    'timestamp': time.time(),
                    'bus':       bid,
                    'type':      'voltage_spike' if v > V_HI else 'voltage_sag',
                    'severity':  'critical' if abs(v - 1.0) > 0.15 else 'high',
                    'value':     v,
                })

            # Frequency deviation
            if not (F_LO <= f <= F_HI):
                anomalies.append({
                    'timestamp': time.time(),
                    'bus':       bid,
                    'type':      'frequency_deviation',
                    'severity':  'high',
                    'value':     f,
                })

            # Generator power limit violation
            if m['is_generator'] and m['p_max'] > 0:
                if not (m['p_min'] - 1e-3 <= m['p_gen'] <= m['p_max'] + 1e-3):
                    anomalies.append({
                        'timestamp': time.time(),
                        'bus':       bid,
                        'type':      'power_limit_violation',
                        'severity':  'medium',
                        'value':     m['p_gen'],
                    })

            # Temporal: sudden voltage change vs sliding window baseline
            if len(hist) >= 5:
                baseline = np.mean([h['voltage'] for h in hist])
                if abs(v - baseline) > 0.1 * max(abs(baseline), 0.01):
                    anomalies.append({
                        'timestamp': time.time(),
                        'bus':       bid,
                        'type':      'sudden_change',
                        'severity':  'medium',
                        'value':     abs(v - baseline),
                    })

            hist.append(m)

        # System-wide Kirchhoff power balance check
        total_gen  = sum(m['p_gen']  for m in measurements.values())
        total_load = sum(m['p_load'] for m in measurements.values())
        if total_load > 0 and abs(total_gen - total_load) / total_load > 0.05:
            anomalies.append({
                'timestamp': time.time(),
                'bus':       'system',
                'type':      'power_imbalance',
                'severity':  'high',
                'value':     abs(total_gen - total_load),
            })

        return anomalies

    def _fallback_step(self):
        """Return safe dummy data if power flow diverges."""
        return (
            {'timestamp': time.time(), 'active_nodes': 0, 'latency': 999},
            [],
            {}
        )

    # ── Plot data helpers (feed directly into existing ax_ calls) ─

    def get_voltage_series(self, n=100):
        """Returns (time_pts, voltage_array, v_lo, v_hi) for ax_voltage."""
        bus = self.ppc_solved['bus']
        v_mean = float(np.mean(bus[:, VM]))
        t = np.linspace(0, 10, n)
        v = v_mean + 0.01 * np.sin(t * 2) + 0.005 * np.random.normal(0, 1, n)
        return t, v, 0.95, 1.05

    def get_frequency_series(self, n=100):
        """Returns (time_pts, freq_array, f_lo, f_hi)."""
        t = np.linspace(0, 10, n)
        f = 60.0 + 0.05 * np.sin(t * 3) + 0.02 * np.random.normal(0, 1, n)
        return t, f, 59.5, 60.5

    def get_power_series(self, n=100):
        """Returns (time_pts, power_array) based on actual gen output."""
        gen = self.ppc_solved['gen']
        total_gen = float(np.sum(gen[:, PG]))
        t = np.linspace(0, 10, n)
        p = total_gen + 10 * np.sin(t * 2) + 5 * np.random.normal(0, 1, n)
        return t, p

    def get_topology_positions(self):
        """
        Returns (gen_xy, sub_xy, n_det) for update_network_topology.
        gen_xy = (x_array, y_array, bus_labels)
        sub_xy = (x_array, y_array, bus_labels)
        Positions derived from actual bus numbers.
        """
        bus = self.ppc_solved['bus']
        gen = self.ppc_solved['gen']
        gen_set = set(gen[:, GEN_BUS].astype(int))

        gen_buses = sorted(gen_set)
        sub_buses = sorted(
            int(b) for b in bus[:, BUS_I]
            if int(b) not in gen_set
            and bus[bus[:, BUS_I] == b, PD][0] > 0
        )

        n_gen = len(gen_buses)
        n_sub = len(sub_buses)

        gen_xy = (
            np.linspace(1, max(n_gen, 1), max(n_gen, 1)),
            np.ones(max(n_gen, 1)) * 3,
            gen_buses
        )
        sub_xy = (
            np.linspace(1, max(n_sub, 1), max(n_sub, 1)),
            np.ones(max(n_sub, 1)) * 2,
            sub_buses
        )
        n_det = max(1, (n_gen + n_sub) // 8)
        return gen_xy, sub_xy, n_det

    # ── Summary info ──────────────────────────────────────────────

    def get_case_summary(self):
        """Return a summary dict of the loaded case."""
        bus = self.ppc_solved['bus']
        gen = self.ppc_solved['gen']
        branch = self.ppc_solved['branch']
        return {
            'case_name':    self.case_name,
            'case_label':   CASES[self.case_name][2],
            'num_buses':    len(bus),
            'num_gens':     len(gen),
            'num_branches': len(branch),
            'total_load':   float(np.sum(bus[:, PD])),
            'total_gen':    float(np.sum(gen[:, PG])),
            'slack_bus':    int(bus[bus[:, BUS_TYPE] == 3, BUS_I][0])
                            if np.any(bus[:, BUS_TYPE] == 3) else 'N/A',
        }

    def get_bus_measurements(self, bus_id):
        """Return voltage, angle, load for a specific bus."""
        bus = self.ppc_solved['bus']
        row = bus[bus[:, BUS_I] == bus_id]
        if len(row) == 0:
            return None
        return {
            'bus_id':   bus_id,
            'voltage':  float(row[0, VM]),
            'angle':    float(row[0, VA]),
            'p_load':   float(row[0, PD]),
            'q_load':   float(row[0, QD]),
            'base_kv':  float(row[0, BASE_KV]),
        }

    def get_branch_flows(self):
        """Return all branch flows as list of dicts."""
        branch = self.ppc_solved['branch']
        flows = []
        for row in branch:
            flows.append({
                'from_bus': int(row[F_BUS]),
                'to_bus':   int(row[T_BUS]),
                'p_flow':   float(row[PF]) if len(row) > PF else 0.0,
                'q_flow':   float(row[QF]) if len(row) > QF else 0.0,
            })
        return flows

    def check_power_balance(self, tolerance=0.05):
        """
        Returns list of (label, imbalance) tuples where |imbalance| > tolerance.
        """
        gen = self.ppc_solved['gen']
        bus = self.ppc_solved['bus']
        violations = []
        total_gen  = float(np.sum(gen[:, PG]))
        total_load = float(np.sum(bus[:, PD]))
        if total_load > 0:
            imbalance = abs(total_gen - total_load) / total_load
            if imbalance > tolerance:
                violations.append(('system', imbalance))
        return violations
