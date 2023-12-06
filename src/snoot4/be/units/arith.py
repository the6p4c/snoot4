from amaranth import Cat, Module, Mux, Signal
from amaranth.lib import enum
from amaranth.lib.wiring import Component, In, Out


class ArithSel(enum.Enum):
    # add: 0b00c
    #  c: add carry
    ADD = 0b000
    ADDC = 0b001

    # subtract: 0b01c
    #  c: subtract carry
    SUB = 0b010
    SUBC = 0b011

    # divide init: 0b10s
    #  ~u/s: ~unsigned/signed
    DIV0U = 0b100
    DIV0S = 0b101

    # divide step: 0b11x
    #  x: don't care
    DIV1 = 0b110


class ArithFlagsSel(enum.Enum):
    CARRY = 0
    OVERFLOW = 1
    EQ = 2
    HS = 3
    GE = 4
    HI = 5
    GT = 6


class Arith(Component):
    sel: In(ArithSel)
    flags_sel: In(ArithFlagsSel)

    op1: In(32)  # Rn
    op2: In(32)  # Rm
    result: Out(32)  # Rn

    ti: In(1)
    to: Out(1)

    def elaborate(self, platform):
        m = Module()

        # === selector decoding ===
        sel_inv = Signal()
        sel_carry = Signal()
        m.d.comb += [
            sel_inv.eq(self.sel[1:3] != 0b00),  # TODO: not generally correct
            sel_carry.eq(self.sel[0]),
        ]

        # === addend generation ===
        add1 = Signal(32)
        add2 = Signal(32)
        carry = Signal()
        m.d.comb += [
            add1.eq(self.op1),
            add2.eq(Mux(sel_inv, ~self.op2, self.op2)),
            carry.eq(sel_inv ^ (sel_carry & self.ti)),
        ]

        # === adder ===
        add1_sign = Signal()
        add2_sign = Signal()
        result_sign = Signal()
        m.d.comb += [
            add1_sign.eq(add1[31]),
            add2_sign.eq(add2[31]),
            Cat(self.result, result_sign).eq(add1 + add2 + carry),
        ]

        # === flags generation ===
        with m.Switch(self.flags_sel):
            with m.Case(ArithFlagsSel.CARRY):
                m.d.comb += self.to.eq(result_sign ^ sel_inv)
            with m.Case(ArithFlagsSel.OVERFLOW):
                m.d.comb += self.to.eq(~(add1_sign ^ add2_sign) & result_sign)
            with m.Case(ArithFlagsSel.EQ):
                m.d.comb += self.to.eq(self.result == 0)
            with m.Case(ArithFlagsSel.HS):
                m.d.comb += self.to.eq(result_sign)
            with m.Case(ArithFlagsSel.GE):
                m.d.comb += self.to.eq(~(result_sign ^ add1_sign ^ add2_sign))
            with m.Case(ArithFlagsSel.HI):
                m.d.comb += self.to.eq(result_sign & (self.result != 0))
            with m.Case(ArithFlagsSel.GT):
                m.d.comb += self.to.eq(
                    ~(result_sign ^ add1_sign ^ add2_sign) & (self.result != 0)
                )

        return m
