-- Generated UVVM testbench for the example_ipbus module (IPBus).
-- Drives the example_ipbus top entity with the stock vip_ipbus VIP and
-- self-checks every register whose behaviour the prototype exercises: plain
-- read-write, enumerated, write-only/singlepulse (reads back 0), onread/onwrite
-- software side effects, software-readonly registers driven from from_hw
-- (we/wel), the hardware we override / hwset / hwclr modifiers, the to_hw values
-- the hardware sees, and the swmod/swacc/singlepulse to_hw strobe pulses (counted
-- by a monitor process, since they are single-cycle).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library ipbus;
use ipbus.ipbus.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library vip_ipbus;
use vip_ipbus.ipbus_bfm_pkg.all;

use work.example_ipbus_localbus_pkg.all;
use work.example_ipbus_regfile_pkg.all;

entity example_ipbus_tb is
end entity example_ipbus_tb;

architecture tb of example_ipbus_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  constant C_BASE : std_logic_vector(31 downto 0) := 32x"0";

  signal clk     : std_logic := '0';
  signal reset   : std_logic := '0';
  signal ipb_in  : ipb_wbus;
  signal ipb_out : ipb_rbus;

  signal to_hw    : t_example_ipbus_to_hw;
  signal from_hw  : t_example_ipbus_from_hw := (
    reg2 => (reg2 => '0'),
    reg4 => (reg4 => (others => '0')),
    reg6 => (reg6 => (others => '0')),
    reg8 => (field0 => '0', field1 => (others => '0'), field2 => '0', field3 => (others => '0')));

  constant C_DATA_W : natural := 32;
  signal ipbus_if         : t_ipbus_if := init_ipbus_if_signals;
  signal ipbus_bfm_config : t_ipbus_bfm_config := C_IPBUS_BFM_CONFIG_DEFAULT;

  function f_addr(reg : std_logic_vector(31 downto 0)) return unsigned is
  begin
    return unsigned(C_BASE) + unsigned(reg);
  end function;

  -- Strobe monitors: count the cycles each swmod/swacc/singlepulse output is
  -- high, so single-cycle pulses are verifiable without cycle-accurate sampling.
  signal reg9_reg9_sp_count : natural := 0;
  signal reg9_reg9_sp_value : std_logic := '0';
  signal reg10_reg10_sp_count : natural := 0;
  signal reg10_reg10_sp_value : std_logic_vector(3 downto 0) := (others => '0');
  signal reg11_field0_sp_count : natural := 0;
  signal reg11_field0_sp_value : std_logic_vector(14 downto 0) := (others => '0');
  signal reg11_field1_sp_count : natural := 0;
  signal reg11_field1_sp_value : std_logic := '0';

begin

  clock_generator(clk, C_CLK_PERIOD);

  ipb_in.ipb_wdata  <= ipbus_if.wdata;
  ipb_in.ipb_write  <= ipbus_if.wr;
  ipb_in.ipb_addr   <= ipbus_if.addr;
  ipb_in.ipb_strobe <= ipbus_if.strobe;
  ipbus_if.rdata    <= ipb_out.ipb_rdata;
  ipbus_if.ack      <= ipb_out.ipb_ack;
  ipbus_if.err      <= ipb_out.ipb_err;

  DUT : entity work.example_ipbus
    generic map (
      G_BASE_ADDRESS       => unsigned(C_BASE),
      G_CHECK_BASE_ADDRESS => true)
    port map (
      clk     => clk,
      reset   => reset,
      ipb_in  => ipb_in,
      ipb_out => ipb_out,      to_hw   => to_hw,      from_hw => from_hw);

  p_strobe_monitor : process (clk) is
  begin
    if rising_edge(clk) then
      if to_hw.reg9.reg9 /= '0' then
        reg9_reg9_sp_count <= reg9_reg9_sp_count + 1;
        reg9_reg9_sp_value <= to_hw.reg9.reg9;
      end if;
      if to_hw.reg10.reg10 /= 4x"0" then
        reg10_reg10_sp_count <= reg10_reg10_sp_count + 1;
        reg10_reg10_sp_value <= to_hw.reg10.reg10;
      end if;
      if to_hw.reg11.field0 /= 15x"0000" then
        reg11_field0_sp_count <= reg11_field0_sp_count + 1;
        reg11_field0_sp_value <= to_hw.reg11.field0;
      end if;
      if to_hw.reg11.field1 /= '0' then
        reg11_field1_sp_count <= reg11_field1_sp_count + 1;
        reg11_field1_sp_value <= to_hw.reg11.field1;
      end if;
    end if;
  end process p_strobe_monitor;

  p_main : process is

    procedure bus_write(constant addr : in unsigned;
                        constant data : in std_logic_vector;
                        constant msg  : in string) is
    begin
      ipbus_write(addr, data, msg, clk, ipbus_if, C_SCOPE,
                  shared_msg_id_panel, ipbus_bfm_config);
    end procedure;

    procedure bus_check(constant addr : in unsigned;
                        constant data : in std_logic_vector;
                        constant msg  : in string) is
      variable v_data : std_logic_vector(C_DATA_W-1 downto 0);
    begin
      ipbus_read(addr, v_data, msg, clk, ipbus_if, C_SCOPE,
                 shared_msg_id_panel, ipbus_bfm_config);
      check_value(v_data, data, error, msg, C_SCOPE);
    end procedure;
    variable v_reg9_reg9_sp : natural;
    variable v_reg10_reg10_sp : natural;
    variable v_reg11_field0_sp : natural;
    variable v_reg11_field1_sp : natural;

  begin
    ipbus_bfm_config.clock_period    <= C_CLK_PERIOD;
    ipbus_bfm_config.max_wait_cycles <= 256;

    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);

    gen_pulse(reset, '1', 500 ns, BLOCKING, "Reset for 500 ns");

    log(ID_LOG_HDR, "reg0: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG0), 32x"00000001", "write reg0");
    bus_check(f_addr(C_ADDR_REG0), 32x"00000001", "reg0 reads back");
    check_value(to_hw.reg0.reg0, '1', error, "reg0.reg0 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg1: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG1), 32x"00000001", "write reg1");
    bus_check(f_addr(C_ADDR_REG1), 32x"00000001", "reg1 reads back");
    check_value(to_hw.reg1.reg1, '1', error, "reg1.reg1 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg3: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG3), 32x"000000FF", "write reg3");
    bus_check(f_addr(C_ADDR_REG3), 32x"000000FF", "reg3 reads back");
    check_value(to_hw.reg3.reg3, 8x"FF", error, "reg3.reg3 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg5: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG5), 32x"FFFFFFFF", "write reg5");
    bus_check(f_addr(C_ADDR_REG5), 32x"FFFFFFFF", "reg5 reads back");
    check_value(to_hw.reg5.reg5, 32x"FFFFFFFF", error, "reg5.reg5 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg7: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG7), 32x"001FFFFF", "write reg7");
    bus_check(f_addr(C_ADDR_REG7), 32x"001FFFFF", "reg7 reads back");
    check_value(to_hw.reg7.field0, '1', error, "reg7.field0 exposed to hw", C_SCOPE);
    check_value(to_hw.reg7.field1, 4x"F", error, "reg7.field1 exposed to hw", C_SCOPE);
    check_value(to_hw.reg7.field2, '1', error, "reg7.field2 exposed to hw", C_SCOPE);
    check_value(to_hw.reg7.field3, 15x"7FFF", error, "reg7.field3 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg9: write-only / pulse reads back zero", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG9), 32x"00000001", "write reg9");
    bus_check(f_addr(C_ADDR_REG9), 32x"0", "reg9 reads back zero");

    log(ID_LOG_HDR, "reg10: write-only / pulse reads back zero", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG10), 32x"0000000F", "write reg10");
    bus_check(f_addr(C_ADDR_REG10), 32x"0", "reg10 reads back zero");

    log(ID_LOG_HDR, "reg11: write-only / pulse reads back zero", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG11), 32x"0000FFFF", "write reg11");
    bus_check(f_addr(C_ADDR_REG11), 32x"0", "reg11 reads back zero");

    log(ID_LOG_HDR, "reg2: hardware-driven status read back over the bus", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg2.reg2 <= '1';
    wait until falling_edge(clk);
    bus_check(f_addr(C_ADDR_REG2), 32x"00000001", "reg2 reflects hardware inputs");

    log(ID_LOG_HDR, "reg4: hardware-driven status read back over the bus", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg4.reg4 <= 14x"1555";
    wait until falling_edge(clk);
    bus_check(f_addr(C_ADDR_REG4), 32x"00001555", "reg4 reflects hardware inputs");

    log(ID_LOG_HDR, "reg6: hardware-driven status read back over the bus", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg6.reg6 <= 32x"55555555";
    wait until falling_edge(clk);
    bus_check(f_addr(C_ADDR_REG6), 32x"55555555", "reg6 reflects hardware inputs");

    log(ID_LOG_HDR, "reg8: hardware-driven status read back over the bus", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg8.field0 <= '1';
    from_hw.reg8.field1 <= 19x"55555";
    from_hw.reg8.field2 <= '1';
    from_hw.reg8.field3 <= 3x"5";
    wait until falling_edge(clk);
    bus_check(f_addr(C_ADDR_REG8), 32x"00BAAAAB", "reg8 reflects hardware inputs");

    log(ID_LOG_HDR, "reg9: software-access strobe pulses", C_SCOPE);
    v_reg9_reg9_sp := reg9_reg9_sp_count;
    bus_write(f_addr(C_ADDR_REG9), 32x"00000001", "write reg9");
    wait until rising_edge(clk);
    wait until rising_edge(clk);
    check_value(reg9_reg9_sp_count - v_reg9_reg9_sp, 1, error, "reg9.reg9 singlepulse high exactly one cycle", C_SCOPE);
    check_value(reg9_reg9_sp_value, '1', error, "reg9.reg9 hw saw the pulse value", C_SCOPE);

    log(ID_LOG_HDR, "reg10: software-access strobe pulses", C_SCOPE);
    v_reg10_reg10_sp := reg10_reg10_sp_count;
    bus_write(f_addr(C_ADDR_REG10), 32x"0000000F", "write reg10");
    wait until rising_edge(clk);
    wait until rising_edge(clk);
    check_value(reg10_reg10_sp_count - v_reg10_reg10_sp, 1, error, "reg10.reg10 singlepulse high exactly one cycle", C_SCOPE);
    check_value(reg10_reg10_sp_value, 4x"F", error, "reg10.reg10 hw saw the pulse value", C_SCOPE);

    log(ID_LOG_HDR, "reg11: software-access strobe pulses", C_SCOPE);
    v_reg11_field0_sp := reg11_field0_sp_count;
    v_reg11_field1_sp := reg11_field1_sp_count;
    bus_write(f_addr(C_ADDR_REG11), 32x"0000FFFF", "write reg11");
    wait until rising_edge(clk);
    wait until rising_edge(clk);
    check_value(reg11_field0_sp_count - v_reg11_field0_sp, 1, error, "reg11.field0 singlepulse high exactly one cycle", C_SCOPE);
    check_value(reg11_field0_sp_value, 15x"7FFF", error, "reg11.field0 hw saw the pulse value", C_SCOPE);
    check_value(reg11_field1_sp_count - v_reg11_field1_sp, 1, error, "reg11.field1 singlepulse high exactly one cycle", C_SCOPE);
    check_value(reg11_field1_sp_value, '1', error, "reg11.field1 hw saw the pulse value", C_SCOPE);

    wait for 10*C_CLK_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
