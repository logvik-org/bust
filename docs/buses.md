# Buses

bust generates one bus endpoint per module, for the bus you choose with `type`
in the `bus` object of the register map:

```json
"bus": {
  "type": "axi",
  "addr_width": 32,
  "data_width": 32
}
```

| `type` | Bus | Endpoint entity | Reset |
|--------|-----|-----------------|-------|
| `axi` | [AXI4-Lite](#axi4-lite) | `<module>_axi_endpoint` | `areset_n`, active low |
| `ipbus` | [IPBus](#ipbus) | `<module>_ipb_endpoint` | `reset`, active high |
| `sbi` | [SBI](#sbi) | `<module>_sbi_endpoint` | `reset`, active high |
| `avalon` | [Avalon-MM](#avalon-mm) | `<module>_avalon_endpoint` | `reset`, active high |
| `wishbone` | [Wishbone](#wishbone) | `<module>_wishbone_endpoint` | `rst_i`, active high |
| `apb` | [APB](#apb) | `<module>_apb_endpoint` | `presetn`, active low |

You instantiate the top wrapper `<module>`, which has the same generics and
ports as its endpoint. Besides the bus ports listed below, both also have the
`to_hw` and `from_hw` ports of the register file. See
[Generated HDL](generated-hdl.md).

## Common behaviour

Every endpoint is a thin bridge to the same register file, so all buses behave
the same apart from the handshake.

### Transfers

- An endpoint handles one single-beat transfer at a time. There are no bursts
  and no outstanding transactions.
- No endpoint has byte enables or write strobes, so software must read and
  write whole registers. A write always writes the whole register, so a byte or
  halfword write to a register writes all its bytes. A read of an address
  inside a register, such as a byte read of byte 1, gets an error.
- Every endpoint answers in the clock cycle after the request, never later.
  A transfer therefore takes at least two clock cycles.

### Addressing

- The address port is `addr_width` bits wide and the data ports are
  `data_width` bits wide. IPBus is the exception, with fixed 32-bit ports.
- The endpoint passes the address to the register file unchanged, except that
  IPBus passes the low `addr_width` bits. By default it is a byte address on
  every bus except IPBus, where it is a word address. When bust
  assigns the addresses, with 32-bit data, the registers are at `0x0`, `0x4`,
  `0x8` and so on, and on IPBus at `0x0`, `0x1`, `0x2`. Addresses you set in
  the JSON are used as they are. See [Register map format](register-map-format.md).
- The register file compares the whole address, low bits included, with the
  register addresses. An address between two registers or inside one, such as
  `0x2` on a byte-addressed bus, matches no register and gets an error.
- Some masters and interconnects drive word addresses on a bus other than
  IPBus. For those, set `"byte_addressable": false` in the module, and bust
  places the registers at `0x0`, `0x1`, `0x2`. See
  [Byte and word addresses](register-map-format.md#byte-and-word-addresses).

### Errors

Only an address that does not decode produces an error:

- a register offset where no register sits, or an address above the
  registers in the module's address range when `G_MODULE_ADDR_WIDTH` is larger
  than `C_MODULE_ADDR_WIDTH`, or
- with `G_CHECK_BASE_ADDRESS` set to `true`, an address whose base address
  bits differ from `G_BASE_ADDRESS`.

[Base address and address range](addressing.md) shows which bits are which. A write
that fails changes nothing, and a read that fails returns 0. Every
access to a register address completes normally, whatever the access mode.
Writing a read-only field has no effect, and reading a write-only field returns
0. See [Access modes](access-modes.md).

| Bus | Error response |
|-----|----------------|
| AXI4-Lite | `SLVERR` on `bresp` or `rresp` |
| IPBus | `ipb_err` instead of `ipb_ack` |
| SBI | None. The transfer completes with `ready` as usual. |
| Avalon-MM | None. The transfer completes as usual. |
| Wishbone | `err_o` instead of `ack_o` |
| APB | `pslverr` together with `pready` |

### Reset

The register file resets synchronously on every bus. The registers take their
reset values on a rising clock edge while the reset is asserted, so hold the
reset for at least one clock cycle. On AXI4-Lite and APB, the endpoint's own
handshake state also resets asynchronously.

### Base address

All endpoints have the generics `G_BASE_ADDRESS`, `G_CHECK_BASE_ADDRESS` and
`G_MODULE_ADDR_WIDTH`. [Base address and address range](addressing.md) describes
them.

### Testbenches

bust generates a self-checking testbench for every bus. It drives the module
with a UVVM verification IP where one exists, and with a bus master inside the
testbench otherwise. See [Testbenches](testbenches.md).

| Bus | Bus master in the testbench |
|-----|-----------------------------|
| AXI4-Lite | UVVM AXI4-Lite VIP (`bitvis_vip_axilite`) |
| IPBus | [vip_ipbus](https://github.com/olagrottvik/vip_ipbus) |
| SBI | UVVM SBI VIP (`bitvis_vip_sbi`) |
| Avalon-MM | UVVM Avalon-MM VIP (`bitvis_vip_avalon_mm`) |
| Wishbone | A master inside the testbench |
| APB | A master inside the testbench |

## AXI4-Lite

[AXI4-Lite](https://en.wikipedia.org/wiki/Advanced_eXtensible_Interface#AXI4-Lite)
is the `axi` bus type. The endpoint is `<module>_axi_endpoint`.

| Port | Direction | Width |
|------|-----------|-------|
| `clk` | in | 1 |
| `areset_n` | in | 1 |
| `awaddr` | in | `addr_width` |
| `awvalid` | in | 1 |
| `awready` | out | 1 |
| `wdata` | in | `data_width` |
| `wvalid` | in | 1 |
| `wready` | out | 1 |
| `bresp` | out | 2 |
| `bvalid` | out | 1 |
| `bready` | in | 1 |
| `araddr` | in | `addr_width` |
| `arvalid` | in | 1 |
| `arready` | out | 1 |
| `rdata` | out | `data_width` |
| `rresp` | out | 2 |
| `rvalid` | out | 1 |
| `rready` | in | 1 |

- The endpoint accepts a write when `awvalid` and `wvalid` are both high, and
  raises `awready` and `wready` together for that one cycle. It does not
  accept the address and the data in different cycles.
- It accepts a read when `arvalid` is high, and raises `arready` for one cycle.
  If `awvalid`, `wvalid` and `arvalid` are all high in the same cycle, the
  write goes first.
- `bvalid` or `rvalid` rises in the cycle after the accept and stays high until
  `bready` or `rready` is high. The endpoint accepts the next transfer in the
  cycle after that.
- `bresp` and `rresp` are `OKAY` (`"00"`) or `SLVERR` (`"10"`). `rdata` is 0
  with `SLVERR`.
- There are no `awprot`, `arprot` or `wstrb` ports.
- `awready`, `wready` and `arready` are combinational from `awvalid`, `wvalid`
  and `arvalid`. If your interconnect or your timing needs registered ready
  signals, put a register slice in front of the module.
- `areset_n` is active low.
- AXI4-Lite allows a `data_width` of 32 or 64.

## IPBus

[IPBus](https://ipbus.web.cern.ch/ipbus/) is the `ipbus` bus type. The endpoint
is `<module>_ipb_endpoint`.

| Port | Direction | Type |
|------|-----------|------|
| `clk` | in | `std_logic` |
| `reset` | in | `std_logic` |
| `ipb_in` | in | `ipb_wbus` |
| `ipb_out` | out | `ipb_rbus` |

`ipb_wbus` and `ipb_rbus` are the records of the IPBus package. The endpoint
and the top wrapper use it as `library ipbus; use ipbus.ipbus.all;`, so compile
`components/ipbus_core/firmware/hdl/ipbus_package.vhd` from the
[IPBus firmware](https://github.com/ipbus/ipbus-firmware) into a library called
`ipbus` before the module. The endpoint uses these members:

| Member | Width | Use |
|--------|-------|-----|
| `ipb_in.ipb_addr` | 32 | Word address. The low `addr_width` bits are used. |
| `ipb_in.ipb_wdata` | 32 | Write data. |
| `ipb_in.ipb_strobe` | 1 | Starts a transfer. |
| `ipb_in.ipb_write` | 1 | High for a write, low for a read. |
| `ipb_out.ipb_rdata` | 32 | Read data. |
| `ipb_out.ipb_ack` | 1 | The transfer completed. |
| `ipb_out.ipb_err` | 1 | The address did not decode. |

- `ipb_strobe` starts a transfer. `ipb_ack` or `ipb_err` is high for one cycle,
  in the cycle after the strobe, with `ipb_rdata` valid on a read.
- `ipb_rdata` is 0 when a read gets `ipb_err`.
- `reset` is active high.
- `data_width` must be 32 and `addr_width` at most 32. bust stops with an
  error for other values.
- With an `addr_width` below 32, the endpoint ignores the upper bits of
  `ipb_addr`, so decode them before the module, as an IPBus fabric does.
- bust also writes an IPBus address table for uHAL. See
  [Headers and documentation](headers-and-docs.md).

## SBI

SBI is the Simple Bus Interface of [UVVM](https://github.com/UVVM/UVVM), the
bus of its `bitvis_vip_sbi` verification IP. It is the `sbi` bus type. The
endpoint is `<module>_sbi_endpoint`.

| Port | Direction | Width |
|------|-----------|-------|
| `clk` | in | 1 |
| `reset` | in | 1 |
| `cs` | in | 1 |
| `addr` | in | `addr_width` |
| `rena` | in | 1 |
| `wena` | in | 1 |
| `wdata` | in | `data_width` |
| `ready` | out | 1 |
| `rdata` | out | `data_width` |

- The master raises `cs` together with `wena` or `rena`, and holds the request
  until `ready` is high. `ready` is high for one cycle, in the cycle after the
  request, with `rdata` valid on a read.
- SBI has no error signal. An access that does not decode completes with
  `ready` as usual, with `rdata` 0 on a read.
- SBI defines no reset. bust adds `reset`, active high.

## Avalon-MM

[Avalon-MM](https://www.intel.com/content/www/us/en/docs/programmable/683091/current/introduction-to-the-interface-specifications.html)
is the `avalon` bus type. The endpoint is `<module>_avalon_endpoint`, an
Avalon-MM agent.

| Port | Direction | Width |
|------|-----------|-------|
| `clk` | in | 1 |
| `reset` | in | 1 |
| `chipselect` | in | 1 |
| `address` | in | `addr_width` |
| `read` | in | 1 |
| `write` | in | 1 |
| `writedata` | in | `data_width` |
| `waitrequest` | out | 1 |
| `readdata` | out | `data_width` |

- A transfer starts when `chipselect` is high together with `read` or `write`.
  The host holds the command while `waitrequest` is high.
- `waitrequest` is high whenever the endpoint is not completing a transfer,
  also while idle. It goes low for one cycle, in the cycle after the command,
  and `readdata` is valid in that cycle. Every transfer therefore has one wait
  state.
- There is no `readdatavalid`, so reads are not pipelined. There is also no
  `byteenable`, `burstcount` or `response`.
- An access that does not decode completes as usual, with `readdata` 0 on a
  read.
- If your host has no chip select, tie `chipselect` to `'1'`.
- `reset` is active high.

## Wishbone

[Wishbone](https://wishbone-interconnect.readthedocs.io/) is the `wishbone` bus
type. The endpoint is `<module>_wishbone_endpoint`, a Wishbone B4 slave for
classic cycles.

| Port | Direction | Width |
|------|-----------|-------|
| `clk_i` | in | 1 |
| `rst_i` | in | 1 |
| `cyc_i` | in | 1 |
| `stb_i` | in | 1 |
| `we_i` | in | 1 |
| `adr_i` | in | `addr_width` |
| `dat_i` | in | `data_width` |
| `dat_o` | out | `data_width` |
| `ack_o` | out | 1 |
| `err_o` | out | 1 |

- A transfer starts when `cyc_i` and `stb_i` are both high, and `we_i` selects
  write or read. `ack_o` or `err_o` is high for one cycle, in the cycle after,
  with `dat_o` valid on a read. The master holds the request until then.
- `dat_o` is 0 when a read gets `err_o`.
- There are no `sel_i`, `rty_o`, `stall_o`, `cti_i`, `bte_i` or `lock_i`
  ports, so the endpoint supports neither the pipelined mode nor registered
  feedback bursts.
- `rst_i` is active high.

## APB

[APB](https://developer.arm.com/documentation/ihi0024/latest/) (AMBA APB) is the
`apb` bus type. The endpoint is `<module>_apb_endpoint`.

| Port | Direction | Width |
|------|-----------|-------|
| `pclk` | in | 1 |
| `presetn` | in | 1 |
| `psel` | in | 1 |
| `penable` | in | 1 |
| `pwrite` | in | 1 |
| `paddr` | in | `addr_width` |
| `pwdata` | in | `data_width` |
| `prdata` | out | `data_width` |
| `pready` | out | 1 |
| `pslverr` | out | 1 |

- The ports are the APB3 signal set, with `pready` and `pslverr`. The APB4
  signals `pprot` and `pstrb` are not there.
- The endpoint starts the access in the SETUP cycle and raises `pready` in the
  first ACCESS cycle, so transfers have no wait states.
- On an error, `pslverr` is high together with `pready`, and `prdata` is 0 on a
  read.
- `presetn` is active low.
