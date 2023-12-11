import pytest

from amaranth.hdl.dsl import Assert, Assume

from snoot4.be.cmp import Cmp
from snoot4.tests.utils import Spec, assertFormal


CmpSpec = Spec(Cmp)


class CmpEqSpec(CmpSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_t = Rn == Rm

        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.EQ),
            Assert(gate.t == gold_t),
        ]


class CmpHsSpec(CmpSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_t = Rn >= Rm

        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.HS),
            Assert(gate.t == gold_t),
        ]


class CmpHiSpec(CmpSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_t = Rn > Rm

        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.HI),
            Assert(gate.t == gold_t),
        ]


class CmpGeSpec(CmpSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_t = Rn.as_signed() >= Rm.as_signed()

        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.GE),
            Assert(gate.t == gold_t),
        ]


class CmpGtSpec(CmpSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_t = Rn.as_signed() > Rm.as_signed()

        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.GT),
            Assert(gate.t == gold_t),
        ]


class CmpClrSpec(CmpSpec):
    def spec(self, m, gate):
        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.CLR),
            Assert(gate.t == 0),
        ]


class CmpSetSpec(CmpSpec):
    def spec(self, m, gate):
        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.SET),
            Assert(gate.t == 1),
        ]


class CmpTstSpec(CmpSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_t = (Rn & Rm) == 0

        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.TST),
            Assert(gate.t == gold_t),
        ]


class CmpStrSpec(CmpSpec):
    def spec(self, m, gate):
        Rn, Rm = gate.op1, gate.op2
        gold_t = (
            (Rn[0:8] == Rm[0:8])
            | (Rn[8:16] == Rm[8:16])
            | (Rn[16:24] == Rm[16:24])
            | (Rn[24:32] == Rm[24:32])
        )

        m.d.comb += [
            Assume(gate.sel == Cmp.Sel.STR),
            Assert(gate.t == gold_t),
        ]


@pytest.mark.parametrize("spec", CmpSpec.specs)
def test_logic(spec, tmp_path):
    assertFormal(spec(), tmp_path)
