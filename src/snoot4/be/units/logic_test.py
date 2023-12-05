import subprocess
import textwrap

from amaranth import Fragment, Module, Mux
from amaranth._toolchain import require_tool
from amaranth.back import rtlil
from amaranth.lib.wiring import Component, In, Out
import pytest

from snoot4.be.units.logic import Logic, LogicSel


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
    gold = LogicGold(result)
    gate = LogicGate(sel)

    assertEquivalent(gold, gate, tmp_path)


class LogicGold(Component):
    op1: In(32)  # Rm
    op2: In(32)  # Rn
    result: Out(32)  # Rn

    def __init__(self, result):
        super().__init__()

        self._result = result

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.result.eq(self._result(self.op1, self.op2))
        return m


class LogicGate(Component):
    op1: In(32)  # Rm
    op2: In(32)  # Rn
    result: Out(32)  # Rn

    def __init__(self, sel):
        super().__init__()

        self._sel = sel

    def elaborate(self, platform):
        m = Module()
        m.submodules.logic = logic = Logic()
        m.d.comb += [
            logic.sel.eq(self._sel),
            logic.op1.eq(self.op1),
            logic.op2.eq(self.op2),
            self.result.eq(logic.result),
        ]
        return m


def assertEquivalent(gold, gate, tmp_path):
    gold_frag = Fragment.get(gold, platform="formal").prepare(
        ports=[value for _, _, value in gold.signature.flatten(gold)]
    )
    gate_frag = Fragment.get(gate, platform="formal").prepare(
        ports=[value for _, _, value in gate.signature.flatten(gate)]
    )

    gold_rtlil = rtlil.convert_fragment(gold_frag)[0]
    gate_rtlil = rtlil.convert_fragment(gate_frag)[0]

    with open(tmp_path / "gold.il", "w") as f:
        f.write(gold_rtlil)
    with open(tmp_path / "gate.il", "w") as f:
        f.write(gate_rtlil)

    config = textwrap.dedent(
        """\
        [gold]
        read_ilang gold.il
        prep

        [gate]
        read_ilang gate.il
        flatten
        prep

        [strategy sby]
        use sby
        depth 2
        engine smtbmc
        """
    )

    with subprocess.Popen(
        [require_tool("eqy"), "-", "-g", "-d", tmp_path / "output"],
        cwd=tmp_path,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ) as proc:
        stdout, _ = proc.communicate(config)
        if proc.returncode != 0:
            pytest.fail(stdout)
