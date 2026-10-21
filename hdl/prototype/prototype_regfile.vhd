-- Protocol-agnostic register file for the prototype module.
-- Speaks only the local bus; protocol wrappers (AXI, IPBus) instantiate it.
-- Exercises the core access-mode matrix: sw {rw,ro,wo,na} x hw {r,w,rw,na}
-- plus the we/wel/hwset/hwclr modifiers, the onread/onwrite software side
-- effects, the swmod/swacc/singlepulse pulse behaviours, and enumerated-value
-- field types. Registers/fields use generic names (reg0..reg11, field0..); see
-- prototype_regfile_pkg.vhd.
--
-- Two clocked processes split the bus side: p_write owns register storage
-- (software writes, hardware-driven updates, and onread side effects, since all
-- modify state) and the write response; p_read owns the read mux and the read
-- response. Concurrent output assignments are grouped at the bottom of the file.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.prototype_localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_regfile is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true;
    G_MODULE_ADDR_WIDTH  : natural               := C_MODULE_ADDR_WIDTH;
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

  signal swmod_r9f0 : std_logic;        -- reg9.field0 swmod pulse (1 cycle)
  signal swacc_r9f1 : std_logic;        -- reg9.field1 swacc pulse (1 cycle)

begin

  rst <= (reset xor '1') when G_RESET_ACTIVE_LOW else reset;

  -- G_MODULE_ADDR_WIDTH must hold the registers and fit in the address.
  assert G_MODULE_ADDR_WIDTH >= C_MODULE_ADDR_WIDTH and G_MODULE_ADDR_WIDTH <= 32
    report "G_MODULE_ADDR_WIDTH must be from C_MODULE_ADDR_WIDTH ("
           & natural'image(C_MODULE_ADDR_WIDTH) & ") to 32"
    severity failure;

  -- The base address must be a multiple of the size of the address range.
  assert (not G_CHECK_BASE_ADDRESS)
      or (G_BASE_ADDRESS(G_MODULE_ADDR_WIDTH-1 downto 0) = 0)
    report "G_BASE_ADDRESS must be aligned to 2**G_MODULE_ADDR_WIDTH bytes"
    severity failure;

  -- Register storage and write response. Single driver of `regs`: software
  -- writes, hardware updates, and onread side effects all live here. Each
  -- multi-source field uses an if/elsif chain so the documented precedence
  -- (provisional, since `precedence` is deferred) reads top-to-bottom:
  --   hwclr > hwset > hardware we/wel write > software write.
  p_write : process (clk) is
    variable reg_offset : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0);
    variable mapped     : boolean;     -- a register sits at this address
    variable sw_write   : boolean;     -- a new software write to a register
    -- p_write is the single driver of `regs`, so the onread side effects (which
    -- modify storage on a software read) are applied here too; this flags a
    -- new software read from a register.
    variable rd_service : boolean;
  begin
    if rising_edge(clk) then
      wr_ack <= '0';
      wr_err <= '0';

      -- A software access only takes effect on the cycle it is first seen
      -- (wr_ack/rd_err/... still low). The master holds the request until it
      -- observes the response, so these guards keep the effect single-shot.
      reg_offset := lb_m2s.address(C_MODULE_ADDR_WIDTH-1 downto 0);
      mapped     := base_match(lb_m2s.address, G_BASE_ADDRESS, G_CHECK_BASE_ADDRESS,
                               G_MODULE_ADDR_WIDTH)
                    and not above_registers(lb_m2s.address, G_MODULE_ADDR_WIDTH)
                    and is_mapped(reg_offset);
      sw_write   := lb_m2s.wen = '1' and wr_ack = '0' and wr_err = '0' and mapped;
      rd_service := lb_m2s.ren = '1' and rd_ack = '0' and rd_err = '0' and mapped;

      -- reg0: sw rw, hw r
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG0) then
        regs.reg0.field0 <= lb_m2s.wdata(0);
        regs.reg0.field1 <= lb_m2s.wdata(2 downto 1);
      end if;

      -- reg2.field0: sw wo, hw r (drives hardware, reads back 0)
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG2) then
        regs.reg2.field0 <= lb_m2s.wdata(0);
      end if;

      -- reg3.field0: sw rw, hw na
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG3) then
        regs.reg3.field0 <= lb_m2s.wdata(7 downto 0);
      end if;

      -- reg1: sw ro, hardware-driven.
      if from_hw.reg1.field0.we = '1' then          -- field0: hw w, we
        regs.reg1.field0 <= from_hw.reg1.field0.value;
      end if;
      if from_hw.reg1.field2.wel = '0' then          -- field2: hw w, active-low we
        regs.reg1.field2 <= from_hw.reg1.field2.value;
      end if;

      -- reg4.field0: hardware we write wins over software write.
      if from_hw.reg4.field0.we = '1' then
        regs.reg4.field0 <= from_hw.reg4.field0.value;
      elsif sw_write and reg_addr_match(reg_offset, C_ADDR_REG4) then
        regs.reg4.field0 <= lb_m2s.wdata(3 downto 0);
      end if;

      -- reg4.field1: hwclr > hwset > software write.
      if from_hw.reg4.field1.clr = '1' then
        regs.reg4.field1 <= '0';
      elsif from_hw.reg4.field1.set = '1' then
        regs.reg4.field1 <= '1';
      elsif sw_write and reg_addr_match(reg_offset, C_ADDR_REG4) then
        regs.reg4.field1 <= lb_m2s.wdata(8);
      end if;

      -- reg5: sw rw, hw r. Plain on write; the onread effect (below) acts on a
      -- software read, not a write.
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG5) then
        regs.reg5.field0 <= lb_m2s.wdata(3 downto 0);
        regs.reg5.field1 <= lb_m2s.wdata(7 downto 4);
      end if;

      -- reg6: onwrite write-1 effects, with stored value f and write data w.
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG6) then
        regs.reg6.field0 <= regs.reg6.field0 or lb_m2s.wdata(3 downto 0);        -- woset
        regs.reg6.field1 <= regs.reg6.field1 and not lb_m2s.wdata(7 downto 4);   -- woclr
        regs.reg6.field2 <= regs.reg6.field2 xor lb_m2s.wdata(11 downto 8);      -- wot
      end if;

      -- reg7: onwrite write-0 effects (the write-1 family with w inverted).
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG7) then
        regs.reg7.field0 <= regs.reg7.field0 or not lb_m2s.wdata(3 downto 0);    -- wzs
        regs.reg7.field1 <= regs.reg7.field1 and lb_m2s.wdata(7 downto 4);       -- wzc
        regs.reg7.field2 <= regs.reg7.field2 xor not lb_m2s.wdata(11 downto 8);  -- wzt
      end if;

      -- reg8: onwrite whole-field effects (data-independent).
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG8) then
        regs.reg8.field0 <= (others => '0');   -- wclr
        regs.reg8.field1 <= (others => '1');   -- wset
      end if;

      -- reg9: sw rw, hw r. Plain storage; swmod/swacc strobes generated below.
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG9) then
        regs.reg9.field0 <= lb_m2s.wdata(3 downto 0);
        regs.reg9.field1 <= lb_m2s.wdata(7 downto 4);
      end if;

      -- reg10.field0: singlepulse. Default-clear every cycle, so a software
      -- write surfaces to hardware as a single-cycle pulse and then self-clears.
      regs.reg10.field0 <= (others => '0');
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG10) then
        regs.reg10.field0 <= lb_m2s.wdata(3 downto 0);
      end if;

      -- reg11.field0: sw rw, hw r. Stored as the enum type; the bus value is
      -- converted to the enum on write and back to bits on read.
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG11) then
        regs.reg11.field0 <= to_reg11_field0(lb_m2s.wdata(1 downto 0));
      end if;

      -- reg5 onread effects: applied on the cycle the software read is serviced.
      -- The read returns the pre-effect value; storage updates here on the same
      -- edge.
      if rd_service and reg_addr_match(reg_offset, C_ADDR_REG5) then
        regs.reg5.field0 <= (others => '0');   -- onread rclr
        regs.reg5.field1 <= (others => '1');   -- onread rset
      end if;

      -- reg9 software-access strobes: swmod pulses when software modifies
      -- field0 (a write), swacc pulses on any software access (read or write).
      swmod_r9f0 <= '0';
      swacc_r9f1 <= '0';
      if sw_write and reg_addr_match(reg_offset, C_ADDR_REG9) then
        swmod_r9f0 <= '1';
        swacc_r9f1 <= '1';
      elsif rd_service and reg_addr_match(reg_offset, C_ADDR_REG9) then
        swacc_r9f1 <= '1';
      end if;

      -- Write response: ack a write to a register (reg1 acks with no effect, all
      -- its fields being sw ro), err a write to any other address.
      if lb_m2s.wen = '1' and wr_ack = '0' and wr_err = '0' then
        if mapped then
          wr_ack <= '1';
        else
          wr_err <= '1';
        end if;
      end if;

      if rst = '1' then
        regs       <= C_PROTOTYPE_REGS_RESET;
        wr_ack     <= '0';
        wr_err     <= '0';
        swmod_r9f0 <= '0';
        swacc_r9f1 <= '0';
      end if;
    end if;
  end process p_write;

  -- Read mux and read response. The onread side effects live in p_write (sole
  -- driver of `regs`); this process only selects read data and the response.
  -- Reads of non-readable fields (sw wo / na) return 0 and ack; err is reserved
  -- for address-decode failures, matching SystemRDL and the legacy bus PIFs.
  p_read : process (clk) is
    variable reg_offset : std_logic_vector(C_MODULE_ADDR_WIDTH-1 downto 0);
    variable mapped     : boolean;     -- a register sits at this address
  begin
    if rising_edge(clk) then
      rd_ack <= '0';
      rd_err <= '0';

      if lb_m2s.ren = '1' and rd_ack = '0' and rd_err = '0' then
        rdata <= (others => '0');
        reg_offset := lb_m2s.address(C_MODULE_ADDR_WIDTH-1 downto 0);
        mapped     := base_match(lb_m2s.address, G_BASE_ADDRESS, G_CHECK_BASE_ADDRESS,
                                 G_MODULE_ADDR_WIDTH)
                      and not above_registers(lb_m2s.address, G_MODULE_ADDR_WIDTH)
                      and is_mapped(reg_offset);
        if not mapped then
          rd_err <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG0) then
          rdata(0)          <= regs.reg0.field0;
          rdata(2 downto 1) <= regs.reg0.field1;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG1) then
          rdata(3 downto 0) <= regs.reg1.field0;
          rdata(4)          <= from_hw.reg1.field1;  -- status field, not stored
          rdata(5)          <= regs.reg1.field2;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG2) then
          rd_ack <= '1';                            -- reg2.field0 sw wo: reads 0
        elsif reg_addr_match(reg_offset, C_ADDR_REG3) then
          rdata(7 downto 0) <= regs.reg3.field0;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG4) then
          rdata(3 downto 0) <= regs.reg4.field0;
          rdata(8)          <= regs.reg4.field1;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG5) then
          rdata(3 downto 0) <= regs.reg5.field0;
          rdata(7 downto 4) <= regs.reg5.field1;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG6) then
          rdata(3 downto 0)  <= regs.reg6.field0;
          rdata(7 downto 4)  <= regs.reg6.field1;
          rdata(11 downto 8) <= regs.reg6.field2;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG7) then
          rdata(3 downto 0)  <= regs.reg7.field0;
          rdata(7 downto 4)  <= regs.reg7.field1;
          rdata(11 downto 8) <= regs.reg7.field2;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG8) then
          rdata(3 downto 0) <= regs.reg8.field0;
          rdata(7 downto 4) <= regs.reg8.field1;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG9) then
          rdata(3 downto 0) <= regs.reg9.field0;
          rdata(7 downto 4) <= regs.reg9.field1;
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG10) then
          rdata(3 downto 0) <= regs.reg10.field0;  -- usually 0 (pulse self-cleared)
          rd_ack <= '1';
        elsif reg_addr_match(reg_offset, C_ADDR_REG11) then
          rdata(1 downto 0) <= to_slv(regs.reg11.field0);
          rd_ack <= '1';
        end if;
      end if;

      if rst = '1' then
        rdata  <= (others => '0');
        rd_ack <= '0';
        rd_err <= '0';
      end if;
    end if;
  end process p_read;

  -- Hardware-side outputs, one aggregate per register.
  to_hw.reg0 <= (field0 => regs.reg0.field0, field1 => regs.reg0.field1);
  to_hw.reg2 <= (field0 => regs.reg2.field0);
  to_hw.reg4 <= (field0 => regs.reg4.field0, field1 => regs.reg4.field1);
  to_hw.reg5 <= (field0 => regs.reg5.field0, field1 => regs.reg5.field1);
  to_hw.reg6 <= (field0 => regs.reg6.field0, field1 => regs.reg6.field1, field2 => regs.reg6.field2);
  to_hw.reg7 <= (field0 => regs.reg7.field0, field1 => regs.reg7.field1, field2 => regs.reg7.field2);
  to_hw.reg8 <= (field0 => regs.reg8.field0, field1 => regs.reg8.field1);
  to_hw.reg9 <= (field0 => (value => regs.reg9.field0, swmod => swmod_r9f0),
                 field1 => (value => regs.reg9.field1, swacc => swacc_r9f1));
  to_hw.reg10 <= (field0 => regs.reg10.field0);
  to_hw.reg11 <= (field0 => regs.reg11.field0);

  lb_s2m.rdata <= rdata;
  lb_s2m.ack   <= wr_ack or rd_ack;
  lb_s2m.err   <= wr_err or rd_err;

end architecture rtl;
