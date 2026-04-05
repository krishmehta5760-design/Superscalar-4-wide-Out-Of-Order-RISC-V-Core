import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import os
import json

@cocotb.test()
async def run_processor(dut):
    """Basic Cocotb test that drives the clock and reset for the OoO core."""
    
    # 1. Start Clock (10ns period -> 100MHz)
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())
    
    # 2. Extract configuration from environment
    # Default to 50 cycles if not specified
    max_cycles = int(os.environ.get("SIM_CYCLES", "50"))
    
    dut._log.info(f"Starting simulation for {max_cycles} cycles.")
    
    # 3. Apply Reset Sequence
    dut.rst.value = 0
    await Timer(15, units="ns")
    dut.rst.value = 1
    
    # State Trackers
    commits = 0
    flushes = 0
    stalls = 0
    arch_regs = {}
    
    # 4. Let the processor run
    for cycle in range(max_cycles):
        await RisingEdge(dut.clk)
        
        # Track pipeline metrics (from ROB 'm' instance and TOP)
        try:
            # Check for up to 4 committed architectural register writes
            try:
                c_val = int(dut.commit_valid.value)
                if c_val & 1:
                    rd_addr = int(dut.commit_rd_0.value)
                    rd_data = int(dut.commit_data_0.value)
                    if rd_addr != 0:
                        arch_regs[rd_addr] = rd_data
                        dut._log.info(f"[COMMIT cycle={cycle}] x{rd_addr} = {rd_data}")
                if c_val & 2:
                    rd_addr = int(dut.commit_rd_1.value)
                    rd_data = int(dut.commit_data_1.value)
                    if rd_addr != 0:
                        arch_regs[rd_addr] = rd_data
                        dut._log.info(f"[COMMIT cycle={cycle}] x{rd_addr} = {rd_data}")
                if c_val & 4:
                    rd_addr = int(dut.commit_rd_2.value)
                    rd_data = int(dut.commit_data_2.value)
                    if rd_addr != 0:
                        arch_regs[rd_addr] = rd_data
                        dut._log.info(f"[COMMIT cycle={cycle}] x{rd_addr} = {rd_data}")
                if c_val & 8:
                    rd_addr = int(dut.commit_rd_3.value)
                    rd_data = int(dut.commit_data_3.value)
                    if rd_addr != 0:
                        arch_regs[rd_addr] = rd_data
                        dut._log.info(f"[COMMIT cycle={cycle}] x{rd_addr} = {rd_data}")
            except Exception:
                pass
                    
            try:
                # ROB pops up to 4 instructions! We use the combinational num_commits wire
                num_c = int(dut.m.num_commits.value)
                commits += num_c
            except Exception:
                pass
                
            if dut.flush.value == 1:
                flushes += 1
                
            if dut.stall.value == 1:
                stalls += 1
        except Exception:
            pass # signals might be 'x' or 'z' on first cycles
        
    dut._log.info(f"Simulation completed {max_cycles} cycles.")
    
    ipc = commits / max_cycles if max_cycles > 0 else 0
    
    results = {
        "status": "success",
        "cycles_run": max_cycles,
        "summary": {
            "total_commits": commits,
            "total_flushes": flushes,
            "stall_cycles": stalls,
            "ipc": round(ipc, 3)
        },
        "arch_regs": arch_regs,
        "message": "Processor simulated successfully with metrics."
    }
    
    with open("results.json", "w") as f:
        json.dump(results, f, indent=4)
