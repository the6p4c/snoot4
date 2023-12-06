import pytest
import subprocess
import textwrap

from amaranth import Fragment
from amaranth._toolchain import require_tool
from amaranth.back import rtlil


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
