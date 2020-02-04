library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library ipbus;
use ipbus.ipbus.all;
use work.example_ipbus_pif_pkg.all;

entity example_ipbus_ipb_pif is

  generic (
    -- IPBUS Bus Interface Generics
    g_ipb_baseaddr        : std_logic_vector(31 downto 0) := (others => '0'));
  port (
    -- IPBUS Bus Interface Ports
    ipb_rw_regs    : out t_example_ipbus_rw_regs    := c_example_ipbus_rw_regs;
    ipb_ro_regs    : in  t_example_ipbus_ro_regs    := c_example_ipbus_ro_regs;
    ipb_pulse_regs : out t_example_ipbus_pulse_regs := c_example_ipbus_pulse_regs;

    -- bus signals
    clk            : in  std_logic;
    reset          : in  std_logic;
    ipb_in         : in  ipb_wbus;
    ipb_out        : out ipb_rbus
    );
end example_ipbus_ipb_pif;

architecture behavior of example_ipbus_ipb_pif is

  constant C_BASEADDR : std_logic_vector(31 downto 0) := g_ipb_baseaddr;

  -- internal signal for readback
  signal ipb_rw_regs_i    : t_example_ipbus_rw_regs := c_example_ipbus_rw_regs;
  signal ipb_pulse_regs_i : t_example_ipbus_pulse_regs := c_example_ipbus_pulse_regs;
  signal ipb_pulse_regs_cycle : t_example_ipbus_pulse_regs := c_example_ipbus_pulse_regs;

  signal ipb_out_i      : ipb_rbus;
  signal reg_rden       : std_logic := '0';
  signal reg_wren       : std_logic := '0';
  signal wr_ack, rd_ack : std_logic := '0';
  signal wr_err, rd_err : std_logic := '0';
  signal reg_data_out   : t_example_ipbus_data;

begin

  ipb_out <= ipb_out_i;
  ipb_rw_regs <= ipb_rw_regs_i;
  ipb_pulse_regs <= ipb_pulse_regs_i;

  reg_wren <= (ipb_in.ipb_strobe and ipb_in.ipb_write) and not (wr_ack or wr_err or ipb_out_i.ipb_ack or ipb_out_i.ipb_err);

  p_write : process(clk)
  begin
    if rising_edge(clk) then
      if reset = '1' then

        ipb_rw_regs_i <= c_example_ipbus_rw_regs;
        ipb_pulse_regs_cycle <= c_example_ipbus_pulse_regs;
        wr_ack <= '0';
        wr_err <= '0';

      else

        -- Return PULSE registers to reset value every clock cycle
        ipb_pulse_regs_cycle <= c_example_ipbus_pulse_regs;

        wr_ack <= '0';
        wr_err <= '0';

        if (reg_wren) then

          if unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG0), 32) then

            ipb_rw_regs_i.reg0 <= ipb_in.ipb_wdata(0);
            wr_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG1), 32) then

            ipb_rw_regs_i.reg1 <= ipb_in.ipb_wdata(0);
            wr_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG3), 32) then

            ipb_rw_regs_i.reg3 <= ipb_in.ipb_wdata(7 downto 0);
            wr_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG5), 32) then

            ipb_rw_regs_i.reg5 <= ipb_in.ipb_wdata;
            wr_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG7), 32) then

            ipb_rw_regs_i.reg7.field0 <= ipb_in.ipb_wdata(0);
            ipb_rw_regs_i.reg7.field1 <= ipb_in.ipb_wdata(4 downto 1);
            ipb_rw_regs_i.reg7.field2 <= ipb_in.ipb_wdata(5);
            ipb_rw_regs_i.reg7.field3 <= ipb_in.ipb_wdata(20 downto 6);
            wr_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG9), 32) then

            ipb_pulse_regs_cycle.reg9 <= ipb_in.ipb_wdata(0);
            wr_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG10), 32) then

            ipb_pulse_regs_cycle.reg10 <= ipb_in.ipb_wdata(3 downto 0);
            wr_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG11), 32) then

            ipb_pulse_regs_cycle.reg11.field0 <= ipb_in.ipb_wdata(14 downto 0);
            ipb_pulse_regs_cycle.reg11.field1 <= ipb_in.ipb_wdata(15);
            wr_ack <= '1';

          else

            wr_err <= '1';

          end if;
        end if;
      end if;
    end if;
  end process p_write;

  p_pulse_reg9 : process(clk)
  variable cnt : natural range 0 to 3 := 0;
  begin
    if rising_edge(clk) then
      if reset = '1' then
        ipb_pulse_regs_i.reg9 <= c_example_ipbus_pulse_regs.reg9;
      else
        if ipb_pulse_regs_cycle.reg9 /= c_example_ipbus_pulse_regs.reg9 then
          cnt := 3;
          ipb_pulse_regs_i.reg9 <= ipb_pulse_regs_cycle.reg9;
        else
          if cnt > 0 then
            cnt := cnt - 1;
          else
            ipb_pulse_regs_i.reg9 <= c_example_ipbus_pulse_regs.reg9;
          end if;
        end if;
      end if;
    end if;
  end process p_pulse_reg9;

  p_pulse_reg10 : process(clk)
  begin
    if rising_edge(clk) then
      if reset = '1' then
        ipb_pulse_regs_i.reg10 <= c_example_ipbus_pulse_regs.reg10;
      else
        if ipb_pulse_regs_cycle.reg10 /= c_example_ipbus_pulse_regs.reg10 then
          ipb_pulse_regs_i.reg10 <= ipb_pulse_regs_cycle.reg10;
        else
          ipb_pulse_regs_i.reg10 <= c_example_ipbus_pulse_regs.reg10;
        end if;
      end if;
    end if;
  end process p_pulse_reg10;

  p_pulse_reg11 : process(clk)
  variable cnt : natural range 0 to 49 := 0;
  begin
    if rising_edge(clk) then
      if reset = '1' then
        ipb_pulse_regs_i.reg11 <= c_example_ipbus_pulse_regs.reg11;
      else
        if ipb_pulse_regs_cycle.reg11 /= c_example_ipbus_pulse_regs.reg11 then
          cnt := 49;
          ipb_pulse_regs_i.reg11 <= ipb_pulse_regs_cycle.reg11;
        else
          if cnt > 0 then
            cnt := cnt - 1;
          else
            ipb_pulse_regs_i.reg11 <= c_example_ipbus_pulse_regs.reg11;
          end if;
        end if;
      end if;
    end if;
  end process p_pulse_reg11;


  reg_rden <= (ipb_in.ipb_strobe and (not ipb_in.ipb_write)) and not (rd_ack or rd_err or ipb_out_i.ipb_ack or ipb_out_i.ipb_err);

  p_read : process(clk)
  begin
    if rising_edge(clk) then
      if reset = '1' then
        reg_data_out <= (others => '0');
        rd_ack <= '0';
        rd_err <= '0';
      else

        -- default values
        rd_ack <= '0';
        rd_err <= '0';

        if (reg_rden) then

          if unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG0), 32) then

            reg_data_out(0) <= ipb_rw_regs_i.reg0;
            rd_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG1), 32) then

            reg_data_out(0) <= ipb_rw_regs_i.reg1;
            rd_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG2), 32) then

            reg_data_out(0) <= ipb_ro_regs.reg2;
            rd_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG3), 32) then

            reg_data_out(7 downto 0) <= ipb_rw_regs_i.reg3;
            rd_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG4), 32) then

            reg_data_out(13 downto 0) <= ipb_ro_regs.reg4;
            rd_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG5), 32) then

            reg_data_out <= ipb_rw_regs_i.reg5;
            rd_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG6), 32) then

            reg_data_out <= ipb_ro_regs.reg6;
            rd_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG7), 32) then

            reg_data_out(0) <= ipb_rw_regs_i.reg7.field0;
            reg_data_out(4 downto 1) <= ipb_rw_regs_i.reg7.field1;
            reg_data_out(5) <= ipb_rw_regs_i.reg7.field2;
            reg_data_out(20 downto 6) <= ipb_rw_regs_i.reg7.field3;
            rd_ack <= '1';

          elsif unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG8), 32) then

            reg_data_out(0) <= ipb_ro_regs.reg8.field0;
            reg_data_out(19 downto 1) <= ipb_ro_regs.reg8.field1;
            reg_data_out(20) <= ipb_ro_regs.reg8.field2;
            reg_data_out(23 downto 21) <= ipb_ro_regs.reg8.field3;
            rd_ack <= '1';

          else

            reg_data_out <= 32X"DEADBEEF";
            rd_err <= '1';

          end if;
        end if;
      end if;
    end if;
  end process p_read;

  p_output : process(all)
  begin
    if reset = '1' then
      ipb_out_i.ipb_rdata <= (others => '0');
      ipb_out_i.ipb_ack <= '0';
      ipb_out_i.ipb_err <= '0';
    else
      ipb_out_i.ipb_rdata <= reg_data_out;
      ipb_out_i.ipb_ack <= '0';
      ipb_out_i.ipb_err <= '0';

      if (rd_ack or rd_err) then
        ipb_out_i.ipb_ack <= rd_ack;
        ipb_out_i.ipb_err <= rd_err;
      elsif (wr_ack or wr_err) then
        ipb_out_i.ipb_ack <= wr_ack;
        ipb_out_i.ipb_err <= wr_err;
      end if;

    end if;
  end process p_output;

end behavior;