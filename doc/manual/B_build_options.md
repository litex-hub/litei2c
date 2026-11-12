# Build options {#build-options}

This appendix lists the parameters of every part of LiteI2C and of the LiteX method that adds it
to a SoC, with their defaults. The chapters explain when to use them; this appendix gives their
names. The core has no generator script and no command-line option of its own: a target exposes
the options it wants.

## SoC method {#opt-soc}

`SoC.add_i2c_master()` (LiteX, `litex/soc/integration/soc.py`) builds a `LiteI2C` core and adds it
to the SoC under `name` ([Integration](#integration)).

| Parameter | Default | Meaning |
|----------------|-------------------|----------------------------------------------------------------|
| `name` | `"i2cmaster"` | Name of the core, of its register bank and of its interrupt |
| `pads` | `None` | Pads of the bus; `None` requests the platform pads called `name` |
| `**kwargs` | | Passed to `LiteI2C` (table below) |

When the CPU has interrupts and an interrupt location named `name`, the method sets
`with_irq=True` unless the caller passes `with_irq`, and adds the interrupt of the core.

## Core {#opt-core}

`LiteI2C` (`litei2c/__init__.py`) holds the PHY, the crossbar and the register master.

| Parameter | Default | Meaning |
|------------------------------------------|------------|-------------------------------------------|
| `sys_clk_freq` | required | Frequency of the PHY clock (`sys`, or `clock_domain`) in Hz; sets the SCL dividers and the stretch timeout |
| `phy` | `None` | A PHY built by the caller; `None` builds `LiteI2CPHYCore` on `pads` |
| `pads` | `None` | Pads of the bus, required when `phy` is `None` |
| `clock_domain` | `"sys"` | Clock domain of the PHY; another domain adds two asynchronous FIFOs of 32 entries in the crossbar and a `MultiReg` on `active` ([status](#intro-status)) |
| `with_master` | `True` | Adds the register master |
| `i2c_master_tx_fifo_depth` | `1` | Depth of the TX FIFO of the master, in elements |
| `i2c_master_rx_fifo_depth` | `1` | Depth of the RX FIFO of the master, in status elements |
| `with_irq` | `False` | Adds the `rx_ready` event of the master and its registers |

`LiteI2C.add_i2c_device(dev)` adds a crossbar port for a gateware user. `dev` provides `source`
(elements, `i2c_core2phy_layout`), `sink` (statuses, `i2c_phy2core_layout`) and `active`, as the
`LiteI2CCore` class of the same file declares them ([Architecture](#architecture)).

## PHY and clock generator {#opt-phy}

| Class | Parameters | Meaning |
|------------------------------|---------------------------------------------|------------------------------------|
| `LiteI2CPHYCore` | `pads`, `clock_domain`, `sys_clk_freq` | The PHY, in `phy/generic.py`; it runs in `clock_domain`, and `sys_clk_freq` is the frequency of that clock |
| `LiteI2CClkGen` | `pads`, `i2c_speed_mode`, `sys_clk_freq` | SCL generator and SCL I/O, in `clkgen.py`, built by the PHY |

The speed register of the PHY selects one of three dividers, computed at build time from
`sys_clk_freq` ([The PHY](#phy)):

| `phy_speed_mode` | Mode | Nominal SCL |
|------------------|---------------------|-------------|
| 0 (reset) | Standard-mode | 100 kHz |
| 1 | Fast-mode | 400 kHz |
| 2 | Fast-mode Plus | 1 MHz |
| 3 | Reserved, decoded as Standard-mode | 100 kHz |

## Pads {#opt-pads}

| Subsignals | Meaning |
|------------------------------------|----------------------------------------------------------------|
| `scl`, `sda` | Bidirectional pins; the PHY instantiates one `SDRTristate` per line |
| `scl_o`, `scl_oe`, `scl_i` | Split SCL; without `scl_i` the PHY sees SCL always high and detects no stretching |
| `sda_o`, `sda_oe`, `sda_i` | Split SDA; without `sda_i` the PHY sees SDA always high |

The split form is chosen per line, when the pads have both `_o` and `_oe`. The PHY drives the `_o`
signals to 0 and pulls a line low by setting `_oe`.

## Register master and crossbar {#opt-master}

| Class | Parameter | Default | Meaning |
|--------------------------|----------------------|-----------|----------------------------------|
| `LiteI2CMaster` | `tx_fifo_depth` | `1` | Depth of the TX FIFO |
| | `rx_fifo_depth` | `1` | Depth of the RX FIFO |
| | `with_irq` | `False` | Adds the event manager (`ev`) |
| `LiteI2CCrossbar` | `cd` | | Clock domain of the PHY side |
| `get_port()` | `active` | required | Signal that requests and holds the bus for this port |
| | `request` | `None` | Separate request signal; `None` uses `active` |

The crossbar grants the bus to one port at a time with a round-robin arbiter; the `active` signal
of the granted port drives the `active` input of the PHY.

## Where to go next {#opt-next}

[Integration](#integration) for the use of these parameters in a SoC; [Register
reference](#registers) for the registers they add.
