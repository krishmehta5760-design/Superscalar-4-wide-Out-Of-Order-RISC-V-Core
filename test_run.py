from wrapper import OoOCoreWrapper
import os

def main():
    # Ensure we are running from the wrapper directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    print("--- OoO RISC-V Wrapper Test ---")
    
    core = OoOCoreWrapper()
    
    # Let's run a simple program:
    # We will use some basic ADDI commands as a test (e.g. ADDI x1, x0, 5)
    # ADDI x1, x0, 5 -> 00500093 in Hex
    # ADDI x2, x1, 10 -> 00a08113 in Hex
    test_program = [
        0x00500093,
        0x00a08113,
        0x00000000 # NOPs or padding
    ]
    
    try:
        results = core.run(test_program, cycles=20)
        print("Results Dump:")
        print(results)
    except Exception as e:
        print(f"Failed to run test: {e}")

if __name__ == "__main__":
    main()
