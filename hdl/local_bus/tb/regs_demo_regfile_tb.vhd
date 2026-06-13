-- Self-checking testbench for regs_demo_regfile.
-- Drives the local bus through a tiny inline BFM and exercises the core
-- access-mode matrix. Plain VHDL-2008 so it runs on bare nvc (no UVVM).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library std;
use std.env.all;

library work;
use work.localbus_pkg.all;
use work.regs_demo_regfile_pkg.all;

entity regs_demo_regfile_tb is
end entity regs_demo_regfile_tb;

architecture tb of regs_demo_regfile_tb is

  constant C_PERIOD : time := 10 ns;

  signal clk     : std_logic := '0';
  signal reset   : std_logic := '1';
  signal running : boolean   := true;

  signal lb_m2s  : t_lb_m2s := C_LB_M2S_IDLE;
  signal lb_s2m  : t_lb_s2m;
  signal to_hw   : t_regs_demo_to_hw;
  signal from_hw : t_regs_demo_from_hw := (
    status => (state => (others => '0'), state_we => '0', flag => '0',
               alarm => '0', alarm_wel => '1'),
    hwctrl => (level => (others => '0'), level_we => '0',
               gate_set => '0', gate_clr => '0'));

begin

  clk <= not clk after C_PERIOD/2 when running else '0';

  dut : entity work.regs_demo_regfile
    generic map (
      G_BASE_ADDRESS       => x"00000000",
      G_CHECK_BASE_ADDRESS => true)
    port map (
      clk     => clk,
      reset   => reset,
      lb_m2s  => lb_m2s,
      lb_s2m  => lb_s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  stim : process is
    variable errors : natural := 0;

    procedure check(cond : boolean; msg : string) is
    begin
      if not cond then
        errors := errors + 1;
        report "CHECK FAILED: " & msg severity error;
      end if;
    end procedure;

    procedure lb_write(addr : std_logic_vector(31 downto 0);
                       data : std_logic_vector(31 downto 0);
                       expect_ack : std_logic := '1') is
    begin
      wait until falling_edge(clk);
      lb_m2s.address <= addr;
      lb_m2s.wdata   <= data;
      lb_m2s.wen     <= '1';
      wait until falling_edge(clk);
      lb_m2s.wen <= '0';
      check(lb_s2m.ack = expect_ack,
            "write ack=" & std_logic'image(lb_s2m.ack) &
            " at addr 0x" & to_hstring(addr));
      check(lb_s2m.err = not expect_ack,
            "write err mismatch at addr 0x" & to_hstring(addr));
    end procedure;

    procedure lb_read(addr     : std_logic_vector(31 downto 0);
                      expected : std_logic_vector(31 downto 0);
                      expect_ack : std_logic := '1') is
    begin
      wait until falling_edge(clk);
      lb_m2s.address <= addr;
      lb_m2s.ren     <= '1';
      wait until falling_edge(clk);
      lb_m2s.ren <= '0';
      check(lb_s2m.ack = expect_ack,
            "read ack=" & std_logic'image(lb_s2m.ack) &
            " at addr 0x" & to_hstring(addr));
      check(lb_s2m.err = not expect_ack,
            "read err mismatch at addr 0x" & to_hstring(addr));
      if expect_ack = '1' then
        check(lb_s2m.rdata = expected,
              "read 0x" & to_hstring(lb_s2m.rdata) & " expected 0x" &
              to_hstring(expected) & " at addr 0x" & to_hstring(addr));
      end if;
    end procedure;
  begin
    wait for 3*C_PERIOD;
    wait until falling_edge(clk);
    reset <= '0';

    -- sw rw: write and read back CTRL (enable=1, mode="10" -> 0x5)
    lb_write(C_ADDR_CTRL, x"00000005");
    lb_read(C_ADDR_CTRL, x"00000005");
    check(to_hw.ctrl.enable = '1', "ctrl.enable not exposed to hw");
    check(to_hw.ctrl.mode = "10", "ctrl.mode not exposed to hw");

    -- sw rw, hw na: SCRATCH round-trips
    lb_write(C_ADDR_SCRATCH, x"000000A5");
    lb_read(C_ADDR_SCRATCH, x"000000A5");

    -- sw wo: TRIGGER drives hw but reads back 0
    lb_write(C_ADDR_CMD, x"00000001");
    check(to_hw.cmd.trigger = '1', "cmd.trigger not exposed to hw");
    lb_read(C_ADDR_CMD, x"00000000");

    -- sw ro fields are write-acked but unchanged; hardware drives them.
    wait until falling_edge(clk);
    from_hw.status.state     <= "1011";
    from_hw.status.state_we  <= '1';      -- hw w + we: capture this cycle
    from_hw.status.flag      <= '1';      -- hw w continuous
    from_hw.status.alarm     <= '1';
    from_hw.status.alarm_wel <= '0';      -- active-low enable asserted
    wait until falling_edge(clk);
    from_hw.status.state_we  <= '0';
    from_hw.status.alarm_wel <= '1';      -- disable further alarm writes
    -- STATUS = alarm(5)|flag(4)|state(3:0) = 1|1|1011 = 0x3B
    lb_read(C_ADDR_STATUS, x"0000003B");

    -- we gating: with state_we=0 a new hw value must NOT land
    wait until falling_edge(clk);
    from_hw.status.state <= "0000";
    lb_read(C_ADDR_STATUS, x"0000003B");
    -- wel gating: alarm_wel=1 holds alarm despite alarm=0
    wait until falling_edge(clk);
    from_hw.status.alarm <= '0';
    lb_read(C_ADDR_STATUS, x"0000003B");

    -- sw write to a read-only register acks but has no effect
    lb_write(C_ADDR_STATUS, x"FFFFFFFF");
    lb_read(C_ADDR_STATUS, x"0000003B");

    -- HWCTRL: sw write first
    lb_write(C_ADDR_HWCTRL, x"00000105");      -- level=5, gate=1
    lb_read(C_ADDR_HWCTRL, x"00000105");
    -- hw we overrides level
    wait until falling_edge(clk);
    from_hw.hwctrl.level    <= "1010";
    from_hw.hwctrl.level_we <= '1';
    wait until falling_edge(clk);
    from_hw.hwctrl.level_we <= '0';
    lb_read(C_ADDR_HWCTRL, x"0000010A");       -- level=0xA, gate still 1
    -- hwclr beats hwset in the same cycle -> gate clears
    wait until falling_edge(clk);
    from_hw.hwctrl.gate_set <= '1';
    from_hw.hwctrl.gate_clr <= '1';
    wait until falling_edge(clk);
    from_hw.hwctrl.gate_set <= '0';
    from_hw.hwctrl.gate_clr <= '0';
    lb_read(C_ADDR_HWCTRL, x"0000000A");       -- gate=0, level=0xA

    -- unmapped offset within base -> err
    lb_read(x"00000014", x"00000000", expect_ack => '0');
    lb_write(x"00000014", x"00000000", expect_ack => '0');
    -- wrong base address -> err
    lb_read(x"10000000", x"00000000", expect_ack => '0');

    wait until falling_edge(clk);
    if errors = 0 then
      report "REGS_DEMO REGFILE TB PASSED" severity note;
    else
      report "REGS_DEMO REGFILE TB FAILED with " & integer'image(errors) &
             " error(s)" severity failure;
    end if;
    running <= false;
    wait for C_PERIOD;
    stop;
    wait;
  end process stim;

end architecture tb;
