from amaranth import Array, Cat, Module, Mux, Signal
from amaranth.lib import enum
from amaranth.lib.wiring import Component, In, Out


class LogicSel(enum.Enum):
    # bitwise: 0b00xx
    NOT = 0b0000
    AND = 0b0001
    XOR = 0b0010
    OR = 0b0011

    # extract: 0b0100
    XTRCT = 0b0100

    # swap: 0b100w
    #  ~b/w = ~byte/word
    SWAPB = 0b1000
    SWAPW = 0b1001

    # extend: 0b11sw
    #  ~u/s = ~unsigned/signed
    #  ~b/w = ~byte/word
    EXTUB = 0b1100
    EXTUW = 0b1101
    EXTSB = 0b1110
    EXTSW = 0b1111


class Logic(Component):
    sel: In(LogicSel)

    op1: In(32)  # Rm
    op2: In(32)  # Rn
    result: Out(32)  # Rn

    def elaborate(self, platform):
        m = Module()
        op1 = self.op1
        op1_b0, op1_b1, op1_b2, op1_b3 = op1[0:8], op1[8:16], op1[16:24], op1[24:32]
        op1_b01, op1_b23 = op1[0:16], op1[16:32]

        op2 = self.op2
        op2_b23 = op2[16:32]

        sel = self.sel
        sel_is_byte = sel[0] == 0
        sel_is_unsigned = sel[1] == 0

        result_not = Signal(32)
        result_and = Signal(32)
        result_xor = Signal(32)
        result_or = Signal(32)
        result_bitwise = Signal(32)
        m.d.comb += [
            result_not.eq(~op1),
            result_and.eq(op1 & op2),
            result_xor.eq(op1 ^ op2),
            result_or.eq(op1 | op2),
            result_bitwise.eq(
                Array([result_not, result_and, result_xor, result_or])[sel[0:2]]
            ),
        ]

        result_extract = Signal(32)
        m.d.comb += result_extract.eq(Cat(op2_b23, op1_b01))

        result_swap = Signal(32)
        m.d.comb += result_swap.eq(
            Mux(
                sel_is_byte,
                Cat(op1_b1, op1_b0, op1_b2, op1_b3),
                Cat(op1_b23, op1_b01),
            )
        )

        result_extb = Signal(32)
        result_extw = Signal(32)
        result_extend = Signal(32)
        m.d.comb += [
            result_extb.eq(
                Cat(op1_b0, Mux(sel_is_unsigned, 0, op1_b0[-1]).replicate(24))
            ),
            result_extw.eq(
                Cat(op1_b01, Mux(sel_is_unsigned, 0, op1_b01[-1]).replicate(16))
            ),
            result_extend.eq(Mux(sel_is_byte, result_extb, result_extw)),
        ]

        with m.Switch(self.sel[2:4]):
            with m.Case(0):
                m.d.comb += self.result.eq(result_bitwise)
            with m.Case(1):
                m.d.comb += self.result.eq(result_extract)
            with m.Case(2):
                m.d.comb += self.result.eq(result_swap)
            with m.Case(3):
                m.d.comb += self.result.eq(result_extend)

        return m
