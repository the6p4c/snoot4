from amaranth import Array, Cat, Module, Mux, Signal
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

    op1: In(32)  # Rm
    op2: In(32)  # Rn
    result: Out(32)  # Rn

    ti: In(1)
    to: Out(1)

    def elaborate(self, platform):
        m = Module()

        op1 = self.op1
        op2 = self.op2
        ti = self.ti

        sel = self.sel
        sel_inv = sel[1:3] != 0b00
        sel_carry = sel[0]

        op1_ = Mux(sel_inv, ~op1, op1)
        carry_in = sel_inv ^ (sel_carry & ti)

        result = Signal(33)
        m.d.comb += result.eq(op1_ + op2 + carry_in)

        flag_carry = Signal()
        flag_overflow = Signal()
        m.d.comb += [
            flag_carry.eq(result[32] ^ sel_inv),
            flag_overflow.eq(~(op1_[31] ^ op2[31]) & result[32]),
        ]

        to = Signal()
        with m.Switch(self.flags_sel):
            with m.Case(ArithFlagsSel.CARRY):
                m.d.comb += to.eq(flag_carry)
            with m.Case(ArithFlagsSel.OVERFLOW):
                m.d.comb += to.eq(flag_overflow)

        m.d.comb += [
            self.result.eq(result),
            self.to.eq(to),
        ]

        return m
