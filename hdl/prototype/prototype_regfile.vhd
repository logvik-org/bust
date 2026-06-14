-- Protocol-agnostic register file for the prototype module.
-- Speaks only the local bus; protocol wrappers (AXI, IPBus) instantiate it.
-- Exercises the core access-mode matrix: sw {rw,ro,wo,na} x hw {r,w,rw,na}
-- plus the we/wel/hwset/hwclr modifiers. Registers/fields use generic names
-- (reg0..reg4, field0..); see prototype_regfile_pkg.vhd for the access map.
--
-- Two clocked processes split the bus side: p_write owns register storage
-- (software writes and all hardware-driven updates, since both modify state)
-- and the write response; p_read owns the read mux and the read response.
-- Concurrent output assignments are grouped at the bottom of the file.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_regfile is
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
    to_hw   : out t_prototype_to_hw;
    from_hw : in  t_prototype_from_hw
  );
end entity prototype_regfile;

architecture rtl of prototype_regfile is

  signal regs : t_prototype_regs := C_PROTOTYPE_REGS_RESET;

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
    variable sel      : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0);
    variable hit      : boolean;     -- write addresses a known register
    variable wr_reg0  : boolean;
    variable wr_reg2  : boolean;
    variable wr_reg3  : boolean;
    variable wr_reg4  : boolean;
    variable sw_write : boolean;     -- a fresh, in-window software write
  begin
    if rising_edge(clk) then
      wr_ack <= '0';
      wr_err <= '0';

      -- A software write only takes effect on the cycle the request is first
      -- seen (wr_ack/wr_err still low). The master holds the request until it
      -- observes the response, so this guard keeps writes and the ack pulse
      -- single-shot.
      sel      := lb_m2s.address(C_MODULE_ADDR_WIDTH-1 downto 0);
      sw_write := lb_m2s.wen = '1' and wr_ack = '0' and wr_err = '0'
                  and base_match(lb_m2s.address, G_BASE_ADDRESS, G_CHECK_BASE_ADDRESS);
      wr_reg0  := sw_write and sel = C_ADDR_REG0(C_MODULE_ADDR_WIDTH-1 downto 0);
      wr_reg2  := sw_write and sel = C_ADDR_REG2(C_MODULE_ADDR_WIDTH-1 downto 0);
      wr_reg3  := sw_write and sel = C_ADDR_REG3(C_MODULE_ADDR_WIDTH-1 downto 0);
      wr_reg4  := sw_write and sel = C_ADDR_REG4(C_MODULE_ADDR_WIDTH-1 downto 0);

      -- reg0: sw rw, hw r
      if wr_reg0 then
        regs.reg0.field0 <= lb_m2s.wdata(0);
        regs.reg0.field1 <= lb_m2s.wdata(2 downto 1);
      end if;

      -- reg2.field0: sw wo, hw r (drives hardware, reads back 0)
      if wr_reg2 then
        regs.reg2.field0 <= lb_m2s.wdata(0);
      end if;

      -- reg3.field0: sw rw, hw na
      if wr_reg3 then
        regs.reg3.field0 <= lb_m2s.wdata(7 downto 0);
      end if;

      -- reg1: sw ro, hardware-driven.
      if from_hw.reg1.field0.we = '1' then          -- field0: hw w, we
        regs.reg1.field0 <= from_hw.reg1.field0.value;
      end if;
      regs.reg1.field1 <= from_hw.reg1.field1;       -- field1: hw w, continuous
      if from_hw.reg1.field2.wel = '0' then          -- field2: hw w, active-low we
        regs.reg1.field2 <= from_hw.reg1.field2.value;
      end if;

      -- reg4.field0: hardware we write wins over software write.
      if from_hw.reg4.field0.we = '1' then
        regs.reg4.field0 <= from_hw.reg4.field0.value;
      elsif wr_reg4 then
        regs.reg4.field0 <= lb_m2s.wdata(3 downto 0);
      end if;

      -- reg4.field1: hwclr > hwset > software write.
      if from_hw.reg4.field1.clr = '1' then
        regs.reg4.field1 <= '0';
      elsif from_hw.reg4.field1.set = '1' then
        regs.reg4.field1 <= '1';
      elsif wr_reg4 then
        regs.reg4.field1 <= lb_m2s.wdata(8);
      end if;

      -- Write response: ack a mapped register (reg1 acks with no effect, all
      -- its fields being sw ro), err an out-of-range or unmapped address.
      if lb_m2s.wen = '1' and wr_ack = '0' and wr_err = '0' then
        if not base_match(lb_m2s.address, G_BASE_ADDRESS, G_CHECK_BASE_ADDRESS) then
          hit := false;
        else
          hit := sel = C_ADDR_REG0(C_MODULE_ADDR_WIDTH-1 downto 0)
              or sel = C_ADDR_REG1(C_MODULE_ADDR_WIDTH-1 downto 0)
              or sel = C_ADDR_REG2(C_MODULE_ADDR_WIDTH-1 downto 0)
              or sel = C_ADDR_REG3(C_MODULE_ADDR_WIDTH-1 downto 0)
              or sel = C_ADDR_REG4(C_MODULE_ADDR_WIDTH-1 downto 0);
        end if;
        if hit then
          wr_ack <= '1';
        else
          wr_err <= '1';
        end if;
      end if;

      if rst = '1' then
        regs   <= C_PROTOTYPE_REGS_RESET;
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
        elsif sel = C_ADDR_REG0(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rdata(0)          <= regs.reg0.field0;
          rdata(2 downto 1) <= regs.reg0.field1;
          rd_ack <= '1';
        elsif sel = C_ADDR_REG1(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rdata(3 downto 0) <= regs.reg1.field0;
          rdata(4)          <= regs.reg1.field1;
          rdata(5)          <= regs.reg1.field2;
          rd_ack <= '1';
        elsif sel = C_ADDR_REG2(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rd_ack <= '1';                            -- reg2.field0 sw wo: reads 0
        elsif sel = C_ADDR_REG3(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rdata(7 downto 0) <= regs.reg3.field0;
          rd_ack <= '1';
        elsif sel = C_ADDR_REG4(C_MODULE_ADDR_WIDTH-1 downto 0) then
          rdata(3 downto 0) <= regs.reg4.field0;
          rdata(8)          <= regs.reg4.field1;
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

  to_hw.reg0.field0 <= regs.reg0.field0;
  to_hw.reg0.field1 <= regs.reg0.field1;
  to_hw.reg2.field0 <= regs.reg2.field0;
  to_hw.reg4.field0 <= regs.reg4.field0;
  to_hw.reg4.field1 <= regs.reg4.field1;

  lb_s2m.rdata <= rdata;
  lb_s2m.ack   <= wr_ack or rd_ack;
  lb_s2m.err   <= wr_err or rd_err;

end architecture rtl;
