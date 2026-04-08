# Project Title
High-Performance 4-Wide Superscalar Out-of-Order RISC-V Processor Core

# Project Overview
This project focuses on the architectural design, Register Transfer Level (RTL) implementation, and functional verification of an advanced RISC-V processor. Advancing beyond traditional in-order single-issue pipelines, this project delivers a dynamically scheduled, 4-wide superscalar core using the RISC-V RV32I instruction set architecture. By leveraging deep out-of-order execution, register renaming, and speculative execution, the design successfully mitigates data hazards and structural stalls, resulting in high instruction-level parallelism and robust processing throughput.

**Duration:** April 2026  
**Project Mentors:** Jishnu, Aadithya GB  
**Team Members:** Aditya Shet, Krish Mehta, Rakshita Hiremath, Veer Nagpal  

---

## 1. Introduction

### 1.1 Project Statement
The objective of this project is to implement a high-performance 4-wide superscalar Out-of-Order (OoO) RISC-V processor from the ground up. Traditional processors rely on in-order pipelines which suffer from significant performance degradation when confronted with structural bottlenecks, control hazards (like branches), or data dependencies (RAW, WAW, WAR). To bypass these limitations, our project implements dynamic instruction scheduling. The processor is designed to fetch, decode, and issue multiple instructions simultaneously, allowing independent operations to execute as soon as their operands are available. The overarching goal is to maximize Instruction-Level Parallelism (ILP) and attain an Instruction Per Cycle (IPC) metric that closely approaches the theoretical peak of a 4-wide machine.

### 1.2 Background Survey
With the increasing demand for high-throughput computing, modern processors have shifted towards Superscalar Out-of-Order execution models. 
*   **RISC-V ISA:** We selected the RISC-V (RV32I) open-standard instruction set architecture due to its modularity, lack of legacy baggage, and rich ecosystem for academic and industrial research.
*   **Tomasulo’s Algorithm & Dynamic Scheduling:** First introduced in the IBM System/360 Model 91, this algorithm tracks operand availability across distributed reservation stations. This forms the basis for allowing younger instructions to bypass older stalled ones safely.
*   **Register Renaming:** A technique critical to superscalar designs. By dynamically mapping a limited set of architectural registers to a much larger pool of physical registers, the processor effectively eliminates false dependencies (Write-After-Write and Write-After-Read hazards), exposing much more true ILP.

---

## 2. Methodology

### 2.1 Techniques & Approach
To achieve a deep out-of-order execution engine, we employed a highly decoupled pipeline architecture. The front-end of the processor remains strictly in-order to ensure correct program flow, while the execution core operates completely out-of-order. 
*   **Explicit Register Renaming:** The architectural state (32 registers) is decoupled from the physical state. We implemented a Physical Register File (PRF) comprising 128 registers alongside a Register Alias Table (RAT) and a Free List. This completely removes WAR and WAW hazards dynamically.
*   **Precise Exceptions and Speculation:** To handle branch mispredictions or exceptions correctly despite executing instructions out-of-order, we implemented speculative execution supported by a Reorder Buffer (ROB). The ROB serves as a safety net, committing instructions to the physical architectural state only when they are known to be definitively correct and the oldest in the machine.

### 2.2 System Architecture & Workflow
The data path follows a modular, deeply pipelined approach separated into distinct phases:
1.  **Frontend (Fetch & Pre-Decode):** The processor fetches up to 4 instructions concurrently from the Instruction Memory. A pre-decode unit swiftly identifies branches and jumps to guide the early stages of control flow.
2.  **Rename & Dispatch Stage:** Fetched instructions enter the rename stage where the RAT updates data dependencies. Each instruction is provided a unique physical register destination. They are then dispatched simultaneously to the Issue Queue and the tail of the ROB.
3.  **Issue & Execute Stage:** Instructions reside in the Issue Queue, listening to the Common Data Bus (CDB) for their required physical operands. Once ready, they are issued to one of four parallel arithmetic logic units (ALUs) or the Load-Store unit, completely independent of their original fetch order.
4.  **Writeback & Commit Stage (Backend):** Upon completion, ALUs broadcast results across the CDB, waking up dependent instructions. Simultaneously, the execution results update the ROB. The ROB examines the oldest up to four instructions every cycle; if they are marked complete, it "commits" them cleanly to the final architectural state.

### 2.3 Tools & Technologies Used
*   **Verilog-2012:** Used for highly structural, synthesizable RTL descriptions of all processor components.
*   **Icarus Verilog:** The core simulation engine used to execute the RTL.
*   **cocotb (Coroutine based co-simulation):** A modern Python-based verification framework employed to build complex testbenches, generate dynamic clocks, auto-check expected architectural states, and gracefully handle wide superscalar state tracking in high-level Python.
*   **GTKWave:** Utilized for deep waveform analysis, timing verification, and tracking signals through the pipeline (such as tracking a 4x parallel fetch across cycles).
*   **Yosys / Xilinx Vivado:** Leveraged for logic synthesis and checking the target FPGA logic resource boundaries (LUT count analysis) and timing paths.

---

## 3. Results & Analysis

Extensive functional and stress-testing verification was performed using our cocotb environment across a variety of dense RISC-V instruction sequences.
*   **Throughput Benchmarks:** During intensive simulation runs (e.g., highly independent mathematical loops), the processor retired 553 instructions over 150 clock cycles. 
*   **Peak IPC Evaluation:** The execution yielded an Instruction Per Cycle (IPC) of **3.687**. This represents an exceptionally high utilization rate, nearly reaching the mathematical maximum of 4.0 for a 4-wide pipeline. By comparison, standard scalar 5-stage pipelines struggle to exceed ~0.8 IPC due to data hazards.
*   **Waveform Validation:** Time-series analysis in GTKWave definitively confirms instances of `commit_valid = 4'hF`, illustrating that four separate instruction commits physically resolve concurrently within a single clock cycle. It also successfully demonstrates non-blocking cache memory dependencies and seamless Register Alias Table recovery sequences during branch mispredictions.

---

## 4. Challenges & Learnings

### 4.1 Obstacles Faced
*   **Hazard Management Under Speculation:** Branch misprediction in an out-of-order machine is devastating if not handled appropriately. Unrolling the pipeline upon a misprediction involved not just flushing queues, but carefully orchestrating a synchronized rollback of the RAT to a safe checkpoint, matching the ROB.
*   **Memory Disambiguation:** Resolving memory hazards dynamically. Supporting Load bypassing (allowing a Load to execute before an older Store) while preventing Read-After-Write violations on identical memory addresses required a deeply intricate Load-Store Queue (LSQ).
*   **Design Complexity:** Routing the Common Data Bus (CDB) to forward operands globally across a 4-wide path incurred massive combinatorial logic depth, risking severe timing violations in synthesis.

### 4.2 Solutions & Insights
*   **Insight into State Rollbacks:** We discovered that instead of full RAT snapshotting, using the Reorder Buffer to sequentially un-rename registers from tail to head simplifies the architectural recovery process, trading slight latency for huge area savings.
*   **Overcoming Verification Limitations:** Standard Verilog testbenches became unmanageable for tracking OoO state. Re-writing our testbench inside `cocotb` enabled us to create dynamic python dictionaries to track expected register states, automatically querying the `$dumpvars` data streams and allowing scalable regression testing.

---

## 5. Conclusion & Applications

### 5.1 Final Takeaways
The transition from a basic pipelined core to a dynamically scheduled, 4-wide Out-of-Order processor radically shifts performance boundaries. We successfully demonstrated a functional RTL design achieving a **3.687 IPC throughput**, effectively yielding nearly 4x the computational density of historical single-issue architectures. The incorporation of a robust ROB and extensive PRF renaming successfully decoupled the execution timeline from the strict program order.

### 5.2 Real-World Applications
*   **High-Volume Compute Accelerators:** Ideal as an IP core for accelerating highly parallel numerical simulations, matrix manipulations, or cryptographic workloads.
*   **Edge AI & ML Processors:** Fast, high-throughput custom silicon forms the backbone of efficient machine learning inference chips requiring dense integer compute.
*   **Academic and Open-Source Baselines:** As an expansive representation of advanced superscalar architectures, this project serves as an educational framework for future embedded systems design.

---

## 6. Future Work & Enhancements
While this core successfully implements superscalar out-of-order execution, it provides a stable foundation for several future architectural enhancements:
*   **TAGE Branch Predictor:** Replacing the simple branch predictor with a Tagged Geometric (TAGE) predictor. This will significantly decrease misprediction rates on complex correlated branch patterns, keeping the 4-wide front-end fed effectively.
*   **Floating-Point Extensions (RV32F):** Synthesizing and integrating FPALUs to accommodate standard scientific and data-science workloads natively.
*   **Advanced Cache Hierarchy:** Upgrading the current flat memory model to include blocking L1 instruction and data caches, backed by an L2 coherent interconnect for potential multi-core expansion.

---

## 7. References
1.  Patterson, D. A., & Hennessy, J. L. *"Computer Architecture: A Quantitative Approach"* (6th Edition). Morgan Kaufmann.
2.  Waterman, A., & Asanović, K. *"The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA"*. RISC-V Foundation.
3.  Tomasulo, R. M. *"An Efficient Algorithm for Exploiting Multiple Arithmetic Units"*. IBM Journal of Research and Development. 
4.  Smith, J. E., & Pleszkun, A. R. *"Implementing Precise Interrupts in Pipelined Processors"*. IEEE Transactions on Computers.
