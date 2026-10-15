-- UVVM testbench for prototype_regfile.
-- Drives the local bus through the localbus UVVM BFM and exercises the core
-- access-mode matrix, the we/wel/hwset/hwclr modifiers, the documented
-- hardware/software write precedence, the onread/onwrite software side effects,
-- the swmod/swacc/singlepulse pulse behaviours, enumerated-value field types,
-- and the err response for both unmapped offsets and wrong-base-address
-- transactions. Registers/fields use generic names (reg0..reg11, field0..); see
-- prototype_regfile_pkg.vhd.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;
use work.localbus_bfm_pkg.all;

entity prototype_regfile_tb is
end entity prototype_regfile_tb;

architecture tb of prototype_regfile_tb is

  constant C_SCOPE  : string := C_TB_SCOPE_DEFAULT;
  constant C_PERIOD : time   := 10 ns;

  signal clk     : std_logic := '0';
  signal reset   : std_logic := '1';
  signal running : boolean   := true;

  signal lb_m2s  : t_lb_m2s := C_LB_M2S_IDLE;
  signal lb_s2m  : t_lb_s2m;
  signal to_hw   : t_prototype_to_hw;
  signal from_hw : t_prototype_from_hw := (
    reg1 => (field0 => (value => (others => '0'), we => '0'),
             field1 => '0',
             field2 => (value => '0', wel => '1')),
    reg4 => (field0 => (value => (others => '0'), we => '0'),
             field1 => (set => '0', clr => '0')));

  -- Pulse monitors: count the cycles each strobe / singlepulse value is high so
  -- a single-cycle pulse is verifiable without cycle-accurate sampling.
  signal swmod_count   : natural := 0;
  signal swacc_count   : natural := 0;
  signal sp_high_count : natural := 0;
  signal sp_last_value : std_logic_vector(3 downto 0) := (others => '0');

begin

  clk <= not clk after C_PERIOD/2 when running else '0';

  dut : entity work.prototype_regfile
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

  p_monitor : process (clk) is
  begin
    if rising_edge(clk) then
      if to_hw.reg9.field0.swmod = '1' then
        swmod_count <= swmod_count + 1;
      end if;
      if to_hw.reg9.field1.swacc = '1' then
        swacc_count <= swacc_count + 1;
      end if;
      if to_hw.reg10.field0 /= "0000" then
        sp_high_count <= sp_high_count + 1;
        sp_last_value <= to_hw.reg10.field0;
      end if;
    end if;
  end process p_monitor;

  p_main : process is
  begin
    set_log_file_name("prototype_regfile_log.txt");
    set_alert_file_name("prototype_regfile_alert.txt");

    wait for 3*C_PERIOD;
    wait until falling_edge(clk);
    reset <= '0';

    log(ID_LOG_HDR, "reg0: sw rw + hw r", C_SCOPE);
    localbus_write(C_ADDR_REG0, x"00000005", "field0=1, field1=10", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG0, x"00000005", "reg0 reads back", clk, lb_m2s, lb_s2m);
    check_value(to_hw.reg0.field0, '1', error, "reg0.field0 exposed to hw", C_SCOPE);
    check_value(to_hw.reg0.field1, "10", error, "reg0.field1 exposed to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg3: sw rw + hw na round-trip", C_SCOPE);
    localbus_write(C_ADDR_REG3, x"000000A5", "reg3=0xA5", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG3, x"000000A5", "reg3 reads back", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg2: sw wo drives hw but reads 0", C_SCOPE);
    localbus_write(C_ADDR_REG2, x"00000001", "field0=1", clk, lb_m2s, lb_s2m);
    check_value(to_hw.reg2.field0, '1', error, "reg2.field0 exposed to hw", C_SCOPE);
    localbus_check(C_ADDR_REG2, x"00000000", "wo reads back 0", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg1: sw ro, hardware-driven (we / continuous / wel)", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg1.field0.value <= "1011";
    from_hw.reg1.field0.we    <= '1';      -- capture this cycle
    from_hw.reg1.field1       <= '1';      -- continuous
    from_hw.reg1.field2.value <= '1';
    from_hw.reg1.field2.wel   <= '0';      -- active-low enable asserted
    wait until falling_edge(clk);
    from_hw.reg1.field0.we    <= '0';
    from_hw.reg1.field2.wel   <= '1';      -- stop further field2 writes
    -- reg1 = field2(5)|field1(4)|field0(3:0) = 1|1|1011 = 0x3B
    localbus_check(C_ADDR_REG1, x"0000003B", "reg1 reflects hw", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "we / wel gating: held values do not land", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg1.field0.value <= "0000";   -- we=0, must not land
    localbus_check(C_ADDR_REG1, x"0000003B", "field0 held (we=0)", clk, lb_m2s, lb_s2m);
    wait until falling_edge(clk);
    from_hw.reg1.field2.value <= '0';      -- wel=1, must not land
    localbus_check(C_ADDR_REG1, x"0000003B", "field2 held (wel=1)", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "sw write to read-only reg1 acks, no effect", C_SCOPE);
    localbus_write(C_ADDR_REG1, x"FFFFFFFF", "write ro acks", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG1, x"0000003B", "reg1 unchanged", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg4: sw write, then hw we override on field0", C_SCOPE);
    localbus_write(C_ADDR_REG4, x"00000105", "field0=5, field1=1", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG4, x"00000105", "reg4 reads back", clk, lb_m2s, lb_s2m);
    check_value(to_hw.reg4.field0, "0101", error, "field0 exposed to hw", C_SCOPE);
    check_value(to_hw.reg4.field1, '1', error, "field1 exposed to hw", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg4.field0.value <= "1010";
    from_hw.reg4.field0.we    <= '1';
    wait until falling_edge(clk);
    from_hw.reg4.field0.we    <= '0';
    localbus_check(C_ADDR_REG4, x"0000010A", "hw we overrode field0", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg4.field1: hwset, then hwclr beats hwset", C_SCOPE);
    wait until falling_edge(clk);
    from_hw.reg4.field1.set <= '1';
    wait until falling_edge(clk);
    from_hw.reg4.field1.set <= '0';
    localbus_check(C_ADDR_REG4, x"0000010A", "hwset set field1", clk, lb_m2s, lb_s2m);
    wait until falling_edge(clk);
    from_hw.reg4.field1.set <= '1';
    from_hw.reg4.field1.clr <= '1';         -- same cycle: clr wins
    wait until falling_edge(clk);
    from_hw.reg4.field1.set <= '0';
    from_hw.reg4.field1.clr <= '0';
    localbus_check(C_ADDR_REG4, x"0000000A", "hwclr beat hwset", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg5: onread rclr (field0) / rset (field1)", C_SCOPE);
    localbus_write(C_ADDR_REG5, x"0000005A", "field0=A, field1=5", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG5, x"0000005A", "read returns pre-effect value", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG5, x"000000F0", "onread: field0 cleared, field1 set", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg6: onwrite woset / woclr / wot", C_SCOPE);
    localbus_write(C_ADDR_REG6, x"0000065C", "woset 0xC, woclr 0x5, wot 0x6", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG6, x"000006AC", "field0 set, field1 bits cleared, field2 toggled", clk, lb_m2s, lb_s2m);
    check_value(to_hw.reg6.field0, "1100", error, "reg6.field0 exposed to hw", C_SCOPE);
    localbus_write(C_ADDR_REG6, x"0000065C", "same write again", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG6, x"000000AC", "woset/woclr idempotent, wot toggled back", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg7: onwrite wzs / wzc / wzt", C_SCOPE);
    localbus_write(C_ADDR_REG7, x"00000555", "write 0x5 to each field", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG7, x"00000A5A", "wzs/wzc/wzt act on the zero bits", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg8: onwrite wclr / wset (data-independent)", C_SCOPE);
    localbus_write(C_ADDR_REG8, x"00000000", "any write triggers wclr/wset", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG8, x"000000F0", "field0 cleared, field1 set", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg9: swmod (field0) / swacc (field1) pulse outputs", C_SCOPE);
    localbus_write(C_ADDR_REG9, x"00000034", "field0=4, field1=3", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG9, x"00000034", "reg9 reads back", clk, lb_m2s, lb_s2m);
    check_value(to_hw.reg9.field0.value, "0100", error, "reg9.field0 value to hw", C_SCOPE);
    check_value(to_hw.reg9.field1.value, "0011", error, "reg9.field1 value to hw", C_SCOPE);

    log(ID_LOG_HDR, "reg10: singlepulse self-clears one cycle after write", C_SCOPE);
    localbus_write(C_ADDR_REG10, x"00000007", "pulse value 7", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG10, x"00000000", "field self-cleared after the pulse", clk, lb_m2s, lb_s2m);

    log(ID_LOG_HDR, "reg11: enumerated field0 (STATE0..STATE3)", C_SCOPE);
    localbus_write(C_ADDR_REG11, x"00000002", "field0 = STATE2", clk, lb_m2s, lb_s2m);
    localbus_check(C_ADDR_REG11, x"00000002", "reg11 reads back the encoded value", clk, lb_m2s, lb_s2m);
    check_value(to_hw.reg11.field0 = STATE2, error, "reg11.field0 is STATE2 to hw", C_SCOPE);

    log(ID_LOG_HDR, "err: unmapped offset and wrong base address", C_SCOPE);
    localbus_check_err(x"0000003C", false, "read unmapped offset", clk, lb_m2s, lb_s2m);
    localbus_check_err(x"0000003C", true,  "write unmapped offset", clk, lb_m2s, lb_s2m);
    localbus_check_err(x"10000000", false, "read wrong base", clk, lb_m2s, lb_s2m);
    localbus_check_err(x"10000000", true,  "write wrong base", clk, lb_m2s, lb_s2m);

    wait for 10*C_PERIOD;

    log(ID_LOG_HDR, "pulse monitors: single-cycle width and counts", C_SCOPE);
    check_value(swmod_count, 1, error, "swmod pulsed once (1 write)", C_SCOPE);
    check_value(swacc_count, 2, error, "swacc pulsed per access (1 write + 1 read)", C_SCOPE);
    check_value(sp_high_count, 1, error, "singlepulse high exactly one cycle", C_SCOPE);
    check_value(sp_last_value, "0111", error, "hw saw the pulse value", C_SCOPE);

    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    running <= false;
    wait for C_PERIOD;
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
