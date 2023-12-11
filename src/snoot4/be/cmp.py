from amaranth import Cat, Module, Signal
from amaranth.lib import enum
from amaranth.lib.wiring import Component, In, Out


class Cmp(Component):
    class Sel(enum.Enum):
        EQ = 0b0000

        HS = 0b0100
        HI = 0b0110
        GE = 0b0101
        GT = 0b0111

        CLR = 0b1100
        SET = 0b1101
        TST = 0b1110
        STR = 0b1111

    sel: In(Sel)

    op1: In(32)
    op2: In(32)

    t: Out(1)

    def elaborate(self, platform):
        m = Module()

        op1_sign = Signal()
        op2_sign = Signal()
        m.d.comb += [
            op1_sign.eq(self.op1[31]),
            op2_sign.eq(self.op2[31]),
        ]

        r_sub = Signal(32)
        r_sub_sign = Signal()
        r_and = Signal(32)
        r_xor = Signal(32)
        m.d.comb += [
            Cat(r_sub, r_sub_sign).eq(self.op1 - self.op2),
            r_and.eq(self.op1 & self.op2),
            r_xor.eq(self.op1 ^ self.op2),
        ]

        t_eq = Signal()
        t_hs = Signal()
        t_ge = Signal()
        t_tst = Signal()
        t_str = Signal()
        m.d.comb += [
            t_eq.eq(r_sub == 0),
            t_hs.eq(~r_sub_sign),
            t_ge.eq(~r_sub_sign ^ op1_sign ^ op2_sign),
            t_tst.eq(r_and == 0),
            t_str.eq(
                (r_xor[0:8] == 0)
                | (r_xor[8:16] == 0)
                | (r_xor[16:24] == 0)
                | (r_xor[24:32] == 0)
            ),
        ]

        with m.Switch(self.sel):
            with m.Case(Cmp.Sel.EQ):
                m.d.comb += self.t.eq(t_eq)

            with m.Case(Cmp.Sel.HS):
                m.d.comb += self.t.eq(t_hs)
            with m.Case(Cmp.Sel.HI):
                m.d.comb += self.t.eq(t_hs & ~t_eq)
            with m.Case(Cmp.Sel.GE):
                m.d.comb += self.t.eq(t_ge)
            with m.Case(Cmp.Sel.GT):
                m.d.comb += self.t.eq(t_ge & ~t_eq)

            with m.Case(Cmp.Sel.CLR):
                m.d.comb += self.t.eq(0)
            with m.Case(Cmp.Sel.SET):
                m.d.comb += self.t.eq(1)
            with m.Case(Cmp.Sel.TST):
                m.d.comb += self.t.eq(t_tst)
            with m.Case(Cmp.Sel.STR):
                m.d.comb += self.t.eq(t_str)

        return m
