from amaranth import Array, Cat, Module, Mux, Signal
from amaranth.lib import enum
from amaranth.lib.wiring import Component, In, Out


class Logic(Component):
    class Sel(enum.Enum):
        # bitwise: 0b00ii
        #  ii: index [NOT, AND, XOR, OR]
        NOT = 0b0000
        AND = 0b0001
        XOR = 0b0010
        OR = 0b0011

        # extract: 0b01xx
        #  x: don't care
        XTRCT = 0b0100

        # swap: 0b10xw
        #  x: don't care
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

    class FlagsSel(enum.Enum):
        ZERO = 0
        STR = 1

    sel: In(Sel)
    flags_sel: In(FlagsSel)

    op1: In(32)  # Rn
    op2: In(32)  # Rm
    result: Out(32)  # Rn

    to: Out(1)

    def elaborate(self, platform):
        m = Module()

        # === split operands into byte and word chunks ===
        op1 = self.op1
        op1_b23 = op1[16:32]

        op2 = self.op2
        op2_b0, op2_b1, op2_b2, op2_b3 = op2[0:8], op2[8:16], op2[16:24], op2[24:32]
        op2_b01, op2_b23 = op2[0:16], op2[16:32]

        # === partially decode selector ===
        sel = self.sel
        sel_byte = sel[0] == 0
        sel_unsigned = sel[1] == 0

        # === bitwise ===
        r_not = Signal(32)
        r_and = Signal(32)
        r_xor = Signal(32)
        r_or = Signal(32)
        r_bitwise = Signal(32)
        m.d.comb += [
            r_not.eq(~op2),
            r_and.eq(op1 & op2),
            r_xor.eq(op1 ^ op2),
            r_or.eq(op1 | op2),
            r_bitwise.eq(Lut(sel[0:2], [r_not, r_and, r_xor, r_or])),
        ]

        # === extract ===
        r_extract = Signal(32)
        m.d.comb += r_extract.eq(Cat(op1_b23, op2_b01))

        # === swap ===
        r_swapb = Signal(32)
        r_swapw = Signal(32)
        r_swap = Signal(32)
        m.d.comb += [
            r_swapb.eq(Cat(op2_b1, op2_b0, op2_b2, op2_b3)),
            r_swapw.eq(Cat(op2_b23, op2_b01)),
            r_swap.eq(Mux(sel_byte, r_swapb, r_swapw)),
        ]

        # === extend ===
        r_extb = Signal(32)
        r_extw = Signal(32)
        r_extend = Signal(32)
        m.d.comb += [
            r_extb.eq(Cat(op2_b0, Mux(sel_unsigned, 0, op2_b0[-1]).replicate(24))),
            r_extw.eq(Cat(op2_b01, Mux(sel_unsigned, 0, op2_b01[-1]).replicate(16))),
            r_extend.eq(Mux(sel_byte, r_extb, r_extw)),
        ]

        # === result ===
        m.d.comb += self.result.eq(
            Lut(sel[2:4], [r_bitwise, r_extract, r_swap, r_extend])
        )

        # === flags ===
        flag_zero = r_bitwise == 0
        flag_str = (
            (r_bitwise[0:8] == 0)
            | (r_bitwise[8:16] == 0)
            | (r_bitwise[16:24] == 0)
            | (r_bitwise[24:32] == 0)
        )
        m.d.comb += self.to.eq(
            Mux(self.flags_sel == Logic.FlagsSel.ZERO, flag_zero, flag_str)
        )

        return m


def Lut(sel, values):
    assert not sel.shape().signed
    assert 2 ** sel.shape().width == len(values)

    return Array(values)[sel]
