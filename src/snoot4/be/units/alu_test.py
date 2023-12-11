from amaranth import Mux
import pytest

from amaranth.hdl.dsl import Assert, Assume

from snoot4.be.units import Alu
from snoot4.tests.utils import Spec, assertFormal


AluSpec = Spec(Alu)


class AddvSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = (Rn + Rm) & 0xFFFFFFFF

        # based on software manual: check for signs that don't make sense
        ops_same_sign = (Rn.as_signed() >= 0) == (Rm.as_signed() >= 0)
        result_negative = (Rn.as_signed() + Rm.as_signed()) < 0
        gold_result_t = ops_same_sign & result_negative

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.ADDV),
            Assert(gate.result == gold_result),
            Assert(gate.result_t == gold_result_t),
        ]


class AddcSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm, T = gate.op1, gate.op2, gate.t
        gold_result = (Rn + Rm + T) & 0xFFFFFFFF

        # based on software manual: checks if either addition would overflow
        carry_step1 = Rn > ((Rn + Rm) & 0xFFFFFFFF)
        carry_step2 = ((Rn + Rm) & 0xFFFFFFFF) > ((Rn + Rm + T) & 0xFFFFFFFF)
        gold_result_t = carry_step1 | carry_step2

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.ADDC),
            Assert(gate.result == gold_result),
            Assert(gate.result_t == gold_result_t),
        ]


class SubvSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = (Rn - Rm) & 0xFFFFFFFF

        # based on software manual: check for signs that don't make sense
        ops_different_sign = (Rn.as_signed() >= 0) != (Rm.as_signed() >= 0)
        result_negative = (Rn.as_signed() - Rm.as_signed()) < 0
        gold_result_t = ops_different_sign & result_negative

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.SUBV),
            Assert(gate.result == gold_result),
            Assert(gate.result_t == gold_result_t),
        ]


class SubcSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm, T = gate.op1, gate.op2, gate.t
        gold_result = (Rn - Rm - T) & 0xFFFFFFFF

        # based on software manual: checks if either subtraction would overflow
        carry_step1 = Rn < ((Rn - Rm) & 0xFFFFFFFF)
        carry_step2 = ((Rn - Rm) & 0xFFFFFFFF) < ((Rn - Rm - T) & 0xFFFFFFFF)
        gold_result_t = carry_step1 | carry_step2

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.SUBC),
            Assert(gate.result == gold_result),
            Assert(gate.result_t == gold_result_t),
        ]


class NotSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = ~Rm

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.NOT),
            Assert(gate.result == gold_result),
        ]


class AndSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = Rn & Rm

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.AND),
            Assert(gate.result == gold_result),
        ]


class XorSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = Rn ^ Rm

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.XOR),
            Assert(gate.result == gold_result),
        ]


class OrSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = Rn | Rm

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.OR),
            Assert(gate.result == gold_result),
        ]


class ExtubSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = Rm & 0x000000FF

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.EXTUB),
            Assert(gate.result == gold_result),
        ]


class ExtuwSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = Rm & 0x0000FFFF

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.EXTUW),
            Assert(gate.result == gold_result),
        ]


class ExtsbSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = Mux((Rm & 0x00000080) == 0, Rm & 0x000000FF, Rm | 0xFFFFFF00)

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.EXTSB),
            Assert(gate.result == gold_result),
        ]


class ExtswSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = Mux((Rm & 0x00008000) == 0, Rm & 0x0000FFFF, Rm | 0xFFFF0000)

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.EXTSW),
            Assert(gate.result == gold_result),
        ]


class SwapbSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = (
            ((Rm & 0x0000FF00) >> 8) | ((Rm & 0x000000FF) << 8) | (Rm & 0xFFFF0000)
        )

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.SWAPB),
            Assert(gate.result == gold_result),
        ]


class SwapwSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = ((Rm << 16) & 0xFFFF0000) | ((Rm >> 16) & 0x0000FFFF)

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.SWAPW),
            Assert(gate.result == gold_result),
        ]


class XtrctSpec(AluSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_result = ((Rm << 16) & 0xFFFF0000) | ((Rn >> 16) & 0x0000FFFF)

        m.d.comb += [
            Assume(gate.sel == Alu.Sel.XTRCT),
            Assert(gate.result == gold_result),
        ]


@pytest.mark.parametrize("spec", AluSpec.specs)
def test_alu(spec, tmp_path):
    assertFormal(spec(), tmp_path)
