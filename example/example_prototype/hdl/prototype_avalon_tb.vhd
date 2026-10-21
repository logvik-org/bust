-- Generated UVVM testbench for the prototype module (Avalon-MM).
-- Drives the prototype top entity with the stock Bitvis Avalon-MM VIP and
-- self-checks every register of the module, by kind: plain
-- read-write, enumerated, write-only/singlepulse (reads back 0), onread/onwrite
-- software side effects, software-readonly registers driven from from_hw
-- (we/wel), the hardware we override / hwset / hwclr modifiers, the to_hw values
-- the hardware sees, and the swmod/swacc/singlepulse to_hw strobe pulses (counted
-- by a monitor process, since they are single-cycle). The endpoint does not
-- implement the optional Avalon-MM response signal (decode errors complete as a
-- normal beat with readdata 0), so use_response_signal is off.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library bitvis_vip_avalon_mm;
use bitvis_vip_avalon_mm.avalon_mm_bfm_pkg.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_tb is
end entity prototype_tb;

architecture tb of prototype_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  constant C_BASE : std_logic_vector(31 downto 0) := 32x"0";

  signal clk   : std_logic := '0';
  signal reset : std_logic := '0';   -- active-high; gen_pulse asserts it

  -- What a read gets where no register sits (G_UNMAPPED_READ_DATA).
  constant C_UNMAPPED_READ_DATA : std_logic_vector(31 downto 0) := 32x"DEADBEEF";

  signal to_hw    : t_prototype_to_hw;
  signal from_hw  : t_prototype_from_hw := (
    reg1 => (field0 => (value => (others => '0'), we => '0'), field1 => '0', field2 => (value => '0', wel => '1')),
    reg4 => (field0 => (value => (others => '0'), we => '0'), field1 => (set => '0', clr => '0')));

  constant C_DATA_W : natural := 32;
  constant C_ADDR_W : natural := 32;
  signal avmm_if : t_avalon_mm_if(address(C_ADDR_W-1 downto 0),
                                  byte_enable((C_DATA_W/8)-1 downto 0),
                                  writedata(C_DATA_W-1 downto 0),
                                  readdata(C_DATA_W-1 downto 0))
                   := init_avalon_mm_if_signals(C_ADDR_W, C_DATA_W);
  signal avmm_bfm_config : t_avalon_mm_bfm_config := C_AVALON_MM_BFM_CONFIG_DEFAULT;

  function f_addr(reg : std_logic_vector(31 downto 0)) return unsigned is
  begin
    return unsigned(C_BASE) + unsigned(reg);
  end function;

  -- Strobe monitors: count the cycles each swmod/swacc output is high and each
  -- singlepulse output differs from its reset value, so single-cycle pulses are
  -- verifiable without cycle-accurate sampling.
  signal reg9_field0_swmod_count : natural := 0;
  signal reg9_field1_swacc_count : natural := 0;
  signal reg10_field0_sp_count : natural := 0;
  signal reg10_field0_sp_value : std_logic_vector(3 downto 0) := (others => '0');

begin

  clock_generator(clk, C_CLK_PERIOD);

  DUT : entity work.prototype_avalon_endpoint
    generic map (
      G_BASE_ADDRESS       => unsigned(C_BASE),
      G_CHECK_BASE_ADDRESS => true,
      G_MODULE_ADDR_WIDTH  => 8,
      G_UNMAPPED_READ_DATA => C_UNMAPPED_READ_DATA)
    port map (
      clk         => clk,
      reset       => reset,
      chipselect  => avmm_if.chipselect,
      address     => avmm_if.address,
      read        => avmm_if.read,
      write       => avmm_if.write,
      writedata   => avmm_if.writedata,
      waitrequest => avmm_if.waitrequest,
      readdata    => avmm_if.readdata,      to_hw       => to_hw,      from_hw     => from_hw);

  p_strobe_monitor : process (clk) is
  begin
    if rising_edge(clk) then
      if to_hw.reg9.field0.swmod = '1' then
        reg9_field0_swmod_count <= reg9_field0_swmod_count + 1;
      end if;
      if to_hw.reg9.field1.swacc = '1' then
        reg9_field1_swacc_count <= reg9_field1_swacc_count + 1;
      end if;
      if to_hw.reg10.field0 /= 4x"0" then
        reg10_field0_sp_count <= reg10_field0_sp_count + 1;
        reg10_field0_sp_value <= to_hw.reg10.field0;
      end if;
    end if;
  end process p_strobe_monitor;

  p_main : process is

    procedure bus_write(constant addr : in unsigned;
                        constant data : in std_logic_vector;
                        constant msg  : in string) is
    begin
      avalon_mm_write(addr, data, msg, clk, avmm_if, C_SCOPE,
                      shared_msg_id_panel, avmm_bfm_config);
    end procedure;

    procedure bus_check(constant addr : in unsigned;
                        constant data : in std_logic_vector;
                        constant msg  : in string) is
    begin
      avalon_mm_check(addr, data, msg, clk, avmm_if, error, C_SCOPE,
                      shared_msg_id_panel, avmm_bfm_config);
    end procedure;

    -- The endpoint does not use the Avalon-MM response signal, so an address
    -- without a register completes normally and reads 0.
    procedure bus_write_unmapped(constant addr : in unsigned;
                                 constant data : in std_logic_vector;
                                 constant msg  : in string) is
    begin
      bus_write(addr, data, msg);
    end procedure;

    procedure bus_check_unmapped(constant addr : in unsigned;
                                 constant msg  : in string) is
    begin
      bus_check(addr, C_UNMAPPED_READ_DATA, msg);
    end procedure;
    variable v_reg9_field0_swmod : natural;
    variable v_reg9_field1_swacc : natural;
    variable v_reg10_field0_sp : natural;

  begin
    avmm_bfm_config.clock_period        <= C_CLK_PERIOD;
    avmm_bfm_config.use_response_signal <= false;
    avmm_bfm_config.use_begintransfer   <= false;

    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);

    gen_pulse(reset, '1', 500 ns, BLOCKING, "Reset for 500 ns");

    log(ID_LOG_HDR, "reg0: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG0), 32x"00000007", "write reg0");
    bus_check(f_addr(C_ADDR_REG0), 32x"00000007", "reg0 reads back");
    check_value(to_hw.reg0.field0, '1', error, "reg0.field0 exposed to hw", C_SCOPE);
    check_value(to_hw.reg0.field1, 2x"3", error, "reg0.field1 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg3: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG3), 32x"000000FF", "write reg3");
    bus_check(f_addr(C_ADDR_REG3), 32x"000000FF", "reg3 reads back");

    log(ID_LOG_HDR, "reg9: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG9), 32x"000000FF", "write reg9");
    bus_check(f_addr(C_ADDR_REG9), 32x"000000FF", "reg9 reads back");
    check_value(to_hw.reg9.field0.value, 4x"F", error, "reg9.field0 exposed to hw", C_SCOPE);
    check_value(to_hw.reg9.field1.value, 4x"F", error, "reg9.field1 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg11: enumerated round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG11), 32x"00000003", "write reg11");
    bus_check(f_addr(C_ADDR_REG11), 32x"00000003", "reg11 reads back encoded value");

    log(ID_LOG_HDR, "reg2: write-only / pulse reads back zero", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG2), 32x"00000001", "write reg2");
    bus_check(f_addr(C_ADDR_REG2), 32x"0", "reg2 reads back zero");

    log(ID_LOG_HDR, "reg10: write-only / pulse reads back zero", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG10), 32x"0000000F", "write reg10");
    bus_check(f_addr(C_ADDR_REG10), 32x"0", "reg10 reads back zero");

    log(ID_LOG_HDR, "reg6: onwrite software side effects", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG6), 32x"00000555", "write reg6");
    bus_check(f_addr(C_ADDR_REG6), 32x"000005A5", "reg6 applies onwrite effects");

    log(ID_LOG_HDR, "reg7: onwrite software side effects", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG7), 32x"00000555", "write reg7");
    bus_check(f_addr(C_ADDR_REG7), 32x"00000A5A", "reg7 applies onwrite effects");

    log(ID_LOG_HDR, "reg8: onwrite software side effects", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG8), 32x"00000055", "write reg8");
    bus_check(f_addr(C_ADDR_REG8), 32x"000000F0", "reg8 applies onwrite effects");

    log(ID_LOG_HDR, "reg5: onread software side effects", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG5), 32x"00000055", "write reg5");
    bus_check(f_addr(C_ADDR_REG5), 32x"00000055", "reg5 first read returns stored value");
    bus_check(f_addr(C_ADDR_REG5), 32x"000000F0", "reg5 second read reflects onread");

    log(ID_LOG_HDR, "reg1: hardware-driven status read back over the bus", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg1.field0.value <= 4x"5";
    from_hw.reg1.field0.we <= '1';
    from_hw.reg1.field1 <= '1';
    from_hw.reg1.field2.value <= '1';
    from_hw.reg1.field2.wel <= '0';
    wait until falling_edge(clk);
    from_hw.reg1.field0.we <= '0';
    from_hw.reg1.field2.wel <= '1';
    bus_check(f_addr(C_ADDR_REG1), 32x"00000035", "reg1 reflects hardware inputs");

    log(ID_LOG_HDR, "reg4: software baseline write", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG4), 32x"00000105", "write reg4");
    bus_check(f_addr(C_ADDR_REG4), 32x"00000105", "reg4 reads back the software value");
    check_value(to_hw.reg4.field0, 4x"5", error, "reg4.field0 exposed to hw", C_SCOPE);
    check_value(to_hw.reg4.field1, '1', error, "reg4.field1 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg4: hardware we overrides the stored value", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg4.field0.value <= 4x"A";
    from_hw.reg4.field0.we <= '1';
    wait until falling_edge(clk);
    from_hw.reg4.field0.we <= '0';
    bus_check(f_addr(C_ADDR_REG4), 32x"0000010A", "reg4 reflects the hardware we override");

    log(ID_LOG_HDR, "reg4: hwset drives fields high", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg4.field1.set <= '1';
    wait until falling_edge(clk);
    from_hw.reg4.field1.set <= '0';
    bus_check(f_addr(C_ADDR_REG4), 32x"0000010A", "reg4 reflects hwset");

    log(ID_LOG_HDR, "reg4: hwclr clears fields (and beats hwset)", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg4.field1.set <= '1';
    from_hw.reg4.field1.clr <= '1';
    wait until falling_edge(clk);
    from_hw.reg4.field1.set <= '0';
    from_hw.reg4.field1.clr <= '0';
    bus_check(f_addr(C_ADDR_REG4), 32x"0000000A", "reg4 reflects hwclr");

    log(ID_LOG_HDR, "reg9: software-access strobe pulses", C_SCOPE);
    v_reg9_field0_swmod := reg9_field0_swmod_count;
    v_reg9_field1_swacc := reg9_field1_swacc_count;
    bus_write(f_addr(C_ADDR_REG9), 32x"000000FF", "write reg9");
    bus_check(f_addr(C_ADDR_REG9), 32x"000000FF", "read reg9");
    wait until rising_edge(clk);
    wait until rising_edge(clk);
    check_value(reg9_field0_swmod_count - v_reg9_field0_swmod, 1, error, "reg9.field0 swmod pulses once per write", C_SCOPE);
    check_value(reg9_field1_swacc_count - v_reg9_field1_swacc, 2, error, "reg9.field1 swacc pulses per access (write + read)", C_SCOPE);

    log(ID_LOG_HDR, "reg10: software-access strobe pulses", C_SCOPE);
    v_reg10_field0_sp := reg10_field0_sp_count;
    bus_write(f_addr(C_ADDR_REG10), 32x"0000000F", "write reg10");
    wait until rising_edge(clk);
    wait until rising_edge(clk);
    check_value(reg10_field0_sp_count - v_reg10_field0_sp, 1, error, "reg10.field0 singlepulse lasts exactly one cycle", C_SCOPE);
    check_value(reg10_field0_sp_value, 4x"F", error, "reg10.field0 hw saw the pulse value", C_SCOPE);

    -- An address where no register sits gets an error response where the bus
    -- has one, reads as G_UNMAPPED_READ_DATA, and a write to it changes no register.
    log(ID_LOG_HDR, "addresses without a register get an error and change nothing", C_SCOPE);
    bus_write_unmapped(f_addr(32x"30"), 32x"0", "write 0x30, an unused register offset");
    bus_check_unmapped(f_addr(32x"30"), "read 0x30, an unused register offset");
    bus_write_unmapped(f_addr(32x"1"), 32x"0", "write 0x1, an address inside a register");
    bus_check_unmapped(f_addr(32x"1"), "read 0x1, an address inside a register");
    bus_write_unmapped(f_addr(32x"40"), 32x"0", "write 0x40, an address above the registers");
    bus_check_unmapped(f_addr(32x"40"), "read 0x40, an address above the registers");
    bus_write_unmapped(f_addr(32x"100"), 32x"0", "write 0x100, another base address");
    bus_check_unmapped(f_addr(32x"100"), "read 0x100, another base address");
    bus_check(f_addr(C_ADDR_REG0), 32x"00000007", "reg0 unchanged by the unmapped writes");

    wait for 10*C_CLK_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
