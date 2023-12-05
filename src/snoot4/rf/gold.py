from amaranth import Array, Module, Signal
from amaranth.hdl.dsl import Assume, Assert

from snoot4.rf import ADDR_R0, RegisterFile


class RegisterFileGold(RegisterFile):
    def elaborate(self, platform):
        m = Module()

        bank0 = [Signal(32, name=f"R{n}_BANK0") for n in range(8)]
        bank1 = [Signal(32, name=f"R{n}_BANK1") for n in range(8)]
        high = [Signal(32, name=f"R{n+16}") for n in range(8)]
        regs = Array(bank0 + bank1 + high)

        bank0 = [Signal(32, name=f"R{n}_BANK0_next") for n in range(8)]
        bank1 = [Signal(32, name=f"R{n}_BANK1_next") for n in range(8)]
        high = [Signal(32, name=f"R{n+16}_next") for n in range(8)]
        regs_next = Array(bank0 + bank1 + high)

        def _reg(bank, addr):
            addr_low, addr_is_high = addr[0:3], addr >= 8

            linear_addr = Signal(5)
            with m.If(addr_is_high):
                m.d.comb += linear_addr.eq(16 + addr_low)
            with m.Elif(bank == 0):
                m.d.comb += linear_addr.eq(0 + addr_low)
            with m.Else():
                m.d.comb += linear_addr.eq(8 + addr_low)
            return regs_next[linear_addr]

        # registers don't change unless written to
        for i in range(len(regs)):
            m.d.comb += regs_next[i].eq(regs[i])

        # core writes never conflict (CSR writes can't conflict)
        m.d.comb += Assume(~(self.rd.en & self.re.en & (self.rd.addr == self.re.addr)))

        # write before read
        with m.If(self.rd.en):
            m.d.comb += _reg(self.bank, self.rd.addr).eq(self.rd.data)
        with m.If(self.re.en):
            m.d.comb += _reg(self.bank, self.re.addr).eq(self.re.data)
        with m.If(self.csr_w.en):
            m.d.comb += _reg(~self.bank, self.csr_w.addr).eq(self.csr_w.data)

        m.d.sync += self.ra.data.eq(_reg(self.bank, self.ra.addr))
        m.d.sync += self.rb.data.eq(_reg(self.bank, self.rb.addr))
        m.d.sync += self.r0.eq(_reg(self.bank, ADDR_R0))
        m.d.sync += self.csr_r.data.eq(_reg(~self.bank, self.csr_r.addr))

        # "changes" are "saved" on the next cycle
        for i in range(len(regs)):
            m.d.sync += regs[i].eq(regs_next[i])

        return m
