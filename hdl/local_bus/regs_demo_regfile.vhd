-- Protocol-agnostic register file for the regs_demo prototype module.
-- Speaks only the local bus; protocol wrappers (AXI, IPBus) instantiate it.
-- Exercises the core access-mode matrix: sw {rw,ro,wo,na} x hw {r,w,rw,na}
-- plus the we/wel/hwset/hwclr modifiers.
--
-- Two clocked processes split the bus side: p_write owns register storage
-- (software writes and all hardware-driven updates, since both modify state)
-- and the write response; p_read owns the read mux and the read response.
-- Concurrent output assignments are grouped at the bottom of the file.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;
use work.regs_demo_regfile_pkg.all;

entity regs_demo_regfile is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true;
    -- Reset polarity. Some FPGA families prefer active-low resets; the regfile
    -- normalizes internally so the rest of the logic is polarity-agnostic.
    G_RESET_ACTIVE_LOW   : boolean               := false
  );
  port (
    clk     : in  std_logic;
    reset   : in  std_logic;
    lb_m2s  : in  t_lb_m2s;
    lb_s2m  : out t_lb_s2m;
    to_hw   : out t_regs_demo_to_hw;
    from_hw : in  t_regs_demo_from_hw
  );
end entity regs_demo_regfile;

architecture rtl of regs_demo_regfile is

  signal regs : t_regs_demo_regs := C_REGS_DEMO_REGS_RESET;

  signal rst    : std_logic;            -- reset normalized to active high
  signal rdata  : std_logic_vector(31 downto 0);
  signal wr_ack : std_logic;
  signal wr_err : std_logic;
  signal rd_ack : std_logic;
  signal rd_err : std_logic;

begin

  rst <= (reset xor '1') when G_RESET_ACTIVE_LOW else reset;

  -- base_match compares only bits above the module window, so the base must be
  -- aligned to that window or it would match a whole 2**C_MODULE_ADDR_WIDTH span.
  assert (not G_CHECK_BASE_ADDRESS)
      or (G_BASE_ADDRESS(C_MODULE_ADDR_WIDTH-1 downto 0) = 0)
    report "G_BASE_ADDRESS must be aligned to 2**C_MODULE_ADDR_WIDTH bytes"
    severity failure;

  -- Register storage and write response. Single driver of `regs`: software
  -- writes and hardware updates both live here. Each multi-source field uses
  -- an if/elsif chain so the documented precedence (provisional, since
  -- `precedence` is deferred) reads top-to-bottom:
  --   hwclr > hwset > hardware we/wel write > software write.
  p_write : process (clk) is
    variable sel        : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0);
    variable hit        : boolean;     -- write addresses a known register
    variable wr_ctrl    : boolean;
    variable wr_scratch : boolean;
    variable wr_hwctrl  : boolean;
    variable wr_cmd     : boolean;
    variable sw_write   : boolean;     -- a fresh, in-window software write
  begin
    if rising_edge(clk) then
      wr_ack <= '0';
      wr_err <= '0';

      -- A software write only takes effect on the cycle the request is first
      -- seen (wr_ack/wr_err still low). The master holds the request until it
      -- observes the response, so this guard keeps writes and the ack pulse
      -- single-shot.
      sel        := lb_m2s.address(C_MODULE_ADDR_WIDTH-1 downto 0);
      sw_write   := lb_m2s.wen = '1' and wr_ack = '0' and wr_err = '0'
                    and base_match(lb_m2s.address, G_BASE_ADDRESS, G_CHECK_BASE_ADDRESS);
      wr_ctrl    := sw_write and sel = C_ADDR_CTRL(C_MODULE_ADDR_WIDTH-1 downto 0);
      wr_cmd     := sw_write and sel = C_ADDR_CMD(C_MODULE_ADDR_WIDTH-1 downto 0);
      wr_scratch := sw_write and sel = C_ADDR_SCRATCH(C_MODULE_ADDR_WIDTH-1 downto 0);
      wr_hwctrl  := sw_write and sel = C_ADDR_HWCTRL(C_MODULE_ADDR_WIDTH-1 downto 0);

      -- CTRL: sw rw, hw r
      if wr_ctrl then
        regs.ctrl.enable <= lb_m2s.wdata(0);
        regs.ctrl.mode   <= lb_m2s.wdata(2 downto 1);
      end if;

      -- CMD.TRIGGER: sw wo, hw r (drives hardware, reads back 0)
      if wr_cmd then
        regs.cmd.trigger <= lb_m2s.wdata(0);
      end if;

      -- SCRATCH.VAL: sw rw, hw na
      if wr_scratch then
        regs.scratch.val <= lb_m2s.wdata(7 downto 0);
      end if;

      -- STATUS: sw ro, hardware-driven.
      if from_hw.status.state.we = '1' then        -- STATE: hw w, we
        regs.status.state <= from_hw.status.state.value;
      end if;
      regs.status.flag <= from_hw.status.flag;      -- FLAG: hw w, continuous
      if from_hw.status.alarm.wel = '0' then        -- ALARM: hw w, active-low we
        regs.status.alarm <= from_hw.status.alarm.value;
      end if;

      -- HWCTRL.LEVEL: hardware we write wins over software write.
      if from_hw.hwctrl.level.we = '1' then
        regs.hwctrl.level <= from_hw.hwctrl.level.value;
      elsif wr_hwctrl then
        regs.hwctrl.level <= lb_m2s.wdata(3 downto 0);
      end if;

      -- HWCTRL.GATE: hwclr > hwset > software write.
      if from_hw.hwctrl.gate.clr = '1' then
        regs.hwctrl.gate <= '0';
      elsif from_hw.hwctrl.gate.set = '1' then
        regs.hwctrl.gate <= '1';
      elsif wr_hwctrl then
        regs.hwctrl.gate <= lb_m2s.wdata(8);
      end if;

      -- Write response: ack a mapped register (STATUS acks with no effect, all
      -- its fields being sw ro), err an out-of-range or unmapped address.
      if lb_m2s.wen = '1' and wr_ack = '0' and wr_err = '0' then
        if not base_match(lb_m2s.address, G_BASE_ADDRESS, G_CHECK_BASE_ADDRESS) then
          hit := false;
        else
          hit := sel = C_ADDR_CTRL(C_MODULE_ADDR_WIDTH-1 downto 0)
              or sel = C_ADDR_STATUS(C_MODULE_ADDR_WIDTH-1 downto 0)
              or sel = C_ADDR_CMD(C_MODULE_ADDR_WIDTH-1 downto 0)
              or sel = C_ADDR_SCRATCH(C_MODULE_ADDR_WIDTH-1 downto 0)
              or sel = C_ADDR_HWCTRL(C_MODULE_ADDR_WIDTH-1 downto 0);
        end if;
        if hit then
          wr_ack <= '1';
        else
          wr_err <= '1';
        end if;
      end if;

      if rst = '1' then
        regs   <= C_REGS_DEMO_REGS_RESET;
        wr_ack <= '0';
        wr_err <= '0';
      end if;
    end if;
  end process p_write;

  -- Read mux and read response. Never writes storage (onread effects are
  -- deferred). Reads of non-readable fields (sw wo / na) return 0 and ack; err
  -- is reserved for address-decode failures, matching SystemRDL and the v1
  -- bus PIFs.
  p_read : process (clk) is
    variable sel : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0);
  begin
    if rising_edge(clk) then
      rd_ack <= '0';
      rd_err <= '0';

      if lb_m2s.ren = '1' and rd_ack = '0' and rd_err = '0' then
        rdata <= (others => '0');
        sel   := lb_m2s.address(C_MODULE_ADDR_WIDTH-1 downto 0);
        if not base_match(lb_m2s.address, G_BASE_ADDRESS, G_CHECK_BASE_ADDRESS) then
          rd_err <= '1';
        elsif sel = C_ADDR_CTRL(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rdata(0)          <= regs.ctrl.enable;
          rdata(2 downto 1) <= regs.ctrl.mode;
          rd_ack <= '1';
        elsif sel = C_ADDR_STATUS(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rdata(3 downto 0) <= regs.status.state;
          rdata(4)          <= regs.status.flag;
          rdata(5)          <= regs.status.alarm;
          rd_ack <= '1';
        elsif sel = C_ADDR_CMD(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rd_ack <= '1';                            -- TRIGGER sw wo: reads 0
        elsif sel = C_ADDR_SCRATCH(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rdata(7 downto 0) <= regs.scratch.val;
          rd_ack <= '1';
        elsif sel = C_ADDR_HWCTRL(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rdata(3 downto 0) <= regs.hwctrl.level;
          rdata(8)          <= regs.hwctrl.gate;
          rd_ack <= '1';
        else
          rd_err <= '1';
        end if;
      end if;

      if rst = '1' then
        rdata  <= (others => '0');
        rd_ack <= '0';
        rd_err <= '0';
      end if;
    end if;
  end process p_read;

  to_hw.ctrl.enable  <= regs.ctrl.enable;
  to_hw.ctrl.mode    <= regs.ctrl.mode;
  to_hw.cmd.trigger  <= regs.cmd.trigger;
  to_hw.hwctrl.level <= regs.hwctrl.level;
  to_hw.hwctrl.gate  <= regs.hwctrl.gate;

  lb_s2m.rdata <= rdata;
  lb_s2m.ack   <= wr_ack or rd_ack;
  lb_s2m.err   <= wr_err or rd_err;

end architecture rtl;
