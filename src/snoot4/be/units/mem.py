from amaranth import Array, Cat, Module, Signal
from amaranth.lib import enum
from amaranth.lib.wiring import Component, In, Out


class Width(enum.Enum):
    B = 0b001
    W = 0b010
    L = 0b100


class MemoryRead(Component):
    width: In(Width)
    addr: In(2)
    rdata: In(32)

    data: Out(32)

    def elaborate(self, platform):
        m = Module()

        # === extract correct lane ===
        data_ub = Signal(8)
        bytes = [
            self.rdata[24:32],
            self.rdata[16:24],
            self.rdata[8:16],
            self.rdata[0:8],
        ]
        m.d.comb += data_ub.eq(Array(bytes)[self.addr])

        data_uw = Signal(16)
        words = [
            self.rdata[16:32],
            self.rdata[0:16],
        ]
        m.d.comb += data_uw.eq(Array(words)[self.addr[1]])

        data_ul = Signal(32)
        m.d.comb += data_ul.eq(self.rdata)

        # === sign extend ===
        data_sb = Signal(32)
        m.d.comb += data_sb.eq(Cat(data_ub, data_ub[7].replicate(24)))

        data_sw = Signal(32)
        m.d.comb += data_sw.eq(Cat(data_uw, data_uw[15].replicate(16)))

        data_sl = Signal(32)
        m.d.comb += data_sl.eq(data_ul)

        # === select correct width ===
        with m.Switch(self.width):
            with m.Case(Width.B):
                m.d.comb += self.data.eq(data_sb)
            with m.Case(Width.W):
                m.d.comb += self.data.eq(data_sw)
            with m.Case(Width.L):
                m.d.comb += self.data.eq(data_sl)

        return m


class MemoryWrite(Component):
    width: In(Width)
    addr: In(2)
    data: In(32)

    wstb: Out(4)
    wdata: Out(32)

    def elaborate(self, platform):
        m = Module()

        # === generate wstb ===
        wstb_b = Signal(4)
        wstb_w = Signal(4)
        wstb_l = Signal(4)
        m.d.comb += [
            wstb_b.eq(Array([0b1000, 0b0100, 0b0010, 0b0001])[self.addr]),
            wstb_w.eq(Array([0b1100, 0b0011])[self.addr[1]]),
            wstb_l.eq(0b1111),
        ]

        # === generate wdata ===
        wdata_b = Signal(32)
        wdata_w = Signal(32)
        wdata_l = Signal(32)
        m.d.comb += [
            wdata_b.eq(self.data[0:8].replicate(4)),
            wdata_w.eq(self.data[0:16].replicate(2)),
            wdata_l.eq(self.data),
        ]

        # === select correct width ===
        with m.Switch(self.width):
            with m.Case(Width.B):
                m.d.comb += [
                    self.wstb.eq(wstb_b),
                    self.wdata.eq(wdata_b),
                ]
            with m.Case(Width.W):
                m.d.comb += [
                    self.wstb.eq(wstb_w),
                    self.wdata.eq(wdata_w),
                ]
            with m.Case(Width.L):
                m.d.comb += [
                    self.wstb.eq(wstb_l),
                    self.wdata.eq(wdata_l),
                ]

        return m
