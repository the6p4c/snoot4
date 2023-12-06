import pytest
import subprocess
import textwrap

from amaranth import Fragment, Module
from amaranth._toolchain import require_tool
from amaranth.back import rtlil
from amaranth.lib.wiring import Component, Out, connect, flipped


def Spec(gate_cls):
    gate = gate_cls()
    gate._MustUse__used = True
    gate_signature = gate.signature

    class Spec(Component):
        ports: Out(gate_signature)
        specs = []

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)

            Spec.specs.append(cls)

        def elaborate(self, platform):
            m = Module()
            m.submodules.gate = gate = gate_cls()
            connect(m, flipped(self.ports), gate)

            self.spec(m, gate)

            return m

        def spec(self, m, gate):
            raise NotImplementedError("spec method must be implemented in subclass")

    return Spec


def assertFormal(uut, tmp_path):
    uut_ports = [value for _, _, value in uut.signature.flatten(uut)]
    uut_frag = Fragment.get(uut, platform="formal").prepare(ports=uut_ports)
    uut_rtlil = rtlil.convert_fragment(uut_frag)[0]

    config = textwrap.dedent(
        f"""\
        [options]
        mode bmc
        depth 1
        wait on
        multiclock on

        [engines]
        smtbmc

        [script]
        read_ilang top.il
        prep

        [file top.il]
        {uut_rtlil}
        """
    )

    with subprocess.Popen(
        [require_tool("sby"), "-f", "-d", tmp_path],
        cwd=tmp_path,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ) as proc:
        stdout, _ = proc.communicate(config)
        if proc.returncode != 0:
            pytest.fail(stdout)
