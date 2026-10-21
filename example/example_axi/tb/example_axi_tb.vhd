-- Generated UVVM testbench for the example_axi module (AXI4-Lite).
-- Drives the example_axi top entity with the stock Bitvis AXI-Lite VIP and
-- self-checks every register of the module, by kind: plain
-- read-write, enumerated, write-only/singlepulse (reads back 0), onread/onwrite
-- software side effects, software-readonly registers driven from from_hw
-- (we/wel), the hardware we override / hwset / hwclr modifiers, the to_hw values
-- the hardware sees, and the swmod/swacc/singlepulse to_hw strobe pulses (counted
-- by a monitor process, since they are single-cycle).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library bitvis_vip_axilite;
use bitvis_vip_axilite.axilite_bfm_pkg.all;

use work.example_axi_localbus_pkg.all;
use work.example_axi_regfile_pkg.all;

entity example_axi_tb is
end entity example_axi_tb;

architecture tb of example_axi_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  constant C_BASE : std_logic_vector(31 downto 0) := 32x"0";

  signal clk      : std_logic := '0';
  signal areset_n : std_logic := '1';

  -- What a read gets where no register sits (G_UNMAPPED_READ_DATA).
  constant C_UNMAPPED_READ_DATA : std_logic_vector(31 downto 0) := 32x"DEADBEEF";

  signal to_hw    : t_example_axi_to_hw;
  signal from_hw  : t_example_axi_from_hw := (
    reg2 => '0',
    reg4 => (others => '0'),
    reg6 => (others => '0'),
    reg8 => (field0 => '0', field1 => (others => '0'), field2 => '0', field3 => (others => '0')));

  constant C_DATA_W : natural := 32;
  constant C_ADDR_W : natural := 32;
  signal axilite_if : t_axilite_if(write_address_channel(awaddr(C_ADDR_W-1 downto 0)),
                                   write_data_channel(wdata(C_DATA_W-1 downto 0),
                                                      wstrb((C_DATA_W/8)-1 downto 0)),
                                   read_address_channel(araddr(C_ADDR_W-1 downto 0)),
                                   read_data_channel(rdata(C_DATA_W-1 downto 0)))
                      := init_axilite_if_signals(C_DATA_W, C_ADDR_W);
  signal axilite_bfm_config : t_axilite_bfm_config := C_AXILITE_BFM_CONFIG_DEFAULT;

  function f_addr(reg : std_logic_vector(31 downto 0)) return unsigned is
  begin
    return unsigned(C_BASE) + unsigned(reg);
  end function;

  -- Strobe monitors: count the cycles each swmod/swacc output is high and each
  -- singlepulse output differs from its reset value, so single-cycle pulses are
  -- verifiable without cycle-accurate sampling.
  signal reg9_reg9_sp_count : natural := 0;
  signal reg9_reg9_sp_value : std_logic := '1';
  signal reg10_reg10_sp_count : natural := 0;
  signal reg10_reg10_sp_value : std_logic_vector(3 downto 0) := 4X"A";
  signal reg11_field0_sp_count : natural := 0;
  signal reg11_field0_sp_value : std_logic_vector(14 downto 0) := 15X"3";
  signal reg11_field1_sp_count : natural := 0;
  signal reg11_field1_sp_value : std_logic := '0';

begin

  clock_generator(clk, C_CLK_PERIOD);

  DUT : entity work.example_axi_axi_endpoint
    generic map (
      G_BASE_ADDRESS       => unsigned(C_BASE),
      G_CHECK_BASE_ADDRESS => true,
      G_MODULE_ADDR_WIDTH  => 8,
      G_UNMAPPED_READ_DATA => C_UNMAPPED_READ_DATA)
    port map (
      clk      => clk,
      areset_n => areset_n,
      awaddr   => axilite_if.write_address_channel.awaddr,
      awvalid  => axilite_if.write_address_channel.awvalid,
      awready  => axilite_if.write_address_channel.awready,
      wdata    => axilite_if.write_data_channel.wdata,
      wvalid   => axilite_if.write_data_channel.wvalid,
      wready   => axilite_if.write_data_channel.wready,
      bresp    => axilite_if.write_response_channel.bresp,
      bvalid   => axilite_if.write_response_channel.bvalid,
      bready   => axilite_if.write_response_channel.bready,
      araddr   => axilite_if.read_address_channel.araddr,
      arvalid  => axilite_if.read_address_channel.arvalid,
      arready  => axilite_if.read_address_channel.arready,
      rdata    => axilite_if.read_data_channel.rdata,
      rresp    => axilite_if.read_data_channel.rresp,
      rvalid   => axilite_if.read_data_channel.rvalid,
      rready   => axilite_if.read_data_channel.rready,      to_hw    => to_hw,      from_hw  => from_hw);

  p_strobe_monitor : process (clk) is
  begin
    if rising_edge(clk) then
      if to_hw.reg9 /= '1' then
        reg9_reg9_sp_count <= reg9_reg9_sp_count + 1;
        reg9_reg9_sp_value <= to_hw.reg9;
      end if;
      if to_hw.reg10 /= 4x"A" then
        reg10_reg10_sp_count <= reg10_reg10_sp_count + 1;
        reg10_reg10_sp_value <= to_hw.reg10;
      end if;
      if to_hw.reg11.field0 /= 15x"0003" then
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
      axilite_write(addr, data, msg, clk, axilite_if, C_SCOPE,
                    shared_msg_id_panel, axilite_bfm_config);
    end procedure;

    procedure bus_check(constant addr : in unsigned;
                        constant data : in std_logic_vector;
                        constant msg  : in string) is
    begin
      axilite_check(addr, data, msg, clk, axilite_if, error, C_SCOPE,
                    shared_msg_id_panel, axilite_bfm_config);
    end procedure;

    -- An address without a register answers SLVERR and reads 0.
    procedure bus_write_unmapped(constant addr : in unsigned;
                                 constant data : in std_logic_vector;
                                 constant msg  : in string) is
      variable v_config : t_axilite_bfm_config := axilite_bfm_config;
    begin
      v_config.expected_response := SLVERR;
      axilite_write(addr, data, msg, clk, axilite_if, C_SCOPE,
                    shared_msg_id_panel, v_config);
    end procedure;

    procedure bus_check_unmapped(constant addr : in unsigned;
                                 constant msg  : in string) is
      variable v_config : t_axilite_bfm_config := axilite_bfm_config;
    begin
      v_config.expected_response := SLVERR;
      axilite_check(addr, C_UNMAPPED_READ_DATA, msg, clk, axilite_if, error, C_SCOPE,
                    shared_msg_id_panel, v_config);
    end procedure;
    variable v_reg9_reg9_sp : natural;
    variable v_reg10_reg10_sp : natural;
    variable v_reg11_field0_sp : natural;
    variable v_reg11_field1_sp : natural;

  begin
    axilite_bfm_config.clock_period <= C_CLK_PERIOD;

    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);

    gen_pulse(areset_n, '0', 500 ns, BLOCKING, "Reset for 500 ns");

    log(ID_LOG_HDR, "reg0: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG0), 32x"00000001", "write reg0");
    bus_check(f_addr(C_ADDR_REG0), 32x"00000001", "reg0 reads back");
    check_value(to_hw.reg0, '1', error, "reg0.reg0 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg1: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG1), 32x"00000001", "write reg1");
    bus_check(f_addr(C_ADDR_REG1), 32x"00000001", "reg1 reads back");
    check_value(to_hw.reg1, '1', error, "reg1.reg1 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg3: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG3), 32x"000000FF", "write reg3");
    bus_check(f_addr(C_ADDR_REG3), 32x"000000FF", "reg3 reads back");
    check_value(to_hw.reg3, 8x"FF", error, "reg3.reg3 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg5: software read-write round-trip", C_SCOPE);
    bus_write(f_addr(C_ADDR_REG5), 32x"FFFFFFFF", "write reg5");
    bus_check(f_addr(C_ADDR_REG5), 32x"FFFFFFFF", "reg5 reads back");
    check_value(to_hw.reg5, 32x"FFFFFFFF", error, "reg5.reg5 exposed to hw", C_SCOPE);

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
    from_hw.reg2 <= '1';
    wait until falling_edge(clk);
    bus_check(f_addr(C_ADDR_REG2), 32x"00000001", "reg2 reflects hardware inputs");

    log(ID_LOG_HDR, "reg4: hardware-driven status read back over the bus", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg4 <= 14x"1555";
    wait until falling_edge(clk);
    bus_check(f_addr(C_ADDR_REG4), 32x"00001555", "reg4 reflects hardware inputs");

    log(ID_LOG_HDR, "reg6: hardware-driven status read back over the bus", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg6 <= 32x"55555555";
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
    bus_write(f_addr(C_ADDR_REG9), 32x"00000000", "write reg9");
    wait until rising_edge(clk);
    wait until rising_edge(clk);
    check_value(reg9_reg9_sp_count - v_reg9_reg9_sp, 1, error, "reg9.reg9 singlepulse lasts exactly one cycle", C_SCOPE);
    check_value(reg9_reg9_sp_value, '0', error, "reg9.reg9 hw saw the pulse value", C_SCOPE);

    log(ID_LOG_HDR, "reg10: software-access strobe pulses", C_SCOPE);
    v_reg10_reg10_sp := reg10_reg10_sp_count;
    bus_write(f_addr(C_ADDR_REG10), 32x"00000005", "write reg10");
    wait until rising_edge(clk);
    wait until rising_edge(clk);
    check_value(reg10_reg10_sp_count - v_reg10_reg10_sp, 1, error, "reg10.reg10 singlepulse lasts exactly one cycle", C_SCOPE);
    check_value(reg10_reg10_sp_value, 4x"5", error, "reg10.reg10 hw saw the pulse value", C_SCOPE);

    log(ID_LOG_HDR, "reg11: software-access strobe pulses", C_SCOPE);
    v_reg11_field0_sp := reg11_field0_sp_count;
    v_reg11_field1_sp := reg11_field1_sp_count;
    bus_write(f_addr(C_ADDR_REG11), 32x"0000FFFC", "write reg11");
    wait until rising_edge(clk);
    wait until rising_edge(clk);
    check_value(reg11_field0_sp_count - v_reg11_field0_sp, 1, error, "reg11.field0 singlepulse lasts exactly one cycle", C_SCOPE);
    check_value(reg11_field0_sp_value, 15x"7FFC", error, "reg11.field0 hw saw the pulse value", C_SCOPE);
    check_value(reg11_field1_sp_count - v_reg11_field1_sp, 1, error, "reg11.field1 singlepulse lasts exactly one cycle", C_SCOPE);
    check_value(reg11_field1_sp_value, '1', error, "reg11.field1 hw saw the pulse value", C_SCOPE);

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
    bus_check(f_addr(C_ADDR_REG0), 32x"00000001", "reg0 unchanged by the unmapped writes");

    wait for 10*C_CLK_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
