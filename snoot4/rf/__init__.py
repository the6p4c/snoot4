from amaranth import C
from amaranth.lib.wiring import Component, In, Out, Signature

ADDR_R0 = C(0, 4)


class ReadPort(Signature):
    def __init__(self, *, addr_width):
        super().__init__({"addr": In(addr_width), "data": Out(32)})


class WritePort(Signature):
    def __init__(self, *, addr_width):
        super().__init__({"en": Out(1), "addr": Out(addr_width), "data": Out(32)})


CoreReadPort = ReadPort(addr_width=4)
CoreWritePort = WritePort(addr_width=4)
CsrReadPort = ReadPort(addr_width=3)
CsrWritePort = WritePort(addr_width=3)


class RegisterFile(Component):
    bank: In(1)

    ra: Out(CoreReadPort)
    rb: Out(CoreReadPort)
    r0: Out(32)

    rd: In(CoreWritePort)
    re: In(CoreWritePort)

    csr_r: Out(CsrReadPort)
    csr_w: In(CsrWritePort)

    def elaborate(self, platform):
        raise NotImplementedError(
            "elaborate must be implemented in RegisterFile subclass"
        )
