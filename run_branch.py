import sys
from wrapper import OoOCoreWrapper
import programs

wrapper = OoOCoreWrapper()
instructions = programs.PROGRAMS['branch_test']['instructions']
cycles = programs.PROGRAMS['branch_test']['cycles']

results = wrapper.run(instructions, cycles=cycles)
import os
results_path = os.path.join(wrapper.workspace_dir, "results.json")
# but wait, wrapper.run() already returns the json objects and suppresses stdout!
# Let's modify wrapper.py instead.
