from amaranth import Module, Mux
from amaranth.hdl.dsl import Assert, Assume
from amaranth.lib.wiring import Component, In
import pytest

from snoot4.be.units.logic import Logic, LogicSel
from snoot4.tests.utils import assertFormal


specs = []


def spec(cls):
    specs.append(cls)
    return cls


class LogicSpec(Component):
    sel: In(LogicSel)

    op1: In(32)  # Rm
    op2: In(32)  # Rn

    def elaborate(self, platform):
        m = Module()

        m.submodules.gate = gate = Logic()
        m.d.comb += [
            gate.sel.eq(self.sel),
            gate.op1.eq(self.op1),
            gate.op2.eq(self.op2),
        ]

        self.test(m, gate)

        return m

    def test(self, m, gate):
        raise NotImplementedError("test method must be implemented in subclass")


@spec
class NotSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = ~Rm

        m.d.comb += [
            Assume(gate.sel == LogicSel.NOT),
            Assert(gate.result == gold_result),
        ]


@spec
class AndSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rn & Rm

        m.d.comb += [
            Assume(gate.sel == LogicSel.AND),
            Assert(gate.result == gold_result),
        ]


@spec
class XorSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rn ^ Rm

        m.d.comb += [
            Assume(gate.sel == LogicSel.XOR),
            Assert(gate.result == gold_result),
        ]


@spec
class OrSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rn | Rm

        m.d.comb += [
            Assume(gate.sel == LogicSel.OR),
            Assert(gate.result == gold_result),
        ]


@spec
class XtrctSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = ((Rm << 16) & 0xFFFF0000) | ((Rn >> 16) & 0x0000FFFF)

        m.d.comb += [
            Assume(gate.sel == LogicSel.XTRCT),
            Assert(gate.result == gold_result),
        ]


@spec
class SwapbSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = (
            ((Rm & 0x0000FF00) >> 8) | ((Rm & 0x000000FF) << 8) | (Rm & 0xFFFF0000)
        )

        m.d.comb += [
            Assume(gate.sel == LogicSel.SWAPB),
            Assert(gate.result == gold_result),
        ]


@spec
class SwapwSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = ((Rm << 16) & 0xFFFF0000) | ((Rm >> 16) & 0x0000FFFF)

        m.d.comb += [
            Assume(gate.sel == LogicSel.SWAPW),
            Assert(gate.result == gold_result),
        ]


@spec
class ExtubSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rm & 0x000000FF

        m.d.comb += [
            Assume(gate.sel == LogicSel.EXTUB),
            Assert(gate.result == gold_result),
        ]


@spec
class ExtuwSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Rm & 0x0000FFFF

        m.d.comb += [
            Assume(gate.sel == LogicSel.EXTUW),
            Assert(gate.result == gold_result),
        ]


@spec
class ExtsbSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Mux((Rm & 0x00000080) == 0, Rm & 0x000000FF, Rm | 0xFFFFFF00)

        m.d.comb += [
            Assume(gate.sel == LogicSel.EXTSB),
            Assert(gate.result == gold_result),
        ]


@spec
class ExtswSpec(LogicSpec):
    def test(self, m, gate):
        Rm, Rn = gate.op1, gate.op2
        gold_result = Mux((Rm & 0x00008000) == 0, Rm & 0x0000FFFF, Rm | 0xFFFF0000)

        m.d.comb += [
            Assume(gate.sel == LogicSel.EXTSW),
            Assert(gate.result == gold_result),
        ]


@pytest.mark.parametrize("spec", specs)
def test_logic(spec, tmp_path):
    uut = spec()

    assertFormal(uut, tmp_path)
