from amaranth import Mux
from amaranth.hdl.dsl import Assert, Assume
import pytest

from snoot4.be.units.logic import Logic, LogicFlagsSel, LogicSel
from snoot4.tests.utils import Spec, assertFormal


LogicSpec = Spec(Logic)


class NotSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = ~Rm

        m.d.comb += [
            Assume(gate.sel == LogicSel.NOT),
            Assert(gate.result == gold_result),
        ]


class AndSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rn & Rm

        m.d.comb += [
            Assume(gate.sel == LogicSel.AND),
            Assert(gate.result == gold_result),
        ]


class XorSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rn ^ Rm

        m.d.comb += [
            Assume(gate.sel == LogicSel.XOR),
            Assert(gate.result == gold_result),
        ]


class OrSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rn | Rm

        m.d.comb += [
            Assume(gate.sel == LogicSel.OR),
            Assert(gate.result == gold_result),
        ]


class XtrctSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = ((Rm << 16) & 0xFFFF0000) | ((Rn >> 16) & 0x0000FFFF)

        m.d.comb += [
            Assume(gate.sel == LogicSel.XTRCT),
            Assert(gate.result == gold_result),
        ]


class SwapbSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = (
            ((Rm & 0x0000FF00) >> 8) | ((Rm & 0x000000FF) << 8) | (Rm & 0xFFFF0000)
        )

        m.d.comb += [
            Assume(gate.sel == LogicSel.SWAPB),
            Assert(gate.result == gold_result),
        ]


class SwapwSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = ((Rm << 16) & 0xFFFF0000) | ((Rm >> 16) & 0x0000FFFF)

        m.d.comb += [
            Assume(gate.sel == LogicSel.SWAPW),
            Assert(gate.result == gold_result),
        ]


class ExtubSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rm & 0x000000FF

        m.d.comb += [
            Assume(gate.sel == LogicSel.EXTUB),
            Assert(gate.result == gold_result),
        ]


class ExtuwSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rm & 0x0000FFFF

        m.d.comb += [
            Assume(gate.sel == LogicSel.EXTUW),
            Assert(gate.result == gold_result),
        ]


class ExtsbSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Mux((Rm & 0x00000080) == 0, Rm & 0x000000FF, Rm | 0xFFFFFF00)

        m.d.comb += [
            Assume(gate.sel == LogicSel.EXTSB),
            Assert(gate.result == gold_result),
        ]


class ExtswSpec(LogicSpec):
    def spec(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Mux((Rm & 0x00008000) == 0, Rm & 0x0000FFFF, Rm | 0xFFFF0000)

        m.d.comb += [
            Assume(gate.sel == LogicSel.EXTSW),
            Assert(gate.result == gold_result),
        ]


class TstSpec(LogicSpec):
    def spec(self, m, gate):
        gold_to = gate.result == 0

        m.d.comb += [
            Assume(gate.sel == LogicSel.AND),
            Assume(gate.flags_sel == LogicFlagsSel.ZERO),
            Assert(gate.to == gold_to),
        ]


class CmpStrSpec(LogicSpec):
    def spec(self, m, gate):
        result = gate.result
        gold_to = (
            (result[0:8] == 0)
            | (result[8:16] == 0)
            | (result[16:24] == 0)
            | (result[24:32] == 0)
        )

        m.d.comb += [
            Assume(gate.sel == LogicSel.XOR),
            Assume(gate.flags_sel == LogicFlagsSel.STR),
            Assert(gate.to == gold_to),
        ]


@pytest.mark.parametrize("spec", LogicSpec.specs)
def test_logic(spec, tmp_path):
    assertFormal(spec(), tmp_path)
