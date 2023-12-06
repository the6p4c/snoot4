import pytest

from amaranth.hdl.dsl import Assert, Assume

from snoot4.be.units.arith import Arith
from snoot4.tests.utils import Spec, assertFormal


ArithSpec = Spec(Arith)


class AddSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = (Rn + Rm) & 0xFFFFFFFF

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.ADD),
            Assert(gate.result == gold_result),
        ]


class AddcSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm, T = gate.op1, gate.op2, gate.ti
        gold_result = (Rn + Rm + T) & 0xFFFFFFFF

        # based on software manual: checks if either addition would overflow
        carry_step1 = Rn > ((Rn + Rm) & 0xFFFFFFFF)
        carry_step2 = ((Rn + Rm) & 0xFFFFFFFF) > ((Rn + Rm + T) & 0xFFFFFFFF)
        gold_to = carry_step1 | carry_step2

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.ADDC),
            Assume(gate.flags_sel == Arith.FlagsSel.CARRY),
            Assert(gate.result == gold_result),
            Assert(gate.to == gold_to),
        ]


class AddvSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = (Rn + Rm) & 0xFFFFFFFF

        # based on software manual: check for signs that don't make sense
        ops_same_sign = (Rn.as_signed() >= 0) == (Rm.as_signed() >= 0)
        result_negative = (Rn.as_signed() + Rm.as_signed()) < 0
        gold_to = ops_same_sign & result_negative

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.ADD),
            Assume(gate.flags_sel == Arith.FlagsSel.OVERFLOW),
            Assert(gate.result == gold_result),
            Assert(gate.to == gold_to),
        ]


class SubSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = (Rn - Rm) & 0xFFFFFFFF

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.SUB),
            Assert(gate.result == gold_result),
        ]


class SubcSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm, T = gate.op1, gate.op2, gate.ti
        gold_result = (Rn - Rm - T) & 0xFFFFFFFF

        # based on software manual: checks if either subtraction would overflow
        carry_step1 = Rn < ((Rn - Rm) & 0xFFFFFFFF)
        carry_step2 = ((Rn - Rm) & 0xFFFFFFFF) < ((Rn - Rm - T) & 0xFFFFFFFF)
        gold_to = carry_step1 | carry_step2

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.SUBC),
            Assume(gate.flags_sel == Arith.FlagsSel.CARRY),
            Assert(gate.result == gold_result),
            Assert(gate.to == gold_to),
        ]


class SubvSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = (Rn - Rm) & 0xFFFFFFFF

        # based on software manual: check for signs that don't make sense
        ops_different_sign = (Rn.as_signed() >= 0) != (Rm.as_signed() >= 0)
        result_negative = (Rn.as_signed() - Rm.as_signed()) < 0
        gold_to = ops_different_sign & result_negative

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.SUB),
            Assume(gate.flags_sel == Arith.FlagsSel.OVERFLOW),
            Assert(gate.result == gold_result),
            Assert(gate.to == gold_to),
        ]


class CmpEqSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_to = Rn == Rm

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.SUB),
            Assume(gate.flags_sel == Arith.FlagsSel.EQ),
            Assert(gate.to == gold_to),
        ]


class CmpHsSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_to = Rn >= Rm

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.SUB),
            Assume(gate.flags_sel == Arith.FlagsSel.HS),
            Assert(gate.to == gold_to),
        ]


class CmpGeSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_to = Rn.as_signed() >= Rm.as_signed()

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.SUB),
            Assume(gate.flags_sel == Arith.FlagsSel.GE),
            Assert(gate.to == gold_to),
        ]


class CmpHiSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_to = Rn > Rm

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.SUB),
            Assume(gate.flags_sel == Arith.FlagsSel.HI),
            Assert(gate.to == gold_to),
        ]


class CmpGtSpec(ArithSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_to = Rn.as_signed() > Rm.as_signed()

        m.d.comb += [
            Assume(gate.sel == Arith.Sel.SUB),
            Assume(gate.flags_sel == Arith.FlagsSel.GT),
            Assert(gate.to == gold_to),
        ]


@pytest.mark.parametrize("spec", ArithSpec.specs)
def test_arith(spec, tmp_path):
    assertFormal(spec(), tmp_path)
