from amaranth import Module, Mux
from amaranth.hdl.dsl import Assert
from amaranth.lib.wiring import Component, In, Out
import pytest

from snoot4.be.units.logic import Logic, LogicSel
from snoot4.tests.utils import assertFormal


def logic_not(Rm, Rn):
    return ~Rm


def logic_and(Rm, Rn):
    return Rn & Rm


def logic_xor(Rm, Rn):
    return Rn ^ Rm


def logic_or(Rm, Rn):
    return Rn | Rm


def logic_xtrct(Rm, Rn):
    return ((Rm << 16) & 0xFFFF0000) | ((Rn >> 16) & 0x0000FFFF)


def logic_swapb(Rm, Rn):
    return ((Rm & 0x0000FF00) >> 8) | ((Rm & 0x000000FF) << 8) | (Rm & 0xFFFF0000)


def logic_swapw(Rm, Rn):
    return ((Rm << 16) & 0xFFFF0000) | ((Rm >> 16) & 0x0000FFFF)


def logic_extub(Rm, Rn):
    return Rm & 0x000000FF


def logic_extuw(Rm, Rn):
    return Rm & 0x0000FFFF


def logic_extsb(Rm, Rn):
    return Mux((Rm & 0x00000080) == 0, Rm & 0x000000FF, Rm | 0xFFFFFF00)


def logic_extsw(Rm, Rn):
    return Mux((Rm & 0x00008000) == 0, Rm & 0x0000FFFF, Rm | 0xFFFF0000)


@pytest.mark.parametrize(
    "sel, result",
    [
        (LogicSel.NOT, logic_not),
        (LogicSel.AND, logic_and),
        (LogicSel.XOR, logic_xor),
        (LogicSel.OR, logic_or),
        (LogicSel.XTRCT, logic_xtrct),
        (LogicSel.SWAPB, logic_swapb),
        (LogicSel.SWAPW, logic_swapw),
        (LogicSel.EXTUB, logic_extub),
        (LogicSel.EXTUW, logic_extuw),
        (LogicSel.EXTSB, logic_extsb),
        (LogicSel.EXTSW, logic_extsw),
    ],
)
def test_logic(sel, result, tmp_path):
    assertFormal(LogicSpec(sel, result), tmp_path)


class LogicSpec(Component):
    op1: In(32)  # Rm
    op2: In(32)  # Rn

    def __init__(self, sel, func):
        super().__init__()

        self._sel = sel
        self._func = func

    def elaborate(self, platform):
        m = Module()

        m.submodules.logic = logic = Logic()
        m.d.comb += [
            logic.sel.eq(self._sel),
            logic.op1.eq(self.op1),
            logic.op2.eq(self.op2),
        ]

        gate_result = logic.result
        gold_result = self._func(self.op1, self.op2)
        m.d.comb += Assert(gate_result == gold_result)

        return m
