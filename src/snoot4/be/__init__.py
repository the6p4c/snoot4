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
            with m.Case(RdSel.OP2):
                m.d.comb += x_rd_val.eq(x_op2)

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
        # 0:      e0 00           mov     #0,r0
        yield uut.instruction.eq(0xE000)
        yield
        # 2:      e1 01           mov     #1,r1
        yield uut.instruction.eq(0xE101)
        yield

        for _ in range(8):
            # 4:      31 0c           add     r0,r1
            yield uut.instruction.eq(0x310C)
            yield
            # 6:      30 1c           add     r1,r0
            yield uut.instruction.eq(0x301C)
            yield

        # 0:      00 09           nop
        yield uut.instruction.eq(0x0009)
        yield

        for _ in range(16):
            yield

    sim.add_clock(1e-6)
    sim.add_sync_process(proc)
    with sim.write_vcd("be.vcd"):
        sim.run()
