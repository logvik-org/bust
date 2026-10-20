-- UVVM handshake-conformance testbench for prototype_avalon_endpoint.
-- Drives the Avalon-MM interface with the stock Bitvis Avalon-MM VIP and checks
-- that the wrapper bridges correctly to the local-bus regfile (writes, reads,
-- hardware-driven readback, and an enumerated field). The master drives byte
-- addresses, so a non-zero base exercises G_CHECK_BASE_ADDRESS. The endpoint does
-- not implement the optional Avalon-MM response signal (decode errors complete as
-- a normal beat with readdata 0, as on SBI), so use_response_signal is off. Full
-- access-mode coverage lives in prototype_regfile_tb; this only proves the
-- protocol translation.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library bitvis_vip_avalon_mm;
use bitvis_vip_avalon_mm.avalon_mm_bfm_pkg.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_avalon_endpoint_tb is
end entity prototype_avalon_endpoint_tb;

architecture tb of prototype_avalon_endpoint_tb is

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
  signal avmm_if : t_avalon_mm_if(address(C_ADDR_W-1 downto 0),
                                  byte_enable((C_DATA_W/8)-1 downto 0),
                                  writedata(C_DATA_W-1 downto 0),
                                  readdata(C_DATA_W-1 downto 0))
                   := init_avalon_mm_if_signals(C_ADDR_W, C_DATA_W);
  signal avmm_bfm_config : t_avalon_mm_bfm_config := C_AVALON_MM_BFM_CONFIG_DEFAULT;

  function f_addr(base : std_logic_vector(31 downto 0);
                  reg  : std_logic_vector(31 downto 0)) return unsigned is
  begin
    return unsigned(base) + unsigned(reg);
  end function;

begin

  clock_generator(clk, C_CLK_PERIOD);

  DUT : entity work.prototype_avalon_endpoint
    generic map (
      G_BASE_ADDRESS       => unsigned(C_BASE),
      G_CHECK_BASE_ADDRESS => true)
    port map (
      clk         => clk,
      reset       => reset,
      chipselect  => avmm_if.chipselect,
      address     => avmm_if.address,
      read        => avmm_if.read,
      write       => avmm_if.write,
      writedata   => avmm_if.writedata,
      waitrequest => avmm_if.waitrequest,
      readdata    => avmm_if.readdata,
      to_hw       => to_hw,
      from_hw     => from_hw);

  p_main : process is

    procedure av_wr(constant addr : in unsigned;
                    constant data : in std_logic_vector;
                    constant msg  : in string) is
    begin
      avalon_mm_write(addr, data, msg, clk, avmm_if, C_SCOPE,
                      shared_msg_id_panel, avmm_bfm_config);
    end procedure;

    procedure av_ck(constant addr : in unsigned;
                    constant data : in std_logic_vector;
                    constant msg  : in string) is
    begin
      avalon_mm_check(addr, data, msg, clk, avmm_if, error, C_SCOPE,
                      shared_msg_id_panel, avmm_bfm_config);
    end procedure;

  begin
    avmm_bfm_config.clock_period        <= C_CLK_PERIOD;
    avmm_bfm_config.use_response_signal <= false;
    avmm_bfm_config.use_begintransfer   <= false;

    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);

    gen_pulse(reset, '1', 500 ns, BLOCKING, "Reset for 500 ns");

    log(ID_LOG_HDR, "reg0: sw rw write/read over Avalon-MM", C_SCOPE);
    av_wr(f_addr(C_BASE, C_ADDR_REG0), 32x"5", "reg0 = field1=10, field0=1");
    av_ck(f_addr(C_BASE, C_ADDR_REG0), 32x"5", "reg0 reads back");
    check_value(to_hw.reg0.field0, '1', error, "reg0.field0 to hw", C_SCOPE);
    check_value(to_hw.reg0.field1, "10", error, "reg0.field1 to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg3: sw rw + hw na round-trip", C_SCOPE);
    av_wr(f_addr(C_BASE, C_ADDR_REG3), 32x"A5", "reg3 = 0xA5");
    av_ck(f_addr(C_BASE, C_ADDR_REG3), 32x"A5", "reg3 reads back");

    log(ID_LOG_HDR, "reg1: sw ro, hardware-driven, read over Avalon-MM", C_SCOPE);
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
    av_ck(f_addr(C_BASE, C_ADDR_REG1), 32x"3B", "reg1 reflects hw over Avalon-MM");

    log(ID_LOG_HDR, "reg11: enumerated field0 over Avalon-MM", C_SCOPE);
    av_wr(f_addr(C_BASE, C_ADDR_REG11), 32x"2", "reg11.field0 = STATE2");
    av_ck(f_addr(C_BASE, C_ADDR_REG11), 32x"2", "reg11 reads back encoded value");
    check_value(to_hw.reg11.field0 = STATE2, error, "reg11.field0 is STATE2 to hw", C_SCOPE);

    -- A decode error completes as a normal beat with deterministic 0 readdata
    -- (regfile err -> readdata 0; the optional Avalon-MM response is not used).
    log(ID_LOG_HDR, "decode error: out-of-base read completes with readdata 0", C_SCOPE);
    av_ck(x"00000000", 32x"0", "invalid-address read completes and reads 0");

    wait for 10*C_CLK_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
