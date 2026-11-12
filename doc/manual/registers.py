#
# This file is part of LiteI2C project.
#
# Copyright (c) 2026 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause
#
# Register appendix of the manual: which designs tools/csr_doc.py elaborates and which register banks
# it documents (the engine is generic, part of the manual kit).

import json
import os
import sys
import tempfile

# Configurations: name -> parameters of the reference design below (shown in the appendix table).
# One design holds a LiteI2C core added with SoC.add_i2c_master, with the register master and the
# interrupt event (with_irq=True), so that every register of the core is present.
CONFIGS = {
    "arty_reference" : ["add_i2c_master()", "with_irq=True", "pads=pmodb:0,1"],
}

# Banks documented in the appendix (prefix match on the bank name), in order, with their title and
# the Python class that defines them. The longest matching prefix owns a bank.
BANKS = [
    ("i2cmaster", "LiteI2C", "LiteI2C", "litei2c/__init__.py"),
]

# Descriptions of the LiteI2C registers that the gateware declares without one (CSRStorage/CSR
# without `description`); they are attached to the elaborated registers before the dump, and a
# description declared in the gateware takes precedence. Keys: (bank, register).
DESCRIPTIONS = {
    ("i2cmaster", "phy_speed_mode") : "Speed mode of the SCL generator: 0 Standard-mode (100 kHz), 1 Fast-mode (400 kHz), 2 Fast-mode Plus (1 MHz). Applied only while `master_active` is 0. 3 is reserved and decoded as Standard-mode.",
    ("i2cmaster", "master_active")  : "1: request the bus for the register master (its crossbar port) and enable the PHY. Keep it at 1 for the whole transaction, chunks included.",
    ("i2cmaster", "master_addr")    : "7-bit address of the target, sent with the next element written to `master_rxtx`.",
    ("i2cmaster", "master_rxtx")    : "Read/write register (a read has a side effect: it pops the RX FIFO). Write: push one element into the TX FIFO, with up to 4 data bytes (the first byte on the bus in the most significant byte used) and the current `master_settings` and `master_addr`; check `tx_ready` first. Read: pop one status element from the RX FIFO; the last byte received is in bits 7:0.",
}

# Access of the registers that the engine cannot infer: `master_rxtx` is a plain CSR read and
# written by strobes (a read pops the RX FIFO), so it is read/write, not a write-only strobe.
ACCESS = {
    "i2cmaster_master_rxtx" : "rw",
}

# Notes printed after the title of a bank family: what the register descriptions do not say.
NOTES = {
    "i2cmaster": [
        "The PHY (`LiteI2CPHYCore`, `litei2c/phy/generic.py`) holds `phy_speed_mode`; the register",
        "master (`LiteI2CMaster`, `litei2c/core/master.py`) holds the other registers. The",
        "`master_ev_*` registers exist only with `with_irq=True`, which `add_i2c_master` sets when",
        "the CPU has an interrupt of the same name; with `with_master=False` the bank holds",
        "`phy_speed_mode` only. The fields of `master_status` other than `tx_ready` and `rx_ready`",
        "describe the head of the RX FIFO: they are valid only while `rx_ready` is 1. The bank takes",
        "the name given to `add_i2c_master`, `i2cmaster` by default ([The register master](#master)).",
    ],
}

# Opening paragraph of the appendix and the sentence that ends the access paragraph.
INTRO = ["This appendix lists the registers of LiteI2C: the speed register of the PHY and the",
         "registers of the register master. It is generated from the register definitions of the",
         "gateware, elaborated on a reference design for the Arty A7 platform without running an",
         "FPGA toolchain. Offsets are in bytes from the base of the bank; the base address depends",
         "on the SoC and is in the `csr.csv` of a build."]
USAGE = ["Software uses these names through the `csr.h` or `csr.csv` of the build",
         "([Bare-metal software](#integ-baremetal))."]
MAIN_BANK = "Registers of the top-level `main` bank of the SoC."


def _describe(soc):
    """Attach the descriptions of DESCRIPTIONS to the registers that have none in the gateware."""
    for bank, region in soc.csr.regions.items():
        if not isinstance(region.obj, list):
            continue
        for csr in region.obj:
            desc = DESCRIPTIONS.get((bank, csr.name))
            if desc and not (getattr(csr, "description", None) or "").strip():
                csr.description = desc


def _reference_soc():
    """Reference design: SoCMini on the Arty A7 platform with a LiteI2C core on Pmod B."""
    from migen.genlib.io import CRG
    from litex.build.generic_platform import Subsignal, Pins, IOStandard
    from litex.soc.integration.soc_core import SoCMini
    from litex_boards.platforms import digilent_arty

    class ReferenceSoC(SoCMini):
        def __init__(self):
            platform = digilent_arty.Platform()
            platform.add_extension([
                ("i2cmaster", 0,
                    Subsignal("scl", Pins("pmodb:0")),
                    Subsignal("sda", Pins("pmodb:1")),
                    IOStandard("LVCMOS33"),
                ),
            ])
            self.crg = CRG(platform.request("clk100"))
            SoCMini.__init__(self, platform, clk_freq=100e6)
            self.add_i2c_master(with_irq=True)

    return ReferenceSoC()


def elaborate(name, repo_root):
    """Elaborate the reference design with a Builder that runs no toolchain; return
    (soc, csr_json, module, argv)."""
    # The LiteI2C of this repository, not an installed one.
    sys.path.insert(0, repo_root)
    for mod in [m for m in sys.modules if m == "litei2c" or m.startswith("litei2c.")]:
        del sys.modules[mod]
    from litex.soc.integration.builder import Builder
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            soc     = _reference_soc()
            builder = Builder(soc, output_dir=tmp, csr_csv=os.path.join(tmp, "csr.csv"),
                csr_json=os.path.join(tmp, "csr.json"), compile_software=False,
                compile_gateware=False)
            builder.build(run=False)
            csr_json = json.load(open(os.path.join(tmp, "csr.json")))
        finally:
            os.chdir(old_cwd)
    # Memories mapped on the CSR bus have no register definitions: keep the register banks only.
    for bank, region in list(soc.csr.regions.items()):
        if not isinstance(region.obj, list):
            del soc.csr.regions[bank]
    _describe(soc)
    return soc, csr_json, "digilent_arty", CONFIGS[name]
