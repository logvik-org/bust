-- UVVM handshake-conformance testbench for prototype_sbi_endpoint.
-- Drives the SBI interface with the stock Bitvis SBI VIP and checks that the
-- wrapper bridges correctly to the local-bus regfile (writes, reads,
-- hardware-driven readback, and an enumerated field). The master drives byte
-- addresses, so a non-zero base exercises G_CHECK_BASE_ADDRESS. Full access-mode
-- coverage lives in prototype_regfile_tb; this only proves the protocol
-- translation.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library bitvis_vip_sbi;
use bitvis_vip_sbi.sbi_bfm_pkg.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_sbi_endpoint_tb is
end entity prototype_sbi_endpoint_tb;

architecture tb of prototype_sbi_endpoint_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  -- 64-byte aligned base (low C_MODULE_ADDR_WIDTH bits zero) so in_window holds.
  constant C_BASE : std_logic_vector(31 downto 0) := 32x"FFAA0000";

  signal clk   : std_logic := '0';
  signal reset : std_logic := '0';   -- active-high; gen_pulse asserts it

  signal to_hw   : t_prototype_to_hw;
  signal from_hw : t_prototype_from_hw := (
    reg1 => (field0 => (value => (others => '0'), we => '0'),
             field1 => '0',
             field2 => (value => '0', wel => '1')),
    reg4 => (field0 => (value => (others => '0'), we => '0'),
             field1 => (set => '0', clr => '0')));

  constant C_DATA_W : natural := 32;
  constant C_ADDR_W : natural := 32;
  signal sbi_if : t_sbi_if(addr(C_ADDR_W-1 downto 0),
                           wdata(C_DATA_W-1 downto 0),
                           rdata(C_DATA_W-1 downto 0))
                  := init_sbi_if_signals(C_ADDR_W, C_DATA_W);
  signal sbi_bfm_config : t_sbi_bfm_config := C_SBI_BFM_CONFIG_DEFAULT;

  function f_addr(base : std_logic_vector(31 downto 0);
                  reg  : std_logic_vector(31 downto 0)) return unsigned is
  begin
    return unsigned(base) + unsigned(reg);
  end function;

begin

  clock_generator(clk, C_CLK_PERIOD);

  DUT : entity work.prototype_sbi_endpoint
    generic map (
      G_BASE_ADDRESS       => unsigned(C_BASE),
      G_CHECK_BASE_ADDRESS => true)
    port map (
      clk     => clk,
      reset   => reset,
      cs      => sbi_if.cs,
      addr    => std_logic_vector(sbi_if.addr),
      rena    => sbi_if.rena,
      wena    => sbi_if.wena,
      wdata   => sbi_if.wdata,
      ready   => sbi_if.ready,
      rdata   => sbi_if.rdata,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_main : process is

    procedure sbi_wr(constant addr : in unsigned;
                     constant data : in std_logic_vector;
                     constant msg  : in string) is
    begin
      sbi_write(addr, data, msg, clk, sbi_if, C_SCOPE,
                shared_msg_id_panel, sbi_bfm_config);
    end procedure;

    procedure sbi_ck(constant addr : in unsigned;
                     constant data : in std_logic_vector;
                     constant msg  : in string) is
    begin
      sbi_check(addr, data, msg, clk, sbi_if, error, C_SCOPE,
                shared_msg_id_panel, sbi_bfm_config);
    end procedure;

  begin
    sbi_bfm_config.clock_period <= C_CLK_PERIOD;

    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);

    gen_pulse(reset, '1', 500 ns, BLOCKING, "Reset for 500 ns");

    log(ID_LOG_HDR, "reg0: sw rw write/read over SBI", C_SCOPE);
    sbi_wr(f_addr(C_BASE, C_ADDR_REG0), 32x"5", "reg0 = field1=10, field0=1");
    sbi_ck(f_addr(C_BASE, C_ADDR_REG0), 32x"5", "reg0 reads back");
    check_value(to_hw.reg0.field0, '1', error, "reg0.field0 to hw", C_SCOPE);
    check_value(to_hw.reg0.field1, "10", error, "reg0.field1 to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg3: sw rw + hw na round-trip", C_SCOPE);
    sbi_wr(f_addr(C_BASE, C_ADDR_REG3), 32x"A5", "reg3 = 0xA5");
    sbi_ck(f_addr(C_BASE, C_ADDR_REG3), 32x"A5", "reg3 reads back");

    log(ID_LOG_HDR, "reg1: sw ro, hardware-driven, read over SBI", C_SCOPE);
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
    sbi_ck(f_addr(C_BASE, C_ADDR_REG1), 32x"3B", "reg1 reflects hw over SBI");

    log(ID_LOG_HDR, "reg11: enumerated field0 over SBI", C_SCOPE);
    sbi_wr(f_addr(C_BASE, C_ADDR_REG11), 32x"2", "reg11.field0 = STATE2");
    sbi_ck(f_addr(C_BASE, C_ADDR_REG11), 32x"2", "reg11 reads back encoded value");
    check_value(to_hw.reg11.field0 = STATE2, error, "reg11.field0 is STATE2 to hw", C_SCOPE);

    -- A decode error has no SBI error line: the wrapper still completes the
    -- ready handshake and returns a deterministic 0 (regfile err -> rdata 0).
    log(ID_LOG_HDR, "decode error: out-of-base read completes with rdata 0", C_SCOPE);
    sbi_ck(x"00000000", 32x"0", "invalid-address read completes and reads 0");

    wait for 10*C_CLK_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
