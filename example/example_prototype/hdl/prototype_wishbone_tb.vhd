-- Generated testbench for the prototype module (Wishbone B4 classic).
-- This drives the prototype top entity with an inlined hand-written
-- classic-cycle Wishbone master BFM (the bus_write/bus_read
-- procedures below) and uses uvvm_util only for logging and checks. It self-checks
-- every register of the module, by kind: plain read-write,
-- enumerated, write-only/singlepulse (reads back 0), onread/onwrite software side
-- effects, software-readonly registers driven from from_hw (we/wel), the hardware
-- we override / hwset / hwclr modifiers, the to_hw values the hardware sees, and the
-- swmod/swacc/singlepulse to_hw strobe pulses (counted by a monitor process, since
-- they are single-cycle).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

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

  signal to_hw    : t_prototype_to_hw;
  signal from_hw  : t_prototype_from_hw := (
    reg1 => (field0 => (value => (others => '0'), we => '0'), field1 => '0', field2 => (value => '0', wel => '1')),
    reg4 => (field0 => (value => (others => '0'), we => '0'), field1 => (set => '0', clr => '0')));

  signal wb_cyc   : std_logic := '0';
  signal wb_stb   : std_logic := '0';
  signal wb_we    : std_logic := '0';
  signal wb_adr   : std_logic_vector(31 downto 0) := (others => '0');
  signal wb_dat_w : std_logic_vector(31 downto 0) := (others => '0');
  signal wb_dat_r : std_logic_vector(31 downto 0);
  signal wb_ack   : std_logic;
  signal wb_err   : std_logic;

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

  DUT : entity work.prototype
    generic map (
      G_BASE_ADDRESS       => unsigned(C_BASE),
      G_CHECK_BASE_ADDRESS => true,
      G_MODULE_ADDR_WIDTH  => 8)
    port map (
      clk_i   => clk,
      rst_i   => reset,
      cyc_i   => wb_cyc,
      stb_i   => wb_stb,
      we_i    => wb_we,
      adr_i   => wb_adr,
      dat_i   => wb_dat_w,
      dat_o   => wb_dat_r,
      ack_o   => wb_ack,
      err_o   => wb_err,      to_hw   => to_hw,      from_hw => from_hw);

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

    -- Classic Wishbone single write: assert cyc/stb/we, hold until ack/err.
    procedure bus_write(constant addr       : in unsigned;
                        constant data       : in std_logic_vector;
                        constant msg        : in string;
                        constant expect_err : in boolean := false) is
    begin
      wb_cyc   <= '1';
      wb_stb   <= '1';
      wb_we    <= '1';
      wb_adr   <= std_logic_vector(addr);
      wb_dat_w <= data;
      wait until rising_edge(clk);
      while wb_ack = '0' and wb_err = '0' loop
        wait until rising_edge(clk);
      end loop;
      if expect_err then
        check_value(wb_err, '1', error, "write must terminate on err: " & msg, C_SCOPE);
      else
        check_value(wb_err, '0', error, "write must terminate on ack, not err: " & msg, C_SCOPE);
      end if;
      wb_cyc   <= '0';
      wb_stb   <= '0';
      wb_we    <= '0';
      wb_adr   <= (others => '0');
      wb_dat_w <= (others => '0');
      wait for 0 ns;
    end procedure;

    -- Classic Wishbone single read: drive the qualified cycle, hold until the
    -- regfile answers, then return the read data and the err_o termination flag.
    procedure bus_read(constant addr    : in  unsigned;
                       variable data    : out std_logic_vector(31 downto 0);
                       variable got_err : out boolean) is
    begin
      wb_cyc <= '1';
      wb_stb <= '1';
      wb_we  <= '0';
      wb_adr <= std_logic_vector(addr);
      wait until rising_edge(clk);
      while wb_ack = '0' and wb_err = '0' loop
        wait until rising_edge(clk);
      end loop;
      data    := wb_dat_r;
      got_err := wb_err = '1';
      wb_cyc  <= '0';
      wb_stb  <= '0';
      wb_adr  <= (others => '0');
      wait for 0 ns;
    end procedure;

    procedure bus_check(constant addr : in unsigned;
                        constant data : in std_logic_vector;
                        constant msg  : in string) is
      variable v_data    : std_logic_vector(31 downto 0);
      variable v_got_err : boolean;
    begin
      bus_read(addr, v_data, v_got_err);
      check_value(v_got_err, false, error, msg & " (terminated on ack)", C_SCOPE);
      check_value(v_data, data, error, msg, C_SCOPE);
    end procedure;

    -- An address without a register terminates on err.
    procedure bus_write_unmapped(constant addr : in unsigned;
                                 constant data : in std_logic_vector;
                                 constant msg  : in string) is
    begin
      bus_write(addr, data, msg, expect_err => true);
    end procedure;

    procedure bus_check_unmapped(constant addr : in unsigned;
                                 constant msg  : in string) is
      variable v_data    : std_logic_vector(31 downto 0);
      variable v_got_err : boolean;
    begin
      bus_read(addr, v_data, v_got_err);
      check_value(v_got_err, true, error, msg & " (terminated on err)", C_SCOPE);
    end procedure;
    variable v_reg9_field0_swmod : natural;
    variable v_reg9_field1_swacc : natural;
    variable v_reg10_field0_sp : natural;

  begin
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
    -- has one, reads as 0, and a write to it changes no register.
    log(ID_LOG_HDR, "addresses without a register get an error and change nothing", C_SCOPE);
    bus_write_unmapped(f_addr(32x"30"), 32x"0", "write 0x30, an unused register offset");
    bus_check_unmapped(f_addr(32x"30"), "read 0x30, an unused register offset");
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
