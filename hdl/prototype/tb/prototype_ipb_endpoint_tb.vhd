-- UVVM handshake-conformance testbench for prototype_ipb_endpoint.
-- Drives the IPBus interface with the stock vip_ipbus VIP and checks that the
-- wrapper bridges correctly to the local-bus regfile. The wrapper forwards the
-- address unchanged and the regfile slices the module window from it, so the VIP
-- drives the register byte offsets directly (zero base). Full access-mode
-- coverage lives in prototype_regfile_tb; this only proves the protocol translation.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library ipbus;
use ipbus.ipbus.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library vip_ipbus;
use vip_ipbus.ipbus_bfm_pkg.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_ipb_endpoint_tb is
end entity prototype_ipb_endpoint_tb;

architecture tb of prototype_ipb_endpoint_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  signal clk   : std_logic := '0';
  signal reset : std_logic := '0';   -- active-high; gen_pulse asserts it

  signal ipb_in  : ipb_wbus;
  signal ipb_out : ipb_rbus;

  signal to_hw   : t_prototype_to_hw;
  signal from_hw : t_prototype_from_hw := (
    reg1 => (field0 => (value => (others => '0'), we => '0'),
             field1 => '0',
             field2 => (value => '0', wel => '1')),
    reg4 => (field0 => (value => (others => '0'), we => '0'),
             field1 => (set => '0', clr => '0')));

  signal ipbus_if         : t_ipbus_if := init_ipbus_if_signals;
  signal ipbus_bfm_config : t_ipbus_bfm_config := C_IPBUS_BFM_CONFIG_DEFAULT;

  -- Register byte offset as the IPBus address (zero base); forwarded as-is.
  function f_addr(reg : std_logic_vector(31 downto 0)) return unsigned is
  begin
    return unsigned(reg);
  end function;

begin

  clock_generator(clk, C_CLK_PERIOD);

  ipb_in.ipb_wdata  <= ipbus_if.wdata;
  ipb_in.ipb_write  <= ipbus_if.wr;
  ipb_in.ipb_addr   <= ipbus_if.addr;
  ipb_in.ipb_strobe <= ipbus_if.strobe;
  ipbus_if.rdata    <= ipb_out.ipb_rdata;
  ipbus_if.ack      <= ipb_out.ipb_ack;
  ipbus_if.err      <= ipb_out.ipb_err;

  DUT : entity work.prototype_ipb_endpoint
    generic map (
      G_BASE_ADDRESS       => x"00000000",
      G_CHECK_BASE_ADDRESS => true)
    port map (
      clk     => clk,
      reset   => reset,
      ipb_in  => ipb_in,
      ipb_out => ipb_out,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_main : process is
    variable v_data : std_logic_vector(31 downto 0);

    procedure ipb_wr(constant addr : in unsigned;
                     constant data : in std_logic_vector;
                     constant msg  : in string) is
    begin
      ipbus_write(addr, data, msg, clk, ipbus_if, C_SCOPE,
                  shared_msg_id_panel, ipbus_bfm_config);
    end procedure;

    procedure ipb_rd_check(constant addr : in unsigned;
                           constant data : in std_logic_vector;
                           constant msg  : in string) is
    begin
      ipbus_read(addr, v_data, msg, clk, ipbus_if, C_SCOPE,
                 shared_msg_id_panel, ipbus_bfm_config);
      check_value(v_data, data, error, msg, C_SCOPE);
    end procedure;

  begin
    ipbus_bfm_config.clock_period    <= C_CLK_PERIOD;
    ipbus_bfm_config.max_wait_cycles <= 256;

    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);

    gen_pulse(reset, '1', 500 ns, BLOCKING, "Reset for 500 ns");

    log(ID_LOG_HDR, "reg0: sw rw write/read over IPBus", C_SCOPE);
    ipb_wr(f_addr(C_ADDR_REG0), 32x"5", "reg0 = field1=10, field0=1");
    ipb_rd_check(f_addr(C_ADDR_REG0), 32x"5", "reg0 reads back");
    check_value(to_hw.reg0.field0, '1', error, "reg0.field0 to hw", C_SCOPE);
    check_value(to_hw.reg0.field1, "10", error, "reg0.field1 to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg3: sw rw + hw na round-trip", C_SCOPE);
    ipb_wr(f_addr(C_ADDR_REG3), 32x"A5", "reg3 = 0xA5");
    ipb_rd_check(f_addr(C_ADDR_REG3), 32x"A5", "reg3 reads back");

    log(ID_LOG_HDR, "reg1: sw ro, hardware-driven, read over IPBus", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg1.field0.value <= "1011";
    from_hw.reg1.field0.we    <= '1';
    from_hw.reg1.field1       <= '1';
    from_hw.reg1.field2.value <= '1';
    from_hw.reg1.field2.wel   <= '0';
    wait until falling_edge(clk);
    from_hw.reg1.field0.we    <= '0';
    from_hw.reg1.field2.wel   <= '1';
    -- reg1 = field2(5)|field1(4)|field0(3:0) = 1|1|1011 = 0x3B
    ipb_rd_check(f_addr(C_ADDR_REG1), 32x"3B", "reg1 reflects hw over IPBus");

    log(ID_LOG_HDR, "reg11: enumerated field0 over IPBus", C_SCOPE);
    ipb_wr(f_addr(C_ADDR_REG11), 32x"2", "reg11.field0 = STATE2");
    ipb_rd_check(f_addr(C_ADDR_REG11), 32x"2", "reg11 reads back encoded value");
    check_value(to_hw.reg11.field0 = STATE2, error, "reg11.field0 is STATE2 to hw", C_SCOPE);

    wait for 10*C_CLK_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
