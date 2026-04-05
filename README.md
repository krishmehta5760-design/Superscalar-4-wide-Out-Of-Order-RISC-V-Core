# Superscalar 4-Wide Out-of-Order RISC-V Core

A high-performance, synthesizable **4-wide Superscalar Out-of-Order (OoO) RISC-V Processor** implemented in Verilog. This core features dynamic scheduling, register renaming, and a robust Python-based verification environment with an interactive performance dashboard.

## 🚀 Key Architectural Features

### Pipeline & Execution
*   **Superscalar Frontend**: 4-wide instruction fetch and decode per cycle.
*   **Out-of-Order Back-end**: Dynamic scheduling using an Issue Queue (IQ) to execute instructions as soon as operands are ready.
*   **4-Wide Commit**: Upgraded Reorder Buffer (ROB) capable of retiring up to 4 instructions per cycle, reaching a peak IPC of 4.0.
*   **Load-Store Queue (LSQ)**: Advanced memory dependency handling for out-of-order loads and stores.

### Register Renaming & Hazards
*   **RAT & PRF**: 128-entry Physical Register File (PRF) with a Register Alias Table (RAT) to eliminate WAW and WAR hazards.
*   **Speculative Execution**: Branch Prediction Unit (BPU) with automated pipeline flushing upon mispredictions.

---

## 📊 Verification & Visualization Suite

This project includes a professional-grade Python verification wrapper designed for hardware exhibitions and performance analysis.

### Interactive Expo Dashboard
The `generate_expo.py` suite automatically runs a sequence of architectural stress tests and generates a **Live HTML Dashboard**.
*   **IPC Monitoring**: Real-time Instructions Per Cycle tracking.
*   **Hazard Analysis**: Visualization of RAW, WAR, and WAW hazard handling.
*   **Cycle Breakdowns**: Detailed logs of instruction retirement and pipeline stalls.

---

## 🛠️ Getting Started

### Prerequisites
*   **Simulator**: [Icarus Verilog](http://iverilog.icarus.com/) (Version 11.0+)
*   **Execution**: [WSL/Ubuntu](https://learn.microsoft.com/en-us/windows/wsl/install) (Recommended for stability)
*   **Verification**: Python 3.12+ with `cocotb` and `cocotb-test`

### Installation & Run
1. Clone the repository:
   ```bash
   git clone https://github.com/krishmehta5760-design/Superscalar-4-wide-Out-Of-Order-RISC-V-Core.git
   cd Superscalar-4-wide-Out-Of-Order-RISC-V-Core
   ```

2. Run the full simulation suite and generate the dashboard:
   ```bash
   python3 generate_expo.py
   ```

3. View the results:
   ```bash
   # On Windows
   start expo_dashboard.html
   ```

---

## 📂 Project Structure

```text
.
├── rtl/               # Core Verilog source files
├── generate_expo.py   # Main dashboard generation script
├── wrapper.py         # Python-to-HDL software bridge
├── programs.py        # RISC-V test assembly programs (Hex)
├── sim_tb.py          # Cocotb hardware testbench
├── Makefile           # Simulation configuration
└── README.md          # You are here!
```

---

## 🏆 Performance Benchmarks
| Benchmark | Theoretical IPC | Achieved IPC |
| :--- | :---: | :---: |
| Maximum ILP | 4.0 | **3.2+** |
| Fibonacci | 1.0 | **0.95** |
| RAW Chain | 1.0 | **0.88** |

---

Developed by **Krish Mehta**
