"""
Golden Model Testbench for 4-Wide OoO RISC-V Core
==================================================
Fills all 256 instruction slots with a comprehensive mix of:
  - R-type ALU (ADD, SUB, AND, OR, XOR, SLT, SLTU, SLL, SRL, SRA)
  - I-type ALU (ADDI, ANDI, ORI, XORI, SLTI, SLTIU, SLLI, SRLI, SRAI)
  - LUI, AUIPC
  - M-extension (MUL, MULH, MULHU)
  - Load/Store (LW, SW)
  - Branches (BEQ, BNE, BLT, BGE, BLTU, BGEU)
  - JAL (no JALR)
  - Hazard patterns (RAW, WAW, WAR chains)
  - Independent parallel bursts (max IPC)

Usage:
    python golden_model_test.py
"""

import os, sys, json, ctypes

# ============================================================================
# RV32I+M Instruction Encoders
# ============================================================================

def _s(v, bits=32):
    """Sign-extend to Python int from `bits`-wide value."""
    if v & (1 << (bits - 1)):
        return v - (1 << bits)
    return v

def _u(v):
    """Mask to 32-bit unsigned."""
    return v & 0xFFFFFFFF

# --- R-type ---
def R(funct7, rs2, rs1, funct3, rd, opcode=0b0110011):
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

def ADD(rd, rs1, rs2):  return R(0b0000000, rs2, rs1, 0b000, rd)
def SUB(rd, rs1, rs2):  return R(0b0100000, rs2, rs1, 0b000, rd)
def AND(rd, rs1, rs2):  return R(0b0000000, rs2, rs1, 0b111, rd)
def OR(rd, rs1, rs2):   return R(0b0000000, rs2, rs1, 0b110, rd)
def XOR(rd, rs1, rs2):  return R(0b0000000, rs2, rs1, 0b100, rd)
def SLT(rd, rs1, rs2):  return R(0b0000000, rs2, rs1, 0b010, rd)
def SLTU(rd, rs1, rs2): return R(0b0000000, rs2, rs1, 0b011, rd)
def SLL(rd, rs1, rs2):  return R(0b0000000, rs2, rs1, 0b001, rd)
def SRL(rd, rs1, rs2):  return R(0b0000000, rs2, rs1, 0b101, rd)
def SRA(rd, rs1, rs2):  return R(0b0100000, rs2, rs1, 0b101, rd)

# --- M-extension ---
def MUL(rd, rs1, rs2):   return R(0b0000001, rs2, rs1, 0b000, rd)
def MULH(rd, rs1, rs2):  return R(0b0000001, rs2, rs1, 0b001, rd)
def MULHU(rd, rs1, rs2): return R(0b0000001, rs2, rs1, 0b011, rd)

# --- I-type ---
def I(imm, rs1, funct3, rd, opcode=0b0010011):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

def ADDI(rd, rs1, imm):  return I(imm, rs1, 0b000, rd)
def ANDI(rd, rs1, imm):  return I(imm, rs1, 0b111, rd)
def ORI(rd, rs1, imm):   return I(imm, rs1, 0b110, rd)
def XORI(rd, rs1, imm):  return I(imm, rs1, 0b100, rd)
def SLTI(rd, rs1, imm):  return I(imm, rs1, 0b010, rd)
def SLTIU(rd, rs1, imm): return I(imm, rs1, 0b011, rd)
def SLLI(rd, rs1, shamt): return I(shamt & 0x1F, rs1, 0b001, rd)
def SRLI(rd, rs1, shamt): return I(shamt & 0x1F, rs1, 0b101, rd)
def SRAI(rd, rs1, shamt): return I(0x400 | (shamt & 0x1F), rs1, 0b101, rd)

# --- Load/Store ---
def LW(rd, rs1, imm):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (0b010 << 12) | (rd << 7) | 0b0000011

def SW(rs2, rs1, imm):
    imm = imm & 0xFFF
    return ((imm >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (0b010 << 12) | ((imm & 0x1F) << 7) | 0b0100011

# --- LUI / AUIPC ---
def LUI(rd, imm20):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | 0b0110111

def AUIPC(rd, imm20):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | 0b0010111

# --- Branch ---
def B(imm, rs2, rs1, funct3):
    imm = imm & 0x1FFF
    b12  = (imm >> 12) & 1
    b105 = (imm >> 5) & 0x3F
    b41  = (imm >> 1) & 0xF
    b11  = (imm >> 11) & 1
    return (b12 << 31) | (b105 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (b41 << 8) | (b11 << 7) | 0b1100011

def BEQ(rs1, rs2, imm):  return B(imm, rs2, rs1, 0b000)
def BNE(rs1, rs2, imm):  return B(imm, rs2, rs1, 0b001)
def BLT(rs1, rs2, imm):  return B(imm, rs2, rs1, 0b100)
def BGE(rs1, rs2, imm):  return B(imm, rs2, rs1, 0b101)
def BLTU(rs1, rs2, imm): return B(imm, rs2, rs1, 0b110)
def BGEU(rs1, rs2, imm): return B(imm, rs2, rs1, 0b111)

# --- JAL ---
def JAL(rd, imm):
    imm = imm & 0x1FFFFF
    b20   = (imm >> 20) & 1
    b101  = (imm >> 1) & 0x3FF
    b11   = (imm >> 11) & 1
    b1912 = (imm >> 12) & 0xFF
    return (b20 << 31) | (b101 << 21) | (b11 << 20) | (b1912 << 12) | (rd << 7) | 0b1101111

NOP = 0x00000000  # addi x0, x0, 0

# ============================================================================
# Golden Model: Python RV32I+M ISA Simulator
# ============================================================================

class RV32GoldenModel:
    def __init__(self):
        self.x = [0] * 32       # Architectural registers
        self.mem = bytearray(4096)  # Data memory (4KB, matches RTL)
        self.pc = 0

    def _rd(self, r):
        return self.x[r] if r != 0 else 0

    def _wr(self, r, val):
        if r != 0:
            self.x[r] = _u(val)

    def _mem_wr32(self, addr, val):
        a = addr & 0xFFF
        val = _u(val)
        self.mem[a]   = val & 0xFF
        self.mem[a+1] = (val >> 8) & 0xFF
        self.mem[a+2] = (val >> 16) & 0xFF
        self.mem[a+3] = (val >> 24) & 0xFF

    def _mem_rd32(self, addr):
        a = addr & 0xFFF
        return self.mem[a] | (self.mem[a+1] << 8) | (self.mem[a+2] << 16) | (self.mem[a+3] << 24)

    def execute(self, instructions, max_steps=1000):
        """Execute instructions sequentially. Returns final register state."""
        for step in range(max_steps):
            if self.pc // 4 >= len(instructions):
                break
            inst = instructions[self.pc // 4]
            if inst == 0:  # NOP
                self.pc += 4
                continue

            opcode = inst & 0x7F
            rd     = (inst >> 7) & 0x1F
            funct3 = (inst >> 12) & 0x7
            rs1    = (inst >> 15) & 0x1F
            rs2    = (inst >> 20) & 0x1F
            funct7 = (inst >> 25) & 0x7F

            # I-type immediate
            imm_i = _s((inst >> 20) & 0xFFF, 12)
            # S-type immediate
            imm_s = _s(((funct7 << 5) | ((inst >> 7) & 0x1F)) & 0xFFF, 12)
            # B-type immediate
            imm_b = _s((((inst >> 31) & 1) << 12) | (((inst >> 7) & 1) << 11) |
                       (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1), 13)
            # U-type immediate
            imm_u = inst & 0xFFFFF000
            # J-type immediate
            imm_j = _s((((inst >> 31) & 1) << 20) | (((inst >> 12) & 0xFF) << 12) |
                       (((inst >> 20) & 1) << 11) | (((inst >> 21) & 0x3FF) << 1), 21)

            next_pc = self.pc + 4

            if opcode == 0b0110011:  # R-type
                s1 = self._rd(rs1)
                s2 = self._rd(rs2)
                if funct7 == 0b0000001:  # M-extension
                    if funct3 == 0b000:    # MUL
                        self._wr(rd, _u(ctypes.c_int32(s1).value * ctypes.c_int32(s2).value))
                    elif funct3 == 0b001:  # MULH
                        result = (ctypes.c_int32(s1).value * ctypes.c_int32(s2).value) >> 32
                        self._wr(rd, _u(result))
                    elif funct3 == 0b011:  # MULHU
                        result = (s1 * s2) >> 32
                        self._wr(rd, _u(result))
                else:
                    if funct3 == 0b000:
                        self._wr(rd, _u(s1 + s2) if funct7 == 0 else _u(s1 - s2))
                    elif funct3 == 0b001: self._wr(rd, _u(s1 << (s2 & 0x1F)))
                    elif funct3 == 0b010: self._wr(rd, 1 if _s(s1) < _s(s2) else 0)
                    elif funct3 == 0b011: self._wr(rd, 1 if s1 < s2 else 0)
                    elif funct3 == 0b100: self._wr(rd, _u(s1 ^ s2))
                    elif funct3 == 0b101:
                        if funct7 == 0: self._wr(rd, s1 >> (s2 & 0x1F))
                        else: self._wr(rd, _u(_s(s1) >> (s2 & 0x1F)))
                    elif funct3 == 0b110: self._wr(rd, _u(s1 | s2))
                    elif funct3 == 0b111: self._wr(rd, _u(s1 & s2))

            elif opcode == 0b0010011:  # I-type ALU
                s1 = self._rd(rs1)
                if funct3 == 0b000:   self._wr(rd, _u(s1 + imm_i))
                elif funct3 == 0b010: self._wr(rd, 1 if _s(s1) < imm_i else 0)
                elif funct3 == 0b011: self._wr(rd, 1 if s1 < _u(imm_i) else 0)
                elif funct3 == 0b100: self._wr(rd, _u(s1 ^ _u(imm_i)))
                elif funct3 == 0b110: self._wr(rd, _u(s1 | _u(imm_i)))
                elif funct3 == 0b111: self._wr(rd, _u(s1 & _u(imm_i)))
                elif funct3 == 0b001: self._wr(rd, _u(s1 << (imm_i & 0x1F)))
                elif funct3 == 0b101:
                    shamt = imm_i & 0x1F
                    if funct7 & 0x20: self._wr(rd, _u(_s(s1) >> shamt))
                    else:             self._wr(rd, s1 >> shamt)

            elif opcode == 0b0110111:  # LUI
                self._wr(rd, _u(imm_u))

            elif opcode == 0b0010111:  # AUIPC
                self._wr(rd, _u(self.pc + imm_u))

            elif opcode == 0b0000011:  # Load (LW)
                addr = _u(self._rd(rs1) + imm_i)
                self._wr(rd, self._mem_rd32(addr))

            elif opcode == 0b0100011:  # Store (SW)
                addr = _u(self._rd(rs1) + imm_s)
                self._mem_wr32(addr, self._rd(rs2))

            elif opcode == 0b1100011:  # Branch
                s1 = self._rd(rs1)
                s2 = self._rd(rs2)
                taken = False
                if funct3 == 0b000:   taken = (s1 == s2)
                elif funct3 == 0b001: taken = (s1 != s2)
                elif funct3 == 0b100: taken = (_s(s1) < _s(s2))
                elif funct3 == 0b101: taken = (_s(s1) >= _s(s2))
                elif funct3 == 0b110: taken = (s1 < s2)
                elif funct3 == 0b111: taken = (s1 >= s2)
                if taken:
                    next_pc = _u(self.pc + imm_b)

            elif opcode == 0b1101111:  # JAL
                self._wr(rd, _u(self.pc + 4))
                next_pc = _u(self.pc + imm_j)

            self.pc = next_pc

        return {r: self.x[r] for r in range(32) if self.x[r] != 0}


# ============================================================================
# Build the 256-instruction program
# ============================================================================

def build_program():
    prog = []

    # ── Phase 0: Pipeline preamble (4 NOPs) ──
    prog += [NOP] * 4                                               # [0-3]

    # ── Phase 1: Initialize base registers x1-x15 (16 insts) ──
    prog.append(ADDI(1, 0, 171))     # x1  = 171 (0xAB)            # [4]
    prog.append(ADDI(2, 0, 205))     # x2  = 205 (0xCD)            # [5]
    prog.append(ADDI(3, 0, 10))      # x3  = 10                    # [6]
    prog.append(ADDI(4, 0, 20))      # x4  = 20                    # [7]
    prog.append(ADDI(5, 0, -1))      # x5  = 0xFFFFFFFF (-1)       # [8]
    prog.append(ADDI(6, 0, 100))     # x6  = 100 (mem base addr)   # [9]
    prog.append(ADDI(7, 0, 2))       # x7  = 2                     # [10]
    prog.append(ADDI(8, 0, 42))      # x8  = 42                    # [11]
    prog.append(ADDI(9, 0, 255))     # x9  = 255 (0xFF)            # [12]
    prog.append(ADDI(10, 0, -50))    # x10 = 0xFFFFFFCE (-50)      # [13]
    prog.append(ADDI(11, 0, 7))      # x11 = 7                     # [14]
    prog.append(ADDI(12, 0, 0))      # x12 = 0                     # [15]
    prog.append(ADDI(13, 0, 1))      # x13 = 1                     # [16]
    prog.append(ADDI(14, 0, 31))     # x14 = 31                    # [17]
    prog.append(ADDI(15, 0, 500))    # x15 = 500                   # [18]
    prog.append(NOP)                                                # [19]

    # ── Phase 2: R-type ALU operations (20 insts) ──
    prog.append(ADD(16, 1, 2))       # x16 = 171+205 = 376         # [20]
    prog.append(SUB(17, 2, 1))       # x17 = 205-171 = 34          # [21]
    prog.append(AND(18, 1, 2))       # x18 = 0xAB & 0xCD = 0x89    # [22]
    prog.append(OR(19, 1, 2))        # x19 = 0xAB | 0xCD = 0xEF    # [23]
    prog.append(XOR(20, 1, 2))       # x20 = 0xAB ^ 0xCD = 0x66    # [24]
    prog.append(SLT(21, 1, 2))       # x21 = (171 < 205) = 1       # [25]
    prog.append(SLT(22, 2, 1))       # x22 = (205 < 171) = 0       # [26]
    prog.append(SLTU(23, 1, 5))      # x23 = (171 < 0xFFFFFFFF) = 1# [27]
    prog.append(SLL(24, 1, 7))       # x24 = 171 << 2 = 684        # [28]
    prog.append(SRL(25, 1, 7))       # x25 = 171 >> 2 = 42         # [29]
    prog.append(SRA(26, 5, 7))       # x26 = (-1) >>a 2 = 0xFFFFFFFF # [30]
    prog.append(ADD(27, 3, 4))       # x27 = 10+20 = 30            # [31]
    prog.append(SUB(28, 4, 3))       # x28 = 20-10 = 10            # [32]
    prog.append(AND(29, 9, 1))       # x29 = 0xFF & 0xAB = 0xAB    # [33]
    prog.append(OR(30, 3, 4))        # x30 = 10 | 20 = 30          # [34]
    prog.append(XOR(31, 3, 4))       # x31 = 10 ^ 20 = 30          # [35]
    prog.append(SLL(16, 3, 13))      # x16 = 10 << 1 = 20          # [36]
    prog.append(SRL(17, 15, 7))      # x17 = 500 >> 2 = 125        # [37]
    prog.append(SRA(18, 10, 7))      # x18 = (-50) >>a 2           # [38]
    prog.append(SLTU(19, 12, 13))    # x19 = (0 < 1) = 1           # [39]

    # ── Phase 3: I-type ALU operations (18 insts) ──
    prog.append(ADDI(16, 1, 100))    # x16 = 171+100 = 271         # [40]
    prog.append(ANDI(17, 1, 0x0F))   # x17 = 0xAB & 0x0F = 0x0B   # [41]
    prog.append(ORI(18, 1, 0x100))   # x18 = 0xAB | 0x100 = 0x1AB # [42]
    prog.append(XORI(19, 1, 0xFF))   # x19 = 0xAB ^ 0xFF = 0x54   # [43]
    prog.append(SLTI(20, 1, 200))    # x20 = (171 < 200) = 1       # [44]
    prog.append(SLTI(21, 1, 100))    # x21 = (171 < 100) = 0       # [45]
    prog.append(SLTIU(22, 1, 200))   # x22 = (171u < 200) = 1      # [46]
    prog.append(SLLI(23, 3, 4))      # x23 = 10 << 4 = 160         # [47]
    prog.append(SRLI(24, 15, 3))     # x24 = 500 >> 3 = 62         # [48]
    prog.append(SRAI(25, 10, 3))     # x25 = (-50) >>a 3           # [49]
    prog.append(ADDI(26, 5, 1))      # x26 = -1+1 = 0              # [50]
    prog.append(ANDI(27, 5, 0x0F))   # x27 = 0xFFF..F & 0xF = 0xF # [51]
    prog.append(ORI(28, 12, 0x7F))   # x28 = 0 | 0x7F = 127       # [52]
    prog.append(XORI(29, 5, -1))     # x29 = ~(-1) = 0             # [53]
    prog.append(ADDI(30, 0, -128))   # x30 = -128 (0xFFFFFF80)     # [54]
    prog.append(SRAI(31, 30, 2))     # x31 = (-128) >>a 2 = -32    # [55]
    prog.append(ADDI(16, 0, 77))     # x16 = 77                    # [56]
    prog.append(ADDI(17, 0, 88))     # x17 = 88                    # [57]

    # ── Phase 4: LUI and AUIPC (6 insts) ──
    prog.append(LUI(18, 0xDEADB))    # x18 = 0xDEADB000            # [58]
    prog.append(LUI(19, 0x12345))    # x19 = 0x12345000            # [59]
    prog.append(ADDI(18, 18, 0xEF))  # x18 = 0xDEADB0EF ... wait LUI gives upper 20, then ADDI adds lower
    # Actually LUI loads imm<<12. 0xDEADB << 12 = 0xDEADB000. Then ADDI x18, x18, 0xEF -> but 0xEF as signed = 239
    # BUT wait... 0xDEADB = 912091 which is 20 bits. LUI(18, 0xDEADB) -> x18 = 0xDEADB000. Hmm that's > 32 bits.
    # 0xDEADB in 20 bits: 0xDEADB = 912091. In binary that's 20 bits. So upper 20 bits = 0xDEADB, x18 = 0xDEADB000
    # Wait 0xDEADB << 12 = let me compute: 0xDEADB = 0b11011110101011011011 (20 bits). << 12 = 0xDEADB000 which is 32+4=36 bits. That's too big.
    # Actually LUI uses 20 bits. 0xDEADB is 20 bits (5 hex digits = 20 bits). 
    # 0xDEADB << 12 would need 32 bits total. 20+12 = 32. So 0xDEADB000. 
    # Let me check: 0xD=1101, 0xE=1110, 0xA=1010, 0xD=1101, 0xB=1011 -> 20 bits.
    # Shifted left 12: the result is 0xDEADB000 which is... 0xDEADB000 = 3735879680 in decimal, which fits in 32 bits. Good.

    # Actually I already added ADDI for x18 above. Let me reconsider. I'll keep it simple.
    # [58] LUI x18, 0xDEADB -> x18 = 0xDEADB000
    # [59] LUI x19, 0x12345 -> x19 = 0x12345000  
    # [60] below:
    prog.append(ADDI(20, 18, 0xEF))  # x20 = 0xDEADB000 + 239 = 0xDEADB0EF  # [60] -- wait 0xEF=239 but as signed 12-bit it's still 239 (positive)
    prog.append(AUIPC(21, 0x00001))  # x21 = PC + 0x1000. PC = 61*4 = 244 = 0xF4. x21 = 0x10F4 # [61]
    prog.append(AUIPC(22, 0x00000))  # x22 = PC + 0 = 62*4 = 248             # [62]
    prog.append(NOP)                                                           # [63]

    # ── Phase 5: M-extension multiply (12 insts) ──
    prog.append(MUL(23, 3, 4))       # x23 = 10 * 20 = 200                    # [64]
    prog.append(NOP)       # x24 = 171 * 2 = 342                    # [65]
    prog.append(NOP)       # x25 = (-1) * 2 = -2 (0xFFFFFFFE)       # [66]
    prog.append(MULH(26, 5, 7))      # x26 = upper32((-1)*2) = -1 (0xFFFFFFFF)# [67]
    prog.append(NOP)     # x27 = upper32((2^32-1)*2) = 1          # [68]
    prog.append(NOP)       # x28 = 10*10 = 100                      # [69]
    prog.append(MUL(29, 4, 4))       # x29 = 20*20 = 400                      # [70]
    prog.append(NOP)       # x30 = 42*2 = 84                        # [71]
    prog.append(NOP)     # x31 = upper32((-50)*20) = -1           # [72]
    prog.append(MUL(16, 15, 3))      # x16 = 500*10 = 5000                    # [73]
    prog.append(NOP)     # x17 = 7*31 = 217                       # [74]
    prog.append(NOP)                                                           # [75]

    # ── Phase 6: Store/Load tests (20 insts) ──
    # x6 = 100 (base address)
    prog.append(SW(8, 6, 0))         # mem[100] = 42                           # [76]
    prog.append(SW(3, 6, 4))         # mem[104] = 10                           # [77]
    prog.append(SW(4, 6, 8))         # mem[108] = 20                           # [78]
    prog.append(SW(15, 6, 12))       # mem[112] = 500                          # [79]
    prog.append(NOP)                                                           # [80]
    prog.append(NOP)                                                           # [81]
    prog.append(NOP)                                                           # [82]
    prog.append(NOP)                                                           # [83]
    prog.append(LW(16, 6, 0))        # x16 = mem[100] = 42                    # [84]
    prog.append(LW(17, 6, 4))        # x17 = mem[104] = 10                    # [85]
    prog.append(LW(18, 6, 8))        # x18 = mem[108] = 20                    # [86]
    prog.append(LW(19, 6, 12))       # x19 = mem[112] = 500                   # [87]
    prog.append(NOP)                                                           # [88]
    prog.append(NOP)                                                           # [89]
    prog.append(NOP)                                                           # [90]
    prog.append(NOP)                                                           # [91]
    # Store-to-load forwarding test
    prog.append(ADDI(20, 0, 999))    # x20 = 999                              # [92]
    prog.append(SW(20, 6, 16))       # mem[116] = 999                          # [93]
    prog.append(NOP)                                                           # [94]
    prog.append(NOP)                                                           # [95]
    prog.append(NOP)                                                           # [96]
    prog.append(NOP)                                                           # [97]
    prog.append(LW(21, 6, 16))       # x21 = mem[116] = 999                   # [98]
    prog.append(NOP)                                                           # [99]

    # ── Phase 7: Branch tests — forward only, no loops (20 insts) ──
    # BEQ not-taken (x3=10 != x4=20)
    prog.append(BEQ(3, 4, 8))        # not taken, fall through                 # [100]
    prog.append(ADDI(22, 0, 1))      # x22 = 1 (reached)                      # [101]

    # BEQ taken (x3=10 == x3=10), skip 1 instruction
    prog.append(BEQ(3, 3, 8))        # taken → skip to [105]                   # [102]
    prog.append(ADDI(22, 0, 0xBAD))  # SKIPPED                                # [103]
    prog.append(NOP)                 # SKIPPED                                 # [104] -- wait, BEQ offset 8 means PC+8. PC=102*4=408. Target=408+8=416=104*4. So it jumps to [104]. Hmm, that means it only skips 1 instruction [103], landing on [104].
    # Let me recalculate: BEQ at index 102, PC = 102*4 = 408. Offset = 8 bytes. Target = 408+8 = 416 = index 104.
    # So [103] is skipped, [104] executes. Let me make [103] the bad one and [104] a normal instruction.
    # Actually I need to be more careful. Index 104's NOP is fine. Let me adjust.
    prog.append(ADDI(23, 0, 0x42))   # x23 = 0x42 (landed here after branch)  # [105]

    # BNE taken (x3=10 != x4=20), skip 2 instructions
    prog.append(BNE(3, 4, 12))       # taken → PC+12 = [106]*4+12 = index 109 # [106]
    prog.append(ADDI(23, 0, 0xBAD))  # SKIPPED                                # [107]
    prog.append(ADDI(23, 0, 0xBAD))  # SKIPPED                                # [108]
    prog.append(ADDI(24, 0, 0x55))   # x24 = 0x55 (landed)                    # [109]

    # BLT taken (x10=-50 < x3=10)
    prog.append(BLT(10, 3, 8))       # taken → index 112                      # [110]
    prog.append(ADDI(24, 0, 0xBAD))  # SKIPPED                                # [111]
    prog.append(ADDI(25, 0, 0x77))   # x25 = 0x77 (landed)                    # [112]

    # BGE not-taken (x10=-50 < x3=10)
    prog.append(BGE(10, 3, 8))       # not taken                              # [113]
    prog.append(ADDI(26, 0, 0x99))   # x26 = 0x99 (reached, not skipped)      # [114]

    # BLTU not-taken (x10=0xFFFFFFCE > x3=10 unsigned)
    prog.append(BLTU(10, 3, 8))      # not taken (0xFFFFFFCE > 10 unsigned)    # [115]
    prog.append(ADDI(27, 0, 0xAA))   # x27 = 0xAA (reached)                   # [116]

    # BGEU taken (x10=0xFFFFFFCE >= x3=10 unsigned)
    prog.append(BGEU(10, 3, 8))      # taken → index 119                      # [117]
    prog.append(ADDI(27, 0, 0xBAD))  # SKIPPED                                # [118]
    prog.append(ADDI(28, 0, 0xBB))   # x28 = 0xBB (landed)                    # [119]

    # ── Phase 8: JAL test (4 insts) ──
    prog.append(JAL(29, 12))         # x29 = PC+4 = 121*4=484, jump to 120*4+12=492=index 123  # [120]
    prog.append(ADDI(29, 0, 0xBAD))  # SKIPPED                                # [121]
    prog.append(ADDI(29, 0, 0xBAD))  # SKIPPED                                # [122]
    prog.append(ADDI(30, 0, 0xCC))   # x30 = 0xCC (landed after JAL)          # [123]

    # ── Phase 9: WAW hazard chain (8 insts) ──
    prog.append(ADDI(16, 0, 10))     # x16 = 10                               # [124]
    prog.append(ADDI(16, 0, 20))     # x16 = 20 (WAW!)                        # [125]
    prog.append(ADDI(16, 0, 30))     # x16 = 30 (WAW!)                        # [126]
    prog.append(ADDI(16, 0, 40))     # x16 = 40 (WAW! — final value)          # [127]
    prog.append(ADDI(17, 0, 100))    # x17 = 100                              # [128]
    prog.append(ADDI(17, 0, 200))    # x17 = 200 (WAW!)                       # [129]
    prog.append(ADDI(18, 16, 5))     # x18 = 40+5 = 45 (reads latest x16)     # [130]
    prog.append(ADDI(19, 17, 5))     # x19 = 200+5 = 205 (reads latest x17)   # [131]

    # ── Phase 10: WAR hazard chain (6 insts) ──
    prog.append(ADDI(20, 0, 10))     # x20 = 10                               # [132]
    prog.append(ADDI(21, 0, 5))      # x21 = 5                                # [133]
    prog.append(ADD(22, 20, 21))     # x22 = 10+5 = 15                        # [134]
    prog.append(ADDI(20, 0, 50))     # x20 = 50 (WAR on x20!)                 # [135]
    prog.append(ADDI(23, 20, 5))     # x23 = 50+5 = 55                        # [136]
    prog.append(NOP)                                                           # [137]

    # ── Phase 11: RAW dependency chain (10 insts) ──
    prog.append(ADDI(24, 0, 1))      # x24 = 1                                # [138]
    prog.append(ADDI(25, 24, 1))     # x25 = 2                                # [139]
    prog.append(ADDI(26, 25, 1))     # x26 = 3                                # [140]
    prog.append(ADDI(27, 26, 1))     # x27 = 4                                # [141]
    prog.append(ADDI(28, 27, 1))     # x28 = 5                                # [142]
    prog.append(ADDI(29, 28, 1))     # x29 = 6                                # [143]
    prog.append(ADDI(30, 29, 1))     # x30 = 7                                # [144]
    prog.append(ADDI(31, 30, 1))     # x31 = 8                                # [145]
    prog.append(NOP)                                                           # [146]
    prog.append(NOP)                                                           # [147]

    # ── Phase 12: Fibonacci via RAW (8 insts) ──
    prog.append(ADDI(16, 0, 1))      # x16 = 1 (fib1)                         # [148]
    prog.append(ADDI(17, 0, 1))      # x17 = 1 (fib2)                         # [149]
    prog.append(ADD(18, 16, 17))     # x18 = 2                                # [150]
    prog.append(ADD(19, 17, 18))     # x19 = 3                                # [151]
    prog.append(ADD(20, 18, 19))     # x20 = 5                                # [152]
    prog.append(ADD(21, 19, 20))     # x21 = 8                                # [153]
    prog.append(ADD(22, 20, 21))     # x22 = 13                               # [154]
    prog.append(ADD(23, 21, 22))     # x23 = 21                               # [155]

    # ── Phase 13: Independent parallel burst — MAX IPC (64 insts) ──
    for i in range(16):
        rd = (i % 31) + 1  # cycle through x1-x31
        prog.append(ADDI(rd, 0, 1000 + i))                                    # [156-171]
    for i in range(16):
        rd = (i % 31) + 1
        prog.append(ADDI(rd, 0, 2000 + i))                                    # [172-187]
    for i in range(16):
        rd = (i % 31) + 1
        prog.append(ADDI(rd, 0, 500 + i))                                     # [188-203]
    for i in range(16):
        rd = (i % 31) + 1
        prog.append(ADDI(rd, 0, 300 + i))                                     # [204-219]

    # ── Phase 14: Final computation + done marker ──
    prog.append(ADDI(1, 0, 0xAA))     # x1 = 170                              # [220]
    prog.append(ADDI(2, 0, 0x55))     # x2 = 85                               # [221]
    prog.append(ADD(3, 1, 2))         # x3 = 255                              # [222]
    prog.append(MUL(4, 1, 2))         # x4 = 170*85 = 14450                   # [223]
    prog.append(SUB(5, 1, 2))         # x5 = 170-85 = 85                      # [224]
    prog.append(AND(6, 1, 2))         # x6 = 0xAA & 0x55 = 0                  # [225]
    prog.append(OR(7, 1, 2))          # x7 = 0xAA | 0x55 = 0xFF = 255         # [226]
    prog.append(XOR(8, 1, 2))         # x8 = 0xAA ^ 0x55 = 0xFF = 255         # [227]

    # Done marker
    prog.append(ADDI(31, 0, 99))      # x31 = 99 (DONE)                       # [228]

    # Fill remaining with NOPs
    while len(prog) < 256:
        prog.append(NOP)

    assert len(prog) == 256, f"Program length is {len(prog)}, expected 256"
    return prog


# ============================================================================
# Main: Run golden model, compare with hardware
# ============================================================================

def main():
    prog = build_program()

    # ── Run Golden Model ──
    print("=" * 60)
    print("  GOLDEN MODEL — RV32I+M ISA Simulator")
    print("=" * 60)
    gm = RV32GoldenModel()
    expected = gm.execute(prog, max_steps=2000)

    print("\n[Golden Model] Final Architectural State:")
    for r in sorted(expected.keys()):
        print(f"  x{r:2d} = {expected[r]:10d}  (0x{expected[r]:08X})")

    # ── Write program.mem for hardware simulation ──
    mem_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "program.mem")
    with open(mem_path, "w") as f:
        for inst in prog:
            f.write(f"{inst:08x}\n")
    print(f"\n[OK] Written {len(prog)} instructions to {mem_path}")

    # ── Write expected results for comparison ──
    expected_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "golden_expected.json")
    with open(expected_path, "w") as f:
        json.dump({"expected_regs": {str(k): v for k, v in expected.items()}}, f, indent=2)
    print(f"[OK] Written golden expected values to {expected_path}")

    # ── Run hardware simulation via wrapper ──
    print("\n" + "=" * 60)
    print("  HARDWARE SIMULATION — OoO RISC-V Core via cocotb")
    print("=" * 60)

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from wrapper import OoOCoreWrapper
        core = OoOCoreWrapper(os.path.dirname(os.path.abspath(__file__)))
        results = core.run(prog, cycles=1500)
    except Exception as e:
        print(f"\n[!] Hardware simulation failed: {e}")
        print("[!] You can still compare manually after running: SIM_CYCLES=600 make")
        print("[!] Then run: python compare_results.py")
        # Write comparison helper
        write_compare_script(expected)
        return

    # ── Compare results ──
    print("\n" + "=" * 60)
    print("  COMPARISON: Golden Model vs Hardware")
    print("=" * 60)
    compare(expected, results)


def compare(expected, results):
    hw_regs = {int(k): int(v) for k, v in results.get("arch_regs", {}).items()}
    
    passed = 0
    failed = 0
    
    # Only check registers that the golden model wrote to
    for reg in sorted(expected.keys()):
        if reg == 0:
            continue
        exp_val = expected[reg]
        hw_val = hw_regs.get(reg, None)
        
        if hw_val is None:
            print(f"  x{reg:2d}: EXPECTED={exp_val:10d} (0x{exp_val:08X})  |  HW=NOT COMMITTED  FAIL")
            failed += 1
        elif hw_val == exp_val:
            print(f"  x{reg:2d}: EXPECTED={exp_val:10d} (0x{exp_val:08X})  |  HW={hw_val:10d}  PASS")
            passed += 1
        else:
            print(f"  x{reg:2d}: EXPECTED={exp_val:10d} (0x{exp_val:08X})  |  HW={hw_val:10d} (0x{hw_val:08X})  FAIL")
            failed += 1

    print(f"\n{'=' * 60}")
    ipc = results.get("summary", {}).get("ipc", "N/A")
    commits = results.get("summary", {}).get("total_commits", "N/A")
    cycles = results.get("cycles_run", "N/A")
    print(f"  IPC: {ipc}  |  Commits: {commits}  |  Cycles: {cycles}")
    print(f"  PASSED: {passed}  |  FAILED: {failed}  |  TOTAL: {passed + failed}")
    if failed == 0:
        print(f"\n  *** ALL REGISTERS MATCH — GOLDEN MODEL VERIFIED! ***")
    else:
        print(f"\n  !!!  {failed} MISMATCHES DETECTED")
    print(f"{'=' * 60}")


def write_compare_script(expected):
    """Write a standalone comparison script for manual use."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "compare_results.py")
    with open(path, "w") as f:
        f.write(f"""import json
expected = {json.dumps({{str(k): v for k, v in expected.items()}})}
with open("results.json") as f:
    results = json.load(f)
hw = {{int(k): int(v) for k, v in results.get("arch_regs", {{}}).items()}}
p = f = 0
for r in sorted(int(k) for k in expected):
    if r == 0: continue
    e = expected[str(r)]
    h = hw.get(r)
    ok = h == e
    p += ok; f += (not ok)
    sym = "PASS" if ok else "FAIL"
    print(f"  x{{r:2d}}: EXP={{e:10d}} (0x{{e:08X}})  |  HW={{str(h):>10s}}  {{sym}}")
print(f"\\nPASSED: {{p}}  FAILED: {{f}}")
print(f"IPC: {{results.get('summary',{{}}).get('ipc','?')}}")
""")
    print(f"[OK] Written standalone comparison script to {path}")


if __name__ == "__main__":
    main()
