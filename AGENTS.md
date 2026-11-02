# AGENTS.md: LiteI2C

I2C master core for LiteX: PHY, core with a command FIFO, crossbar and clock generator.

Read the LiteX agent page first: https://github.com/enjoy-digital/litex/wiki/LiteX-for-AI-Agents (framework map, conventions, how to
verify a change, contribute back). Index of the whole wiki for agents: https://github.com/enjoy-digital/litex/wiki/llms.txt.

## Where things are

- `litei2c/phy/`, `litei2c/core/`, `litei2c/crossbar.py`, `litei2c/clkgen.py`, `litei2c/common.py`; `test/`.

## Verify a change

```sh
python3 -m pytest -q test                                           # unit tests (no CI workflow yet)
python3 -m litex_boards.targets.<board> --build --no-compile         # with a target using LiteI2C
```

- Bus robustness (clock stretching, arbitration loss, NACK, stuck bus) is the usual source of
  hardware bugs: add a simulation test for the case, then say which devices ran on hardware.

## Rules

- Style: https://github.com/enjoy-digital/litex/blob/master/doc/coding_style.md (match the
  surrounding file; `module: Description of the change.` commit titles; one change per commit).
- Never edit generated files (`build/`, `csr.h`, `csr.csv`, the Verilog): change the Python.
- One topic per pull request, from the default development branch, with what was tested and on
  which hardware; say that an agent wrote it and who supervised. Do not rename options or
  reformat unrelated code.
- Hardware: never flash a board or write its SPI flash unless the user asked; `--load` (volatile)
  is the default for experiments.

## Debug on hardware

Method: https://github.com/enjoy-digital/litex/wiki/Debug-A-SoC-On-Hardware (check the link and `--ident` first, registers before
traces, narrow LiteScope captures). `litex_mcp` gives the same loop as MCP tools (CSRs by name,
LiteScope captures, builds with parsed timing, simulation): https://github.com/enjoy-digital/litex/wiki/LiteX-for-AI-Agents#drive-a-soc-through-mcp.
