import pytest
import subprocess
import textwrap

from amaranth import Fragment
from amaranth._toolchain import require_tool
from amaranth.back import rtlil


def assertEquivalent(gold, gate, tmp_path):
    gold_frag = Fragment.get(gold, platform="formal").prepare(
        ports=[value for _, _, value in gold.signature.flatten(gold)]
    )
    gate_frag = Fragment.get(gate, platform="formal").prepare(
        ports=[value for _, _, value in gate.signature.flatten(gate)]
    )

    gold_rtlil = rtlil.convert_fragment(gold_frag)[0]
    gate_rtlil = rtlil.convert_fragment(gate_frag)[0]

    with open(tmp_path / "gold.il", "w") as f:
        f.write(gold_rtlil)
    with open(tmp_path / "gate.il", "w") as f:
        f.write(gate_rtlil)

    config = textwrap.dedent(
        """\
        [gold]
        read_ilang gold.il
        prep

        [gate]
        read_ilang gate.il
        flatten
        prep

        [strategy sby]
        use sby
        depth 2
        engine smtbmc
        """
    )

    with subprocess.Popen(
        [require_tool("eqy"), "-", "-g", "-d", tmp_path / "output"],
        cwd=tmp_path,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ) as proc:
        stdout, _ = proc.communicate(config)
        if proc.returncode != 0:
            pytest.fail(stdout)
