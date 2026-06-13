-- Protocol-agnostic register file for the regs_demo prototype module.
-- Speaks only the local bus; protocol wrappers (AXI, IPBus) instantiate it.
-- Exercises the core access-mode matrix: sw {rw,ro,wo,na} x hw {r,w,rw,na}
-- plus the we/wel/hwset/hwclr modifiers.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.localbus_pkg.all;
use work.regs_demo_regfile_pkg.all;

entity regs_demo_regfile is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
  );
  port (
    clk     : in  std_logic;
    reset   : in  std_logic;                  -- synchronous, active high
    lb_m2s  : in  t_lb_m2s;
    lb_s2m  : out t_lb_s2m;
    to_hw   : out t_regs_demo_to_hw;
    from_hw : in  t_regs_demo_from_hw
  );
end entity regs_demo_regfile;

architecture rtl of regs_demo_regfile is

  signal ctrl_enable  : std_logic;
  signal ctrl_mode    : std_logic_vector(1 downto 0);
  signal status_state : std_logic_vector(3 downto 0);
  signal status_flag  : std_logic;
  signal status_alarm : std_logic;
  signal cmd_trigger  : std_logic;
  signal scratch_val  : std_logic_vector(7 downto 0);
  signal hwctrl_level : std_logic_vector(3 downto 0);
  signal hwctrl_gate  : std_logic;

  signal rdata : std_logic_vector(31 downto 0);
  signal ack   : std_logic;
  signal err   : std_logic;

  function base_ok(addr : std_logic_vector(31 downto 0)) return boolean is
    constant base_slv : std_logic_vector(31 downto 0) := std_logic_vector(G_BASE_ADDRESS);
  begin
    if not G_CHECK_BASE_ADDRESS then
      return true;
    end if;
    return addr(31 downto C_MODULE_ADDR_WIDTH)
         = base_slv(31 downto C_MODULE_ADDR_WIDTH);
  end function;

begin

  -- base_ok only compares bits above the module window, so the base must be
  -- aligned to that window or it would match a whole 2**C_MODULE_ADDR_WIDTH span.
  assert (not G_CHECK_BASE_ADDRESS)
      or (G_BASE_ADDRESS(C_MODULE_ADDR_WIDTH-1 downto 0) = 0)
    report "G_BASE_ADDRESS must be aligned to 2**C_MODULE_ADDR_WIDTH bytes"
    severity failure;

  to_hw.ctrl.enable  <= ctrl_enable;
  to_hw.ctrl.mode    <= ctrl_mode;
  to_hw.cmd.trigger  <= cmd_trigger;
  to_hw.hwctrl.level <= hwctrl_level;
  to_hw.hwctrl.gate  <= hwctrl_gate;

  lb_s2m.rdata   <= rdata;
  lb_s2m.ack     <= ack;
  lb_s2m.err     <= err;
  lb_s2m.waitreq <= '0';

  p_access : process (clk) is
    variable sel : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0);
  begin
    if rising_edge(clk) then
      if reset = '1' then
        ctrl_enable  <= '0';
        ctrl_mode    <= (others => '0');
        status_state <= (others => '0');
        status_flag  <= '0';
        status_alarm <= '0';
        cmd_trigger  <= '0';
        scratch_val  <= (others => '0');
        hwctrl_level <= (others => '0');
        hwctrl_gate  <= '0';
        rdata        <= (others => '0');
        ack          <= '0';
        err          <= '0';
      else
        ack <= '0';
        err <= '0';
        sel := lb_m2s.address(C_MODULE_ADDR_WIDTH-1 downto 0);

        -- Hardware writes into sw-read-only status fields.
        status_flag <= from_hw.status.flag;                 -- hw w, continuous
        if from_hw.status.state_we = '1' then               -- hw w, we
          status_state <= from_hw.status.state;
        end if;
        if from_hw.status.alarm_wel = '0' then              -- hw w, wel (active low)
          status_alarm <= from_hw.status.alarm;
        end if;

        if lb_m2s.wen = '1' then
          if not base_ok(lb_m2s.address) then
            err <= '1';
          elsif sel = C_ADDR_CTRL(C_MODULE_ADDR_WIDTH-1 downto 0) then
            ctrl_enable <= lb_m2s.wdata(0);                 -- sw rw
            ctrl_mode   <= lb_m2s.wdata(2 downto 1);        -- sw rw
            ack <= '1';
          elsif sel = C_ADDR_CMD(C_MODULE_ADDR_WIDTH-1 downto 0) then
            cmd_trigger <= lb_m2s.wdata(0);                 -- sw wo
            ack <= '1';
          elsif sel = C_ADDR_SCRATCH(C_MODULE_ADDR_WIDTH-1 downto 0) then
            scratch_val <= lb_m2s.wdata(7 downto 0);        -- sw rw, hw na
            ack <= '1';
          elsif sel = C_ADDR_HWCTRL(C_MODULE_ADDR_WIDTH-1 downto 0) then
            hwctrl_level <= lb_m2s.wdata(3 downto 0);       -- sw rw (hw may override below)
            hwctrl_gate  <= lb_m2s.wdata(8);                -- sw rw (hw may override below)
            ack <= '1';
          elsif sel = C_ADDR_STATUS(C_MODULE_ADDR_WIDTH-1 downto 0) then
            ack <= '1';                                     -- all fields sw ro: ack, no effect
          else
            err <= '1';
          end if;
        end if;

        -- Hardware overrides on HWCTRL, ordered so the documented precedence
        -- (hwclr > hwset > hw we > sw write) resolves by last-assignment-wins.
        if from_hw.hwctrl.level_we = '1' then               -- hw rw, we
          hwctrl_level <= from_hw.hwctrl.level;
        end if;
        if from_hw.hwctrl.gate_set = '1' then               -- hwset
          hwctrl_gate <= '1';
        end if;
        if from_hw.hwctrl.gate_clr = '1' then               -- hwclr
          hwctrl_gate <= '0';
        end if;

        if lb_m2s.ren = '1' then
          rdata <= (others => '0');
          if not base_ok(lb_m2s.address) then
            err <= '1';
          elsif sel = C_ADDR_CTRL(C_MODULE_ADDR_WIDTH-1 downto 0) then
            rdata(0)          <= ctrl_enable;
            rdata(2 downto 1) <= ctrl_mode;
            ack <= '1';
          elsif sel = C_ADDR_STATUS(C_MODULE_ADDR_WIDTH-1 downto 0) then
            rdata(3 downto 0) <= status_state;
            rdata(4)          <= status_flag;
            rdata(5)          <= status_alarm;
            ack <= '1';
          elsif sel = C_ADDR_CMD(C_MODULE_ADDR_WIDTH-1 downto 0) then
            ack <= '1';                                     -- trigger sw wo: reads 0
          elsif sel = C_ADDR_SCRATCH(C_MODULE_ADDR_WIDTH-1 downto 0) then
            rdata(7 downto 0) <= scratch_val;
            ack <= '1';
          elsif sel = C_ADDR_HWCTRL(C_MODULE_ADDR_WIDTH-1 downto 0) then
            rdata(3 downto 0) <= hwctrl_level;
            rdata(8)          <= hwctrl_gate;
            ack <= '1';
          else
            err <= '1';
          end if;
        end if;
      end if;
    end if;
  end process p_access;

end architecture rtl;
