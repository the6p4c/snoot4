from amaranth import Module, Signal
from amaranth.lib.wiring import Component, In

from snoot4.be.decoder import Decoder, Op2Sel, RdSel
from snoot4.be.units.arith import Arith
from snoot4.be.units.logic import Logic
from snoot4.rf.sim import RegisterFileSim


class Backend(Component):
    instruction: In(16)

    def elaborate(self, platform):
        m = Module()

        m.submodules.rf = rf = RegisterFileSim()
        m.submodules.decoder = decoder = Decoder()

        m.submodules.arith = arith = Arith()
        m.submodules.logic = logic = Logic()

        # === pipeline registers ===
        dx_ra = Signal(4)
        dx_ra_val = Signal(32)
        dx_rb = Signal(4)
        dx_rb_val = Signal(32)
        dx_r0_val = Signal(32)
        dx_rd_en = Signal()
        dx_rd = Signal(4)
        dx_imm = Signal(32)
        dx_op2_sel = Signal(Op2Sel)
        dx_arith_sel = Signal(Arith.Sel)
        dx_logic_sel = Signal(Logic.Sel)
        dx_rd_sel = Signal(RdSel)

        xm_rd_en = Signal()
        xm_rd = Signal(4)
        xm_rd_val = Signal(32)

        mw_rd_en = Signal()
        mw_rd = Signal(4)
        mw_rd_val = Signal(32)

        # === D ===
        m.d.comb += [
            decoder.instruction.eq(self.instruction),
            rf.ra.addr.eq(decoder.ra),
            rf.rb.addr.eq(decoder.rb),
        ]

        m.d.comb += [
            dx_ra_val.eq(rf.ra.data),  # TODO: stall handling
            dx_rb_val.eq(rf.rb.data),  # TODO: stall handling
            dx_r0_val.eq(rf.r0),
        ]
        m.d.sync += [
            dx_ra.eq(decoder.ra),
            dx_rb.eq(decoder.rb),
            dx_rd_en.eq(decoder.rd_en),
            dx_rd.eq(decoder.rd),
            dx_imm.eq(decoder.imm),
            dx_op2_sel.eq(decoder.op2_sel),
            dx_arith_sel.eq(decoder.arith_sel),
            dx_logic_sel.eq(decoder.logic_sel),
            dx_rd_sel.eq(decoder.rd_sel),
        ]

        # === X ===
        def _bypass(*, rn, rn_val):
            byp_val = Signal(32)
            with m.If(xm_rd_en & (xm_rd == rn)):
                m.d.comb += byp_val.eq(xm_rd_val)
            with m.Elif(mw_rd_en & (mw_rd == rn)):
                m.d.comb += byp_val.eq(mw_rd_val)
            with m.Else():
                m.d.comb += byp_val.eq(rn_val)
            return byp_val

        x_ra_val = Signal(32)
        x_rb_val = Signal(32)
        x_r0_val = Signal(32)
        m.d.comb += [
            x_ra_val.eq(_bypass(rn=dx_ra, rn_val=dx_ra_val)),
            x_rb_val.eq(_bypass(rn=dx_rb, rn_val=dx_rb_val)),
            x_r0_val.eq(_bypass(rn=0, rn_val=dx_r0_val)),
        ]

        x_op1 = Signal(32)
        x_op2 = Signal(32)
        m.d.comb += x_op1.eq(x_ra_val)
        with m.Switch(dx_op2_sel):
            with m.Case(Op2Sel.RB):
                m.d.comb += x_op2.eq(x_rb_val)
            with m.Case(Op2Sel.R0):
                m.d.comb += x_op2.eq(x_r0_val)
            with m.Case(Op2Sel.IMM):
                m.d.comb += x_op2.eq(dx_imm)

        m.d.comb += [
            arith.sel.eq(dx_arith_sel),
            arith.flags_sel.eq(Arith.FlagsSel.CARRY),
            arith.op1.eq(x_op1),
            arith.op2.eq(x_op2),
            arith.ti.eq(0),
        ]

        m.d.comb += [
            logic.sel.eq(dx_logic_sel),
            logic.flags_sel.eq(Logic.FlagsSel.ZERO),
            logic.op1.eq(x_op1),
            logic.op2.eq(x_op2),
        ]

        x_rd_val = Signal(32)
        with m.Switch(dx_rd_sel):
            with m.Case(RdSel.ARITH):
                m.d.comb += x_rd_val.eq(arith.result)
            with m.Case(RdSel.LOGIC):
                m.d.comb += x_rd_val.eq(logic.result)

        m.d.sync += [
            xm_rd_val.eq(x_rd_val),
            xm_rd_en.eq(dx_rd_en),
            xm_rd.eq(dx_rd),
        ]

        # === M ===
        m.d.sync += [
            mw_rd_val.eq(xm_rd_val),
            mw_rd_en.eq(xm_rd_en),
            mw_rd.eq(xm_rd),
        ]

        # === W ===
        m.d.comb += [
            rf.rd.en.eq(mw_rd_en),
            rf.rd.addr.eq(mw_rd),
            rf.rd.data.eq(mw_rd_val),
        ]

        return m


if __name__ == "__main__":
    from amaranth.sim import Simulator

    uut = Backend()
    sim = Simulator(uut)

    def proc():
        # NOP    0000 0000 0000 1001
        yield uut.instruction.eq(0b0000_0000_0000_1001)
        yield
        # ADD #imm,Rn   Rn + imm -> Rn    0111 nnnn iiii iiii
        # ADD #1,R2     R2 + 1   -> R2    0111 0100 0000 0001
        yield uut.instruction.eq(0b0111_0010_0000_0001)
        yield
        # ADD #imm,Rn   Rn + imm -> Rn    0111 nnnn iiii iiii
        # ADD #3,R4     R4 + 3   -> R4    0111 0100 0000 0011
        yield uut.instruction.eq(0b0111_0100_0000_0011)
        yield
        # ADD Rm,Rn   Rn + Rm -> Rn    0011 nnnn mmmm 1100
        # ADD R2,R4   R4 + R2 -> R4    0011 0100 0010 1100
        yield uut.instruction.eq(0b0011_0100_0010_1100)
        yield
        # NOT Rm,Rn   ~Rm -> Rn    0110 nnnn mmmm 0111
        # NOT R4,R8   ~R4 -> R8    0110 1000 0100 0111
        yield uut.instruction.eq(0b0110_1000_0100_0111)
        yield
        # AND Rm,Rn   Rn & Rm -> Rn    0010 nnnn mmmm 1001
        # AND R2,R8   R8 & R2 -> R8    0010 1000 0010 1001
        yield uut.instruction.eq(0b0010_1000_0010_1001)
        yield
        # NOP    0000 0000 0000 1001
        yield uut.instruction.eq(0b0000_0000_0000_1001)
        yield

        for _ in range(16):
            yield

    sim.add_clock(1e-6)
    sim.add_sync_process(proc)
    with sim.write_vcd("be.vcd"):
        sim.run()
