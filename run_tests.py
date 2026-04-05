from wrapper import OoOCoreWrapper
from programs import PROGRAMS
import os

def run_all_tests():
    # Make sure we're in the wrapper directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("=" * 60)
    print(" OoO RISC-V Benchmark & Test Suite")
    print("=" * 60)

    # Initialize our newly built wrapper
    core = OoOCoreWrapper()

    # Pre-copy RTL once so it doesn't happen on every test iteration
    print("[Suite] Synchronizing RTL...")
    core._copy_rtl()

    # Prepare reporting table
    results_table = []
    
    for test_key, test_data in PROGRAMS.items():
        print(f"\n--- Running Test: {test_data['name']} ---")
        instructions = test_data["instructions"]
        recommended_cycles = test_data["cycles"]
        
        try:
            # We skip the wrapper's internal _copy_rtl since we did it above
            # For simplicity, we just use the wrapper's run method which does it anyway, but that's fine.
            res = core.run(instructions, cycles=recommended_cycles)
            
            summary = res.get("summary", {})
            ipc = summary.get("ipc", 0)
            stalls = summary.get("stall_cycles", 0)
            
            status = "PASS"
            results_table.append(f"{test_data['name'][:25]:<25} | {status:<5} | IPC: {ipc:<5.3f} | Stalls: {stalls}")
            
        except Exception as e:
            results_table.append(f"{test_data['name'][:25]:<25} | FAIL  | Error: {e}")
            print(f"[ERROR] Test failed: {e}")

    print("\n" + "=" * 60)
    print(" Final Test Suite Results")
    print("=" * 60)
    for res in results_table:
        print(res)
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
