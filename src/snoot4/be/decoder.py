from amaranth import Cat, Module
from amaranth.lib import enum
from amaranth.lib.wiring import Component, In, Out, Signature
from contextlib import contextmanager
import re
from types import SimpleNamespace


class Op2Sel(enum.Enum):
    RB = 0b00
    R0 = 0b10
    IMM = 0b11


class Decoder(Component):
    instruction: In(16)

    valid: Out(1)

    ra_en: Out(1)
    ra: Out(4)
    rb_en: Out(1)
    rb: Out(4)
    imm: Out(32)

    op2_sel: Out(Op2Sel)

    rd_en: Out(1)
    rd: Out(4)

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

        def _use_ra(ra):
            m.d.comb += [
                self.ra_en.eq(1),
                self.ra.eq(ra),
            ]

        def _use_rb(rb):
            m.d.comb += [
                self.rb_en.eq(1),
                self.rb.eq(rb),
            ]

        def _use_simm(imm):
            sign_bits = imm[-1].replicate(32 - imm.shape().width)
            m.d.comb += self.imm.eq(Cat(imm, sign_bits))

        def _with_op2(op2_sel):
            m.d.comb += self.op2_sel.eq(op2_sel)

        def _use_rd(rd):
            m.d.comb += [
                self.rd_en.eq(1),
                self.rd.eq(rd),
            ]

        # ADD Rm, Rn
        with _instruction("0011 nnnn mmmm 1100") as inst:
            _use_ra(inst.n)
            _use_rb(inst.m)
            _with_op2(Op2Sel.RB)
            _use_rd(inst.n)

        # ADD #imm,Rn
        with _instruction("0111 nnnn iiii iiii") as inst:
            _use_ra(inst.n)
            _use_simm(inst.i)
            _with_op2(Op2Sel.IMM)
            _use_rd(inst.n)

        return m
