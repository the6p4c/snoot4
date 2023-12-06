from amaranth import Array, Module, Signal

from snoot4.rf import ADDR_R0, RegisterFile


class RegisterFileSim(RegisterFile):
    def elaborate(self, platform):
        m = Module()

        bank0 = Array([Signal(32, name=f"R{n}_BANK0") for n in range(8)])
        bank1 = Array([Signal(32, name=f"R{n}_BANK1") for n in range(8)])
        high = Array([Signal(32, name=f"R{n+16}") for n in range(8)])

        def _read(bank, addr):
            addr_low, addr_is_high = addr[0:3], addr >= 8

            data = Signal(32)
            with m.If(addr_is_high):
                m.d.comb += data.eq(high[addr_low])
            with m.Elif(bank == 0):
                m.d.comb += data.eq(bank0[addr_low])
            with m.Else():  # bank == 1
                m.d.comb += data.eq(bank1[addr_low])
            return data

        def _write(bank, addr, data):
            addr_low, addr_is_high = addr[0:3], addr >= 8

            with m.If(addr_is_high):
                m.d.sync += high[addr_low].eq(data)
            with m.Elif(bank == 0):
                m.d.sync += bank0[addr_low].eq(data)
            with m.Else():  # bank == 1
                m.d.sync += bank1[addr_low].eq(data)

        # === core ports ===
        # the core always reads from the active bank. bypass paths are required from write ports to
        # read ports as a write and read of the same register can occur within the same cycle.
        def _read_core(addr):
            data = Signal(32)
            with m.If(self.re.en & (addr == self.re.addr)):
                m.d.comb += data.eq(self.re.data)
            with m.Elif(self.rd.en & (addr == self.rd.addr)):
                m.d.comb += data.eq(self.rd.data)
            with m.Else():
                m.d.comb += data.eq(_read(self.bank, addr))
            return data

        def _write_core(addr, data):
            _write(self.bank, addr, data)

        m.d.sync += self.ra.data.eq(_read_core(self.ra.addr))
        m.d.sync += self.rb.data.eq(_read_core(self.rb.addr))
        m.d.sync += self.r0.eq(_read_core(ADDR_R0))
        with m.If(self.rd.en):
            _write_core(self.rd.addr, self.rd.data)
        with m.If(self.re.en):
            _write_core(self.re.addr, self.re.data)

        # === CSR ports ===
        # the CSR unit can read and write from the inactive bank. reads and writes can ocurr in the
        # same cycle, as reads are performed at the X/M boundary and writes at the M/W boundary.
        # this means a bypass path is required.
        def _read_csr(addr):
            data = Signal(32)
            with m.If(self.csr_w.en & (self.csr_w.addr == addr)):
                m.d.comb += data.eq(self.csr_w.data)
            with m.Else():
                m.d.comb += data.eq(_read(~self.bank, addr))
            return data

        def _write_csr(addr, data):
            _write(~self.bank, addr, data)

        m.d.sync += self.csr_r.data.eq(_read_csr(self.csr_r.addr))
        with m.If(self.csr_w.en):
            _write_csr(self.csr_w.addr, self.csr_w.data)

        return m
