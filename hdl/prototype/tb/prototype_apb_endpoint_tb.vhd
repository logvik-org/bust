-- Conformance testbench for prototype_apb_endpoint. UVVM ships no APB VIP, so
-- this drives the bus with a small hand-written APB master BFM (two-phase
-- SETUP/ACCESS procedures below) and uses uvvm_util only for logging and checks.
-- It proves the wrapper bridges correctly to the local-bus regfile (writes,
-- reads, hardware-driven readback, the enumerated field, and a decode error that
-- maps to pslverr). The master drives byte addresses, so a non-zero base
-- exercises G_CHECK_BASE_ADDRESS. Full access-mode coverage lives in
-- prototype_regfile_tb; this only proves the protocol translation.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_apb_endpoint_tb is
end entity prototype_apb_endpoint_tb;

architecture tb of prototype_apb_endpoint_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  -- 64-byte aligned base (low C_MODULE_ADDR_WIDTH bits zero) so base_match holds.
  constant C_BASE : std_logic_vector(31 downto 0) := 32x"FFAA0000";

  signal pclk    : std_logic := '0';
  signal presetn : std_logic := '1';   -- active-low; gen_pulse drives it low

  signal psel    : std_logic := '0';
  signal penable : std_logic := '0';
  signal pwrite  : std_logic := '0';
  signal paddr   : std_logic_vector(31 downto 0) := (others => '0');
  signal pwdata  : std_logic_vector(31 downto 0) := (others => '0');
  signal prdata  : std_logic_vector(31 downto 0);
  signal pready  : std_logic;
  signal pslverr : std_logic;

  signal to_hw   : t_prototype_to_hw;
  signal from_hw : t_prototype_from_hw := (
    reg1 => (field0 => (value => (others => '0'), we => '0'),
             field1 => '0',
             field2 => (value => '0', wel => '1')),
    reg4 => (field0 => (value => (others => '0'), we => '0'),
             field1 => (set => '0', clr => '0')));

  function f_addr(base : std_logic_vector(31 downto 0);
                  reg  : std_logic_vector(31 downto 0)) return std_logic_vector is
  begin
    return std_logic_vector(unsigned(base) + unsigned(reg));
  end function;

begin

  clock_generator(pclk, C_CLK_PERIOD);

  DUT : entity work.prototype_apb_endpoint
    generic map (
      G_BASE_ADDRESS       => unsigned(C_BASE),
      G_CHECK_BASE_ADDRESS => true)
    port map (
      pclk    => pclk,
      presetn => presetn,
      psel    => psel,
      penable => penable,
      pwrite  => pwrite,
      paddr   => paddr,
      pwdata  => pwdata,
      prdata  => prdata,
      pready  => pready,
      pslverr => pslverr,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_main : process is

    -- APB single write: SETUP (psel, penable low), then ACCESS (penable high)
    -- held until pready.
    procedure apb_write(constant addr : in std_logic_vector;
                        constant data : in std_logic_vector) is
    begin
      psel    <= '1';
      penable <= '0';
      pwrite  <= '1';
      paddr   <= addr;
      pwdata  <= data;
      wait until rising_edge(pclk);
      penable <= '1';
      wait until rising_edge(pclk);
      while pready = '0' loop
        wait until rising_edge(pclk);
      end loop;
      psel    <= '0';
      penable <= '0';
      pwrite  <= '0';
      wait for 0 ns;
    end procedure;

    -- APB single read: returns the read data and whether pslverr was asserted.
    procedure apb_read(constant addr : in std_logic_vector;
                       variable data : out std_logic_vector(31 downto 0);
                       variable got_err : out boolean) is
    begin
      psel    <= '1';
      penable <= '0';
      pwrite  <= '0';
      paddr   <= addr;
      wait until rising_edge(pclk);
      penable <= '1';
      wait until rising_edge(pclk);
      while pready = '0' loop
        wait until rising_edge(pclk);
      end loop;
      data    := prdata;
      got_err := pslverr = '1';
      psel    <= '0';
      penable <= '0';
      wait for 0 ns;
    end procedure;

    procedure apb_check(constant addr : in std_logic_vector;
                        constant exp  : in std_logic_vector;
                        constant msg  : in string) is
      variable data    : std_logic_vector(31 downto 0);
      variable got_err : boolean;
    begin
      apb_read(addr, data, got_err);
      check_value(got_err, false, error, msg & " (no pslverr)", C_SCOPE);
      check_value(data, exp, error, msg, C_SCOPE);
    end procedure;

    variable v_rdata : std_logic_vector(31 downto 0);
    variable v_err   : boolean;

  begin
    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);

    gen_pulse(presetn, '0', 500 ns, BLOCKING, "Reset for 500 ns");

    log(ID_LOG_HDR, "reg0: sw rw write/read over APB", C_SCOPE);
    apb_write(f_addr(C_BASE, C_ADDR_REG0), 32x"5");
    apb_check(f_addr(C_BASE, C_ADDR_REG0), 32x"5", "reg0 reads back");
    check_value(to_hw.reg0.field0, '1', error, "reg0.field0 to hw", C_SCOPE);
    check_value(to_hw.reg0.field1, "10", error, "reg0.field1 to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg3: sw rw + hw na round-trip", C_SCOPE);
    apb_write(f_addr(C_BASE, C_ADDR_REG3), 32x"A5");
    apb_check(f_addr(C_BASE, C_ADDR_REG3), 32x"A5", "reg3 reads back");

    log(ID_LOG_HDR, "reg1: sw ro, hardware-driven, read over APB", C_SCOPE);
    wait until falling_edge(pclk);
    from_hw.reg1.field0.value <= "1011";
    from_hw.reg1.field0.we    <= '1';
    from_hw.reg1.field1       <= '1';
    from_hw.reg1.field2.value <= '1';
    from_hw.reg1.field2.wel   <= '0';
    wait until falling_edge(pclk);
    from_hw.reg1.field0.we    <= '0';
    from_hw.reg1.field2.wel   <= '1';
    -- reg1 = field2(5)|field1(4)|field0(3:0) = 1|1|1011 = 0x3B
    apb_check(f_addr(C_BASE, C_ADDR_REG1), 32x"3B", "reg1 reflects hw over APB");

    log(ID_LOG_HDR, "reg11: enumerated field0 over APB", C_SCOPE);
    apb_write(f_addr(C_BASE, C_ADDR_REG11), 32x"2");
    apb_check(f_addr(C_BASE, C_ADDR_REG11), 32x"2", "reg11 reads back encoded value");
    check_value(to_hw.reg11.field0 = STATE2, error, "reg11.field0 is STATE2 to hw", C_SCOPE);

    log(ID_LOG_HDR, "decode error: out-of-base read raises pslverr", C_SCOPE);
    apb_read(x"00000000", v_rdata, v_err);
    check_value(v_err, true, error, "invalid-address read raises pslverr", C_SCOPE);
    check_value(v_rdata, 32x"0", error, "invalid-address read returns 0", C_SCOPE);

    wait for 10*C_CLK_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
