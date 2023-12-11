from amaranth import Cat, Module, Mux, Signal, Value
from amaranth.lib import enum
from amaranth.lib.wiring import Component, In, Out


class _AluReg:
    op1: In(32)
    op2: In(32)
    result: Out(32)


class _AluT:
    t: In(1)
    result_t: Out(1)


_L = 2
_ADD = 0b00 << _L
_LOGIC = 0b01 << _L
_EXTEND = 0b10 << _L
_SWAP = 0b11 << _L


class Alu(_AluReg, _AluT, Component):
    class Sel(enum.Enum):
        # TODO: can we automatically generate this from the unit selector enums?
        ADDV = _ADD | 0b00
        ADDC = _ADD | 0b01
        SUBV = _ADD | 0b10
        SUBC = _ADD | 0b11

        NOT = _LOGIC | 0b00
        AND = _LOGIC | 0b01
        XOR = _LOGIC | 0b10
        OR = _LOGIC | 0b11

        EXTUB = _EXTEND | 0b00
        EXTUW = _EXTEND | 0b01
        EXTSB = _EXTEND | 0b10
        EXTSW = _EXTEND | 0b11

        SWAPB = _SWAP | 0b00
        SWAPW = _SWAP | 0b01
        XTRCT = _SWAP | 0b10

    sel: In(Sel)

    def elaborate(self, platform):
        m = Module()
        m.submodules.add = add = AluAdd()
        m.submodules.logic = logic = AluLogic()
        m.submodules.extend = extend = AluExtend()
        m.submodules.swap = swap = AluSwap()

        units = [
            (_ADD, add),
            (_LOGIC, logic),
            (_EXTEND, extend),
            (_SWAP, swap),
        ]

        for unit_sel, unit in units:
            # === drive inputs ===
            m.d.comb += [
                unit.sel.eq(self.sel),
                unit.op1.eq(self.op1),
                unit.op2.eq(self.op2),
            ]
            if isinstance(unit, _AluT):
                m.d.comb += unit.t.eq(self.t)

            # === select result ===
            with m.If(self.sel[_L:] == Value.cast(unit_sel)[_L:]):
                m.d.comb += self.result.eq(unit.result)
                if isinstance(unit, _AluT):
                    m.d.comb += self.result_t.eq(unit.result_t)

        return m


class AluAdd(_AluReg, _AluT, Component):
    class Sel(enum.Enum):
        ADDV = 0b00
        ADDC = 0b01
        SUBV = 0b10
        SUBC = 0b11

    sel: In(Sel)

    def elaborate(self, platform):
        m = Module()

        # === selector decode ===
        sel_sub = Signal()
        sel_carry = Signal()
        m.d.comb += [
            sel_sub.eq(self.sel[1]),
            sel_carry.eq(self.sel[0]),
        ]

        # === addends ===
        add1 = Signal(32)
        add2 = Signal(32)
        carry = Signal()
        m.d.comb += [
            add1.eq(self.op1),
            add2.eq(Mux(sel_sub, ~self.op2, self.op2)),
            carry.eq(sel_sub ^ (sel_carry & self.t)),
        ]

        # === adder ===
        add1_sign = Signal()
        add2_sign = Signal()
        r_add = Signal(32)
        r_add_sign = Signal()
        m.d.comb += [
            add1_sign.eq(add1[31]),
            add2_sign.eq(add2[31]),
            Cat(r_add, r_add_sign).eq(add1 + add2 + carry),
        ]

        # === flags ===
        t_carry = Signal()
        t_overflow = Signal()
        m.d.comb += [
            t_carry.eq(r_add_sign ^ sel_sub),
            t_overflow.eq(~(add1_sign ^ add2_sign) & r_add_sign),
        ]

        # === result ===
        m.d.comb += [
            self.result.eq(r_add),
            self.result_t.eq(Mux(sel_carry, t_carry, t_overflow)),
        ]

        return m


class AluLogic(_AluReg, Component):
    class Sel(enum.Enum):
        NOT = 0b00
        AND = 0b01
        XOR = 0b10
        OR = 0b11

    sel: In(Sel)

    def elaborate(self, platform):
        m = Module()

        # === operations ===
        r_not = Signal(32)
        r_and = Signal(32)
        r_xor = Signal(32)
        r_or = Signal(32)
        m.d.comb += [
            r_not.eq(~self.op2),
            r_and.eq(self.op1 & self.op2),
            r_xor.eq(self.op1 ^ self.op2),
            r_or.eq(self.op1 | self.op2),
        ]

        # === result ===
        with m.Switch(self.sel):
            with m.Case(AluLogic.Sel.NOT):
                m.d.comb += self.result.eq(r_not)
            with m.Case(AluLogic.Sel.AND):
                m.d.comb += self.result.eq(r_and)
            with m.Case(AluLogic.Sel.XOR):
                m.d.comb += self.result.eq(r_xor)
            with m.Case(AluLogic.Sel.OR):
                m.d.comb += self.result.eq(r_or)

        return m


class AluExtend(_AluReg, Component):
    class Sel(enum.Enum):
        EXTUB = 0b00
        EXTUW = 0b01
        EXTSB = 0b10
        EXTSW = 0b11

    sel: In(Sel)

    def elaborate(self, platform):
        m = Module()

        # === selector decode ===
        sel_byte = Signal()
        sel_signed = Signal()
        m.d.comb += [
            sel_byte.eq(~self.sel[0]),
            sel_signed.eq(self.sel[1]),
        ]

        # === operations ===
        r_extxb = Signal(32)
        r_extxw = Signal(32)
        m.d.comb += [
            r_extxb.eq(Cat(self.op2[0:8], (self.op2[7] & sel_signed).replicate(24))),
            r_extxw.eq(Cat(self.op2[0:16], (self.op2[15] & sel_signed).replicate(16))),
        ]

        # === result ===
        m.d.comb += self.result.eq(Mux(sel_byte, r_extxb, r_extxw))

        return m


class AluSwap(_AluReg, Component):
    class Sel(enum.Enum):
        SWAPB = 0b00
        SWAPW = 0b01
        XTRCT = 0b10

    sel: In(Sel)

    def elaborate(self, platform):
        m = Module()

        # === selector decode ===
        sel_byte = Signal()
        sel_swap = Signal()
        m.d.comb += [
            sel_byte.eq(~self.sel[0]),
            sel_swap.eq(~self.sel[1]),
        ]

        # === swap operation ===
        r_swapb = Signal(32)
        r_swapw = Signal(32)
        r_swap = Signal(32)
        m.d.comb += [
            r_swapb.eq(Cat(self.op2[8:16], self.op2[0:8], self.op2[16:32])),
            r_swapw.eq(Cat(self.op2[16:32], self.op2[0:16])),
            r_swap.eq(Mux(sel_byte, r_swapb, r_swapw)),
        ]

        # === extract operation ===
        r_xtrct = Signal(32)
        m.d.comb += r_xtrct.eq(Cat(self.op1[16:32], self.op2[0:16]))

        # === result ===
        m.d.comb += self.result.eq(Mux(sel_swap, r_swap, r_xtrct))

        return m
