# Testbenches

For every module, bust writes `tb/<module>_tb.vhd`, a self-checking
testbench. It instantiates the bus endpoint `<module>_<bus>_endpoint`, drives
the bus with a bus functional model (BFM), drives the `from_hw` record,
watches the `to_hw` record, and checks the results with
[UVVM](https://github.com/UVVM/UVVM). It does not use your `<module>.vhd`. This page describes what the testbench
checks, what it needs, and how to compile and run it.

bust does not write simulator scripts, so you add the testbench to your own
simulation flow.

## What it checks

The testbench entity is `<module>_tb`, with no ports or generics. It runs a
10 ns clock and holds the module in reset for 500 ns. It sets the base address
to 0 with `G_BASE_ADDRESS`, the base address check on with
`G_CHECK_BASE_ADDRESS`, and `G_MODULE_ADDR_WIDTH` two bits larger than the
registers need. It then runs one group of checks for each
kind of register below. A register that fits a row gets that row's checks.

| Register                                                                                                     | Checks                                                                                                                                                                                       |
|--------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Plain read-write: every field `sw: rw`, with no side effect, enumeration or hardware writer                  | Writes 1 to every field bit, reads the same value back, and checks that `to_hw` shows it for each field hardware reads.                                                                     |
| One enumerated read-write field                                                                              | Writes the highest value of the enumeration and reads it back.                                                                                                                               |
| Write-only, or `singlepulse` with a reset of 0                                                               | Writes 1 to every field bit and checks that the register reads back 0.                                                                                                                      |
| `onwrite` side effects on read-write fields                                                                  | Writes `0101...` to each field and checks that the readback matches the `onwrite` rule of each field, starting from its reset value.                                                       |
| `onread` side effects on read-write fields                                                                   | Writes `0101...`, reads it back, then reads again and checks that `rclr` fields read 0 and `rset` fields read all 1s.                                                                       |
| Hardware status: every field `sw: ro` and written by hardware, without `hwset`, `hwclr` or an enumeration      | Drives `0101...` on `from_hw`, asserts `we` or `wel` for one clock cycle where the field has one, and reads the register back.                                                              |
| `we`, `hwset` or `hwclr` on read-write fields that hardware reads                                            | Up to four steps, each ending with a read: a software write, also checked on `to_hw`, then a hardware write with `we`, then `hwset`, then `hwclr` together with `hwset`, where `hwclr` must win. |
| `swmod`, `swacc` or `singlepulse`                                                                            | Counts the strobe pulses on `to_hw` during a write and a read: `swmod` must pulse once, `swacc` twice, and a `singlepulse` field must hold the written value for exactly one clock cycle.    |
| One field with `hwset`, `onread: rclr` and `swacc`                                                           | Holds `hwset` through a read and checks that the field is still set afterwards, since hardware wins over the read clear. Once `hwset` is released, a read clears it.                        |

Last, the testbench writes and reads addresses where no register sits: an
unused register offset if there is one, an address one byte into a register
when addresses count bytes, an address above the registers, and an address with
another base address. Each access must get an
[error response](buses.md#errors), or read 0 on SBI and Avalon-MM, which have
none. A plain read-write register is then read again to check that none of
these writes reached it.

The groups run in the order of the table, not in register order. A register
can be in more than one group. A read-write register with a `swmod` field, for
example, gets both the plain read-write checks and the strobe checks.
[Access modes](access-modes.md) describes the behaviour these checks expect.

The testbench does not check reset values directly. Registers that fit no row
get no checks. Examples are read-only constants (`sw: ro` with no hardware
writer), enumerated fields that hardware writes, and a register with a field
that software cannot access (`sw: na`).

This is the `onread` group and part of the hardware modifier group from the
testbench of the prototype example in the repository, where `reg5` has an
`rclr` and an `rset` field and `reg4` has a `we` field and a field with both
`hwset` and `hwclr`:

```vhdl
log(ID_LOG_HDR, "reg5: onread software side effects", C_SCOPE);
bus_write(f_addr(C_ADDR_REG5), 32x"00000055", "write reg5");
bus_check(f_addr(C_ADDR_REG5), 32x"00000055", "reg5 first read returns stored value");
bus_check(f_addr(C_ADDR_REG5), 32x"000000F0", "reg5 second read reflects onread");

log(ID_LOG_HDR, "reg4: hardware we overrides the stored value", C_SCOPE);
wait until falling_edge(clk);
from_hw.reg4.field0.value <= 4x"A";
from_hw.reg4.field0.we <= '1';
wait until falling_edge(clk);
from_hw.reg4.field0.we <= '0';
bus_check(f_addr(C_ADDR_REG4), 32x"0000010A", "reg4 reflects the hardware we override");

log(ID_LOG_HDR, "reg4: hwclr clears fields (and beats hwset)", C_SCOPE);
wait until falling_edge(clk);
from_hw.reg4.field1.set <= '1';
from_hw.reg4.field1.clr <= '1';
wait until falling_edge(clk);
from_hw.reg4.field1.set <= '0';
from_hw.reg4.field1.clr <= '0';
bus_check(f_addr(C_ADDR_REG4), 32x"0000000A", "reg4 reflects hwclr");
```

`bus_write` and `bus_check` wrap the BFM of the bus. `C_ADDR_REG5` and
`C_ADDR_REG4` are the register addresses from `<module>_regfile_pkg`.

## Pass or fail

Every check is a UVVM check with alert level `error`. The testbench turns off
UVVM's other log messages and logs one header line for each group, such as
`reg5: onread software side effects`, so the log shows how far it got.

UVVM stops the simulation at the first error by default. The alert message
names the register, the value read and the value expected.

When every check passes, the testbench prints UVVM's alert summary, which ends
with:

```text
>> Simulation SUCCESS: No mismatch between counted and expected serious alerts
```

It then logs `SIMULATION COMPLETED` and ends the simulation with
`std.env.stop`. In a script, treat a non-zero exit status from the simulator,
or a UVVM `FAIL` line in the log, as a failure.

## What it needs

- **VHDL-2008.** The testbench uses context clauses, sized bit-string literals
  such as `32x"00000055"`, and `std.env.stop`.
- **The generated files from the same run**, compiled into the same library as
  the testbench. Every generated file and the testbench refer to each other
  through `work`.
- **UVVM's `uvvm_util` library**, for logging and checks.
- **The BFM for the bus**, in a library with the name the testbench uses:

| Bus        | Libraries the testbench uses                       | BFM                                                                                                                                                                                                   |
|------------|----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `axi`      | `uvvm_util`, `bitvis_vip_axilite`                  | `axilite_bfm_pkg` from UVVM's AXI4-Lite VIP.                                                                                                                                                          |
| `ipbus`    | `uvvm_util`, `ipbus`, `vip_ipbus`                  | `ipbus_bfm_pkg` from [vip_ipbus](https://github.com/olagrottvik/vip_ipbus). The `ipbus` library holds `ipbus_package.vhd` from [ipbus-firmware](https://github.com/ipbus/ipbus-firmware).             |
| `sbi`      | `uvvm_util`, `bitvis_vip_sbi`                      | `sbi_bfm_pkg` from UVVM's SBI VIP.                                                                                                                                                                    |
| `avalon`   | `uvvm_util`, `bitvis_vip_avalon_mm`                | `avalon_mm_bfm_pkg` from UVVM's Avalon-MM VIP.                                                                                                                                                        |
| `wishbone` | `uvvm_util`                                        | A Wishbone classic master BFM written into the testbench itself.                                                                                                                                      |
| `apb`      | `uvvm_util`                                        | An APB master BFM written into the testbench itself.                                                                                                                                                  |

The testbench uses only the BFM package of each VIP, not its VVC.

For IPBus, the generated endpoint and the starter top level also use the
`ipbus` library, so you need it for synthesis as well. `vip_ipbus` uses `uvvm_util` and
`ipbus`, so compile it after both.

## Compile and run

In any simulator, the steps are:

1. Compile `uvvm_util` into a library named `uvvm_util`.
2. Compile the libraries for your bus from the table above. For IPBus, compile
   `ipbus` before `vip_ipbus`.
3. Compile the generated files and the testbench into one library, in this
   order:
   1. `hdl/<module>_localbus_pkg.vhd`
   2. `hdl/<module>_regfile_pkg.vhd`
   3. `hdl/<module>_regfile.vhd`
   4. `hdl/<module>_<bus>_endpoint.vhd`
   5. `tb/<module>_tb.vhd`
4. Elaborate and run `<module>_tb`.

Several modules can share one library. Every package carries the module name,
so the generated files of two modules do not clash.

### Example with nvc

This example follows the scripts the bust repository uses to simulate its own
examples with [nvc](https://github.com/nickg/nvc). It is one way to do it, not
something bust installs.

nvc can fetch and compile UVVM, including `uvvm_util` and all its VIPs, into
its own library directory, where it finds them without further options:

```bash
nvc --install uvvm
```

For an AXI4-Lite module, that is all you need. From the directory you gave to
`-o`, compile the files of the module into the default `work` library, then
elaborate and run the testbench:

```bash
nvc --std=08 -a example_axi/hdl/example_axi_localbus_pkg.vhd \
    example_axi/hdl/example_axi_regfile_pkg.vhd \
    example_axi/hdl/example_axi_regfile.vhd \
    example_axi/hdl/example_axi_axi_endpoint.vhd \
    example_axi/tb/example_axi_tb.vhd
nvc --std=08 -e example_axi_tb
nvc --std=08 -r example_axi_tb
```

SBI, Avalon-MM, Wishbone and APB modules work the same way, with their own
endpoint file.

An IPBus module also needs the `ipbus` and `vip_ipbus` libraries. With
checkouts of ipbus-firmware and vip_ipbus in the same directory, compile them
into a directory `libs` and add it to the library search path with `-L`:

```bash
mkdir -p libs
nvc --std=08 --work=ipbus:libs/ipbus \
    -a ipbus-firmware/components/ipbus_core/firmware/hdl/ipbus_package.vhd
nvc --std=08 -L libs --work=vip_ipbus:libs/vip_ipbus \
    -a --relaxed vip_ipbus/src/ipbus_bfm_pkg.vhd
```

`vip_ipbus` needs `--relaxed`, because UVVM uses a shared variable as a default
parameter value, which strict VHDL-2008 does not allow. nvc takes `--relaxed`
only after `-a`. Then compile and run the module as for AXI4-Lite, with
`-L libs` on every command:

```bash
nvc --std=08 -L libs -a example_ipbus/hdl/example_ipbus_localbus_pkg.vhd \
    example_ipbus/hdl/example_ipbus_regfile_pkg.vhd \
    example_ipbus/hdl/example_ipbus_regfile.vhd \
    example_ipbus/hdl/example_ipbus_ipb_endpoint.vhd \
    example_ipbus/tb/example_ipbus_tb.vhd
nvc --std=08 -L libs -e example_ipbus_tb
nvc --std=08 -L libs -r example_ipbus_tb
```

The repository's CI compiles and runs the generated testbenches of its
examples this way, including one for each of the six buses. It uses nvc 1.19.3,
ipbus-firmware v1.16 and a fixed commit of vip_ipbus, in the Docker image
described in [`sim/`](https://github.com/logvik-org/bust/tree/master/sim).
