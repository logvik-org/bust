library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library bust;
use bust.axi_pkg.all;
use work.example_axi_pif_pkg.all;

entity example_axi_axi_pif is

  generic (
    -- AXI Bus Interface Generics
    g_axi_baseaddr        : std_logic_vector(31 downto 0) := (others => '0'));
  port (
    -- AXI Bus Interface Ports
    axi_rw_regs    : out t_example_axi_rw_regs    := c_example_axi_rw_regs;
    axi_ro_regs    : in  t_example_axi_ro_regs    := c_example_axi_ro_regs;
    axi_pulse_regs : out t_example_axi_pulse_regs := c_example_axi_pulse_regs;

    -- bus signals
    clk            : in  std_logic;
    areset_n       : in  std_logic;
    awaddr         : in  t_example_axi_addr;
    awvalid        : in  std_logic;
    awready        : out std_logic;
    wdata          : in  t_example_axi_data;
    wvalid         : in  std_logic;
    wready         : out std_logic;
    bresp          : out std_logic_vector(1 downto 0);
    bvalid         : out std_logic;
    bready         : in  std_logic;
    araddr         : in  t_example_axi_addr;
    arvalid        : in  std_logic;
    arready        : out std_logic;
    rdata          : out t_example_axi_data;
    rresp          : out std_logic_vector(1 downto 0);
    rvalid         : out std_logic;
    rready         : in  std_logic
    );
end example_axi_axi_pif;

architecture behavior of example_axi_axi_pif is

  constant C_BASEADDR : t_axi_addr := g_axi_baseaddr;

  -- internal signal for readback
  signal axi_rw_regs_i    : t_example_axi_rw_regs := c_example_axi_rw_regs;
  signal axi_pulse_regs_i : t_example_axi_pulse_regs := c_example_axi_pulse_regs;
  signal axi_pulse_regs_cycle : t_example_axi_pulse_regs := c_example_axi_pulse_regs;

  -- internal bus signals for readback
  signal awaddr_i      : t_example_axi_addr;
  signal awready_i     : std_logic;
  signal wready_i      : std_logic;
  signal bresp_i       : std_logic_vector(1 downto 0);
  signal bvalid_i      : std_logic;
  signal araddr_i      : t_example_axi_addr;
  signal arready_i     : std_logic;
  signal rdata_i       : t_example_axi_data;
  signal rresp_i       : std_logic_vector(1 downto 0);
  signal rvalid_i      : std_logic;

  signal slv_reg_rden : std_logic;
  signal slv_reg_wren : std_logic;
  signal reg_data_out : t_example_axi_data;
  -- signal byte_index   : integer; -- unused

begin

  axi_rw_regs <= axi_rw_regs_i;
  axi_pulse_regs <= axi_pulse_regs_i;

  awready <= awready_i;
  wready  <= wready_i;
  bresp   <= bresp_i;
  bvalid  <= bvalid_i;
  arready <= arready_i;
  rdata   <= rdata_i;
  rresp   <= rresp_i;
  rvalid  <= rvalid_i;

  p_awready : process(clk, areset_n)
  begin
    if areset_n = '0' then
      awready_i <= '0';
    elsif rising_edge(clk) then
      if (awready_i = '0' and awvalid = '1'  and wvalid = '1') then
        awready_i <= '1';
      else
        awready_i <= '0';
      end if;
    end if;
  end process p_awready;

  p_awaddr : process(clk, areset_n)
  begin
    if areset_n = '0' then
      awaddr_i <= (others => '0');
    elsif rising_edge(clk) then
      if (awready_i = '0' and awvalid = '1' and wvalid = '1') then
        awaddr_i <= awaddr;
      end if;
    end if;
  end process p_awaddr;

  p_wready : process(clk, areset_n)
  begin
    if areset_n = '0' then
      wready_i <= '0';
    elsif rising_edge(clk) then
      if (wready_i = '0' and awvalid = '1' and wvalid = '1') then
        wready_i <= '1';
      else
        wready_i <= '0';
      end if;
    end if;
  end process p_wready;

  slv_reg_wren <= wready_i and wvalid and awready_i and awvalid;

  p_mm_select_write : process(clk, areset_n)
  begin
    if areset_n = '0' then

      axi_rw_regs_i <= c_example_axi_rw_regs;
      axi_pulse_regs_cycle <= c_example_axi_pulse_regs;

    elsif rising_edge(clk) then

      -- Return PULSE registers to reset value every clock cycle
      axi_pulse_regs_cycle <= c_example_axi_pulse_regs;


      if (slv_reg_wren = '1') then

          if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG0), 32) then

            axi_rw_regs_i.reg0 <= wdata(0);

          end if;

          if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG1), 32) then

            axi_rw_regs_i.reg1 <= wdata(0);

          end if;

          if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG3), 32) then

            axi_rw_regs_i.reg3 <= wdata(7 downto 0);

          end if;

          if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG5), 32) then

            axi_rw_regs_i.reg5 <= wdata;

          end if;

          if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG7), 32) then

            axi_rw_regs_i.reg7.field0 <= wdata(0);
            axi_rw_regs_i.reg7.field1 <= wdata(4 downto 1);
            axi_rw_regs_i.reg7.field2 <= wdata(5);
            axi_rw_regs_i.reg7.field3 <= wdata(20 downto 6);

          end if;

          if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG9), 32) then

            axi_pulse_regs_cycle.reg9 <= wdata(0);

          end if;

          if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG10), 32) then

            axi_pulse_regs_cycle.reg10 <= wdata(3 downto 0);

          end if;

          if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG11), 32) then

            axi_pulse_regs_cycle.reg11.field0 <= wdata(14 downto 0);
            axi_pulse_regs_cycle.reg11.field1 <= wdata(15);

          end if;

      end if;

    end if;
  end process p_mm_select_write;

  p_pulse_reg9 : process(clk)
    variable cnt : natural range 0 to 3 := 0;
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        axi_pulse_regs_i.reg9 <= c_example_axi_pulse_regs.reg9;
      else
        if axi_pulse_regs_cycle.reg9 /= c_example_axi_pulse_regs.reg9 then
          cnt := 3;
          axi_pulse_regs_i.reg9 <= axi_pulse_regs_cycle.reg9;
        else
          if cnt > 0 then
            cnt := cnt - 1;
          else
            axi_pulse_regs_i.reg9 <= c_example_axi_pulse_regs.reg9;
          end if;
        end if;
      end if;
    end if;
  end process p_pulse_reg9;

  p_pulse_reg10 : process(clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        axi_pulse_regs_i.reg10 <= c_example_axi_pulse_regs.reg10;
      else
        if axi_pulse_regs_cycle.reg10 /= c_example_axi_pulse_regs.reg10 then
          axi_pulse_regs_i.reg10 <= axi_pulse_regs_cycle.reg10;
        else
          axi_pulse_regs_i.reg10 <= c_example_axi_pulse_regs.reg10;
        end if;
      end if;
    end if;
  end process p_pulse_reg10;

  p_pulse_reg11 : process(clk)
    variable cnt : natural range 0 to 49 := 0;
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        axi_pulse_regs_i.reg11 <= c_example_axi_pulse_regs.reg11;
      else
        if axi_pulse_regs_cycle.reg11 /= c_example_axi_pulse_regs.reg11 then
          cnt := 49;
          axi_pulse_regs_i.reg11 <= axi_pulse_regs_cycle.reg11;
        else
          if cnt > 0 then
            cnt := cnt - 1;
          else
            axi_pulse_regs_i.reg11 <= c_example_axi_pulse_regs.reg11;
          end if;
        end if;
      end if;
    end if;
  end process p_pulse_reg11;

  p_write_response : process(clk, areset_n)
  begin
    if areset_n = '0' then
      bvalid_i <= '0';
      bresp_i  <= "00";
    elsif rising_edge(clk) then
      if (awready_i = '1' and awvalid = '1' and wready_i = '1' and wvalid = '1' and bvalid_i = '0') then
        bvalid_i <= '1';
        bresp_i  <= "00";
      elsif (bready = '1' and bvalid_i = '1') then
        bvalid_i <= '0';
      end if;
    end if;
  end process p_write_response;

  p_arready : process(clk, areset_n)
  begin
    if areset_n = '0' then
      arready_i <= '0';
      araddr_i  <= (others => '0');
    elsif rising_edge(clk) then
      if (arready_i = '0' and arvalid = '1') then
        arready_i <= '1';
        araddr_i  <= araddr;
      else
        arready_i <= '0';
      end if;
    end if;
  end process p_arready;

  p_arvalid : process(clk, areset_n)
  begin
    if areset_n = '0' then
      rvalid_i <= '0';
      rresp_i  <= "00";
    elsif rising_edge(clk) then
      if (arready_i = '1' and arvalid = '1' and rvalid_i = '0') then
        rvalid_i <= '1';
        rresp_i  <= "00";
      elsif (rvalid_i = '1' and rready = '1') then
        rvalid_i <= '0';
      end if;
    end if;
  end process p_arvalid;

  slv_reg_rden <= arready_i and arvalid and (not rvalid_i);

  p_mm_select_read : process(all)
  begin

    reg_data_out <= (others => '0');

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG0), 32) then

      reg_data_out(0) <= axi_rw_regs_i.reg0;

    end if;

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG1), 32) then

      reg_data_out(0) <= axi_rw_regs_i.reg1;

    end if;

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG2), 32) then

      reg_data_out(0) <= axi_ro_regs.reg2;

    end if;

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG3), 32) then

      reg_data_out(7 downto 0) <= axi_rw_regs_i.reg3;

    end if;

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG4), 32) then

      reg_data_out(13 downto 0) <= axi_ro_regs.reg4;

    end if;

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG5), 32) then

      reg_data_out <= axi_rw_regs_i.reg5;

    end if;

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG6), 32) then

      reg_data_out <= axi_ro_regs.reg6;

    end if;

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG7), 32) then

      reg_data_out(0) <= axi_rw_regs_i.reg7.field0;
      reg_data_out(4 downto 1) <= axi_rw_regs_i.reg7.field1;
      reg_data_out(5) <= axi_rw_regs_i.reg7.field2;
      reg_data_out(20 downto 6) <= axi_rw_regs_i.reg7.field3;

    end if;

    if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_REG8), 32) then

      reg_data_out(0) <= axi_ro_regs.reg8.field0;
      reg_data_out(19 downto 1) <= axi_ro_regs.reg8.field1;
      reg_data_out(20) <= axi_ro_regs.reg8.field2;
      reg_data_out(23 downto 21) <= axi_ro_regs.reg8.field3;

    end if;

  end process p_mm_select_read;

  p_output : process(clk, areset_n)
  begin
    if areset_n = '0' then
      rdata_i <= (others => '0');
    elsif rising_edge(clk) then
      if (slv_reg_rden = '1') then
        rdata_i <= reg_data_out;
      end if;
    end if;
  end process p_output;

end behavior;
