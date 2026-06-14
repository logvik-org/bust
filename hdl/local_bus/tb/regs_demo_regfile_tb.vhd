-- UVVM testbench for regs_demo_regfile.
-- Drives the local bus through the localbus UVVM BFM and exercises the core
-- access-mode matrix, the we/wel/hwset/hwclr modifiers, the documented
-- hardware/software write precedence, and the err response for both unmapped
-- offsets and wrong-base-address transactions.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

use work.localbus_pkg.all;
use work.regs_demo_regfile_pkg.all;
use work.localbus_bfm_pkg.all;

entity regs_demo_regfile_tb is
end entity regs_demo_regfile_tb;

architecture tb of regs_demo_regfile_tb is

  constant C_SCOPE  : string := C_TB_SCOPE_DEFAULT;
  constant C_PERIOD : time   := 10 ns;

  signal clk     : std_logic := '0';
  signal reset   : std_logic := '1';
  signal running : boolean   := true;

  signal lb_m2s  : t_lb_m2s := C_LB_M2S_IDLE;
  signal lb_s2m  : t_lb_s2m;
  signal to_hw   : t_regs_demo_to_hw;
  signal from_hw : t_regs_demo_from_hw := (
    status => (state => (value => (others => '0'), we => '0'),
               flag  => '0',
               alarm => (value => '0', wel => '1')),
    hwctrl => (level => (value => (others => '0'), we => '0'),
               gate  => (set => '0', clr => '0')));

begin

  clk <= not clk after C_PERIOD/2 when running else '0';

  dut : entity work.regs_demo_regfile
    generic map (
      G_BASE_ADDRESS       => x"00000000",
      G_CHECK_BASE_ADDRESS => true,
      G_RESET_ACTIVE_LOW   => false)
    port map (
      clk     => clk,
      reset   => reset,
      lb_m2s  => lb_m2s,
      lb_s2m  => lb_s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_main : process is
  begin
    set_log_file_name("regs_demo_regfile_log.txt");
    set_alert_file_name("regs_demo_regfile_alert.txt");

    wait for 3*C_PERIOD;
    wait until falling_edge(clk);
    reset <= '0';

    log(ID_LOG_HDR, "CTRL: sw rw + hw r", C_SCOPE);
    localbus_write(C_ADDR_CTRL, x"00000005", "enable=1, mode=10", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_CTRL, x"00000005", "CTRL reads back", clk, lb_m2s, lb_s2m);
    check_value(to_hw.ctrl.enable, '1', error, "ctrl.enable exposed to hw", C_SCOPE);
    check_value(to_hw.ctrl.mode, "10", error, "ctrl.mode exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "SCRATCH: sw rw + hw na round-trip", C_SCOPE);
    localbus_write(C_ADDR_SCRATCH, x"000000A5", "scratch=0xA5", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_SCRATCH, x"000000A5", "scratch reads back", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "CMD: sw wo drives hw but reads 0", C_SCOPE);
    localbus_write(C_ADDR_CMD, x"00000001", "trigger=1", clk, lb_m2s, lb_s2m);
    check_value(to_hw.cmd.trigger, '1', error, "cmd.trigger exposed to hw", C_SCOPE);
    localbus_check(C_ADDR_CMD, x"00000000", "wo reads back 0", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "STATUS: sw ro, hardware-driven (we / continuous / wel)", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.status.state.value <= "1011";
    from_hw.status.state.we    <= '1';      -- capture this cycle
    from_hw.status.flag        <= '1';      -- continuous
    from_hw.status.alarm.value <= '1';
    from_hw.status.alarm.wel   <= '0';      -- active-low enable asserted
    wait until falling_edge(clk);
    from_hw.status.state.we    <= '0';
    from_hw.status.alarm.wel   <= '1';      -- stop further alarm writes
    -- STATUS = alarm(5)|flag(4)|state(3:0) = 1|1|1011 = 0x3B
    localbus_check(C_ADDR_STATUS, x"0000003B", "status reflects hw", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "we / wel gating: held values do not land", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.status.state.value <= "0000";   -- we=0, must not land
    localbus_check(C_ADDR_STATUS, x"0000003B", "state held (we=0)", clk, lb_m2s, lb_s2m);
    wait until falling_edge(clk);
    from_hw.status.alarm.value <= '0';      -- wel=1, must not land
    localbus_check(C_ADDR_STATUS, x"0000003B", "alarm held (wel=1)", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "sw write to read-only STATUS acks, no effect", C_SCOPE);
    localbus_write(C_ADDR_STATUS, x"FFFFFFFF", "write ro acks", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_STATUS, x"0000003B", "status unchanged", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "HWCTRL: sw write, then hw we override on LEVEL", C_SCOPE);
    localbus_write(C_ADDR_HWCTRL, x"00000105", "level=5, gate=1", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_HWCTRL, x"00000105", "hwctrl reads back", clk, lb_m2s, lb_s2m);
    check_value(to_hw.hwctrl.level, "0101", error, "level exposed to hw", C_SCOPE);
    check_value(to_hw.hwctrl.gate, '1', error, "gate exposed to hw", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.hwctrl.level.value <= "1010";
    from_hw.hwctrl.level.we    <= '1';
    wait until falling_edge(clk);
    from_hw.hwctrl.level.we    <= '0';
    localbus_check(C_ADDR_HWCTRL, x"0000010A", "hw we overrode level", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "HWCTRL.GATE: hwset, then hwclr beats hwset", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.hwctrl.gate.set <= '1';
    wait until falling_edge(clk);
    from_hw.hwctrl.gate.set <= '0';
    localbus_check(C_ADDR_HWCTRL, x"0000010A", "hwset set gate", clk, lb_m2s, lb_s2m);
    wait until falling_edge(clk);
    from_hw.hwctrl.gate.set <= '1';
    from_hw.hwctrl.gate.clr <= '1';         -- same cycle: clr wins
    wait until falling_edge(clk);
    from_hw.hwctrl.gate.set <= '0';
    from_hw.hwctrl.gate.clr <= '0';
    localbus_check(C_ADDR_HWCTRL, x"0000000A", "hwclr beat hwset", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "err: unmapped offset and wrong base address", C_SCOPE);
    localbus_check_err(x"00000014", false, "read unmapped offset", clk, lb_m2s, lb_s2m);
    localbus_check_err(x"00000014", true,  "write unmapped offset", clk, lb_m2s, lb_s2m);
    localbus_check_err(x"10000000", false, "read wrong base", clk, lb_m2s, lb_s2m);
    localbus_check_err(x"10000000", true,  "write wrong base", clk, lb_m2s, lb_s2m);

    wait for 10*C_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    running <= false;
    wait for C_PERIOD;
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
