from amaranth import Cat, Const, Signal
import pytest

from amaranth.hdl.dsl import Assert, Assume

from snoot4.be.units import MemoryRead, MemoryWrite
from snoot4.be.units.mem import Width  # TODO: stuff
from snoot4.tests.utils import Spec, assertFormal


MemoryReadSpec = Spec(MemoryRead)
MemoryWriteSpec = Spec(MemoryWrite)


class ReadByteSpec(MemoryReadSpec):
    def spec(self, m, gate):
        # least-significant byte
        b0 = gate.rdata[0:8]
        b1 = gate.rdata[8:16]
        b2 = gate.rdata[16:24]
        b3 = gate.rdata[24:32]
        # most-significant byte

        gold_data = Signal(32)
        with m.Switch(gate.addr):
            with m.Case(0b00):
                m.d.comb += gold_data.eq(Cat(b3, b3[7].replicate(24)))
            with m.Case(0b01):
                m.d.comb += gold_data.eq(Cat(b2, b2[7].replicate(24)))
            with m.Case(0b10):
                m.d.comb += gold_data.eq(Cat(b1, b1[7].replicate(24)))
            with m.Case(0b11):
                m.d.comb += gold_data.eq(Cat(b0, b0[7].replicate(24)))

        m.d.comb += [
            Assume(gate.width == Width.B),
            Assert(gate.data == gold_data),
        ]


class ReadWordSpec(MemoryReadSpec):
    def spec(self, m, gate):
        # least-significant word
        w0 = gate.rdata[0:16]
        w1 = gate.rdata[16:32]
        # most-significant word

        gold_data = Signal(32)
        with m.Switch(gate.addr):
            with m.Case(0b00):
                m.d.comb += gold_data.eq(Cat(w1, w1[15].replicate(16)))
            with m.Case(0b10):
                m.d.comb += gold_data.eq(Cat(w0, w0[15].replicate(16)))

        m.d.comb += [
            Assume(gate.width == Width.W),
            Assume(gate.addr[0] == 0),
            Assert(gate.data == gold_data),
        ]


class ReadLongSpec(MemoryReadSpec):
    def spec(self, m, gate):
        gold_data = gate.rdata

        m.d.comb += [
            Assume(gate.width == Width.L),
            Assume(gate.addr == 0),
            Assert(gate.data == gold_data),
        ]


class WriteByteSpec(MemoryWriteSpec):
    def spec(self, m, gate):
        gold_wstb = Signal(4)
        with m.Switch(gate.addr):
            with m.Case(0b00):
                m.d.comb += gold_wstb.eq(0b1000)
            with m.Case(0b01):
                m.d.comb += gold_wstb.eq(0b0100)
            with m.Case(0b10):
                m.d.comb += gold_wstb.eq(0b0010)
            with m.Case(0b11):
                m.d.comb += gold_wstb.eq(0b0001)

        gold_wdata = Signal(32)
        m.d.comb += gold_wdata.eq(gate.data[0:8].replicate(4))

        m.d.comb += [
            Assume(gate.width == Width.B),
            Assert(gate.wstb == gold_wstb),
            Assert(gate.wdata == gold_wdata),
        ]


class WriteWordSpec(MemoryWriteSpec):
    def spec(self, m, gate):
        gold_wstb = Signal(4)
        with m.Switch(gate.addr):
            with m.Case(0b00):
                m.d.comb += gold_wstb.eq(0b1100)
            with m.Case(0b10):
                m.d.comb += gold_wstb.eq(0b0011)

        gold_wdata = Signal(32)
        m.d.comb += gold_wdata.eq(gate.data[0:16].replicate(2))

        m.d.comb += [
            Assume(gate.width == Width.W),
            Assume(gate.addr[0] == 0),
            Assert(gate.wstb == gold_wstb),
            Assert(gate.wdata == gold_wdata),
        ]


class WriteLongSpec(MemoryWriteSpec):
    def spec(self, m, gate):
        gold_wstb = Signal(4)
        m.d.comb += gold_wstb.eq(0b1111)

        gold_wdata = Signal(32)
        m.d.comb += gold_wdata.eq(gate.data)

        m.d.comb += [
            Assume(gate.width == Width.L),
            Assume(gate.addr == 0),
            Assert(gate.wstb == gold_wstb),
            Assert(gate.wdata == gold_wdata),
        ]


@pytest.mark.parametrize("spec", MemoryReadSpec.specs)
def test_mem_read(spec, tmp_path):
    assertFormal(spec(), tmp_path)


@pytest.mark.parametrize("spec", MemoryWriteSpec.specs)
def test_mem_write(spec, tmp_path):
    assertFormal(spec(), tmp_path)
