SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Hardcoded reference to the local RTL sources that wrapper.py copies
VERILOG_SOURCES = $(wildcard rtl/*.v)
export VERILOG_SOURCES

# Toplevel module in your Verilog
TOPLEVEL = TOP

# Python module for cocotb testbench
MODULE = sim_tb

# Allow parsing of SystemVerilog or advanced Verilog-2012 constructs just in case
COMPILE_ARGS += -g2012

# We must include the cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim
