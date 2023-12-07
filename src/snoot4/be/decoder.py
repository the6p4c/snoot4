from contextlib import contextmanager
import re
from types import SimpleNamespace

from amaranth import Cat, Module
from amaranth.lib import enum
from amaranth.lib.wiring import Component, In, Out

from snoot4.be.units.arith import Arith
from snoot4.be.units.logic import Logic


class Op2Sel(enum.Enum):
    RB = 0b00
    R0 = 0b10
    IMM = 0b11


class RdSel(enum.Enum):
    ARITH = 0
    LOGIC = 1


class Decoder(Component):
    instruction: In(16)

    valid: Out(1)

    ra_en: Out(1)
    ra: Out(4)
    rb_en: Out(1)
    rb: Out(4)
    rd_en: Out(1)
    rd: Out(4)

    imm: Out(32)

    op2_sel: Out(Op2Sel)
    arith_sel: Out(Arith.Sel)
    logic_sel: Out(Logic.Sel)
    rd_sel: Out(RdSel)

    def elaborate(self, platform):
        m = Module()

        @contextmanager
        def _instruction(pattern):
            WILDCARDS = "mnid"

            # === extract fields ===
            # reversed with spaces removed so that string indices match bit indices
            bit_pattern = "".join(reversed(pattern.replace(" ", "")))

            fields = {}
            for wildcard in WILDCARDS:
                start = bit_pattern.find(wildcard)
                end = bit_pattern.rfind(wildcard) + 1

                if start == -1:
                    continue

                if not all(c == wildcard for c in bit_pattern[start:end]):
                    raise ValueError(
                        f"field {wildcard!r} in pattern {pattern!r} is not contiguous"
                    )

                fields[wildcard] = self.instruction[start:end]

            # === decode ===
            # all wildcards must be replaced with don't care bits
            matcher = re.sub(f"[{WILDCARDS}]", "-", pattern)

            with m.If(self.instruction.matches(matcher)):
                m.d.comb += self.valid.eq(1)
                yield SimpleNamespace(**fields)

        def _rf(*, ra=None, rb=None, rd=None):
            for rn, self_rn_en, self_rn in [
                (ra, self.ra_en, self.ra),
                (rb, self.rb_en, self.rb),
                (rd, self.rd_en, self.rd),
            ]:
                if rn is not None:
                    m.d.comb += [
                        self_rn_en.eq(1),
                        self_rn.eq(rn),
                    ]

        def _use_simm(imm):
            sign_bits = imm[-1].replicate(32 - imm.shape().width)
            m.d.comb += self.imm.eq(Cat(imm, sign_bits))

        def _with_op2(op2_sel):
            m.d.comb += self.op2_sel.eq(op2_sel)

        def _use_arith(arith_sel):
            m.d.comb += self.arith_sel.eq(arith_sel)

        def _use_logic(logic_sel):
            m.d.comb += self.logic_sel.eq(logic_sel)

        def _with_rd(rd_sel):
            m.d.comb += self.rd_sel.eq(rd_sel)

        # ADD Rm, Rn
        with _instruction("0011 nnnn mmmm 1100") as inst:
            _rf(ra=inst.n, rb=inst.m, rd=inst.n)
            _with_op2(Op2Sel.RB)
            _use_arith(Arith.Sel.ADD)
            _with_rd(RdSel.ARITH)

        # ADD #imm,Rn
        with _instruction("0111 nnnn iiii iiii") as inst:
            _rf(ra=inst.n, rd=inst.n)
            _use_simm(inst.i)
            _with_op2(Op2Sel.IMM)
            _use_arith(Arith.Sel.ADD)
            _with_rd(RdSel.ARITH)

        # AND Rm,Rn
        with _instruction("0010 nnnn mmmm 1001") as inst:
            _rf(ra=inst.n, rb=inst.m, rd=inst.n)
            _with_op2(Op2Sel.RB)
            _use_logic(Logic.Sel.AND)
            _with_rd(RdSel.LOGIC)

        # NOT Rm,Rn
        with _instruction("0110 nnnn mmmm 0111") as inst:
            _rf(rb=inst.m, rd=inst.n)
            _with_op2(Op2Sel.RB)
            _use_logic(Logic.Sel.NOT)
            _with_rd(RdSel.LOGIC)

        return m
