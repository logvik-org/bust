library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.module_name.all;

entity module_name_axi_pif is

  port (    -- register record signals
    axi_ro_regs : in  t_module_name_ro_regs;
    axi_rw_regs : out t_module_name_rw_regs;
    
    -- bus signals
    clk         : in  std_logic;
    areset_n    : in  std_logic;
    awaddr      : in  t_module_name_addr;
    awvalid     : in  std_logic;
    awready     : out std_logic;
    wdata       : in  t_module_name_data;
    wvalid      : in  std_logic;
    wready      : out std_logic;
    bresp       : out std_logic_vector(1 downto 0);
    bvalid      : out std_logic;
    bready      : in  std_logic;
    araddr      : in  t_module_name_addr;
    arvalid     : in  std_logic;
    arready     : out std_logic;
    rdata       : out t_module_name_data;
    rresp       : out std_logic_vector(1 downto 0);
    rvalid      : out std_logic;
    rready      : in  std_logic
    );
end module_name_axi_pif;

architecture behavior of module_name_axi_pif is

  -- internal signal for readback
  signal axi_rw_regs_i : t_module_name_rw_regs;
  
  -- internal bus signals for readback
  signal awaddr_i      : t_module_name_addr;
  signal awready_i     : std_logic;
  signal wready_i      : std_logic;
  signal bresp_i       : std_logic_vector(1 downto 0);
  signal bvalid_i      : std_logic;
  signal araddr_i      : t_module_name_addr;
  signal arready_i     : std_logic;
  signal rdata_i       : t_module_name_data;
  signal rresp_i       : std_logic_vector(1 downto 0);
  signal rvalid_i      : std_logic;
  
  signal slv_reg_rden : std_logic;
  signal slv_reg_wren : std_logic;
  signal reg_data_out : t_module_name_data;
  -- signal byte_index   : integer; -- unused
  
begin

  axi_rw_regs <= axi_rw_regs_i;

  awready <= awready_i;
  wready  <= wready_i;
  bresp   <= bresp_i;
  bvalid  <= bvalid_i;
  arready <= arready_i;
  rdata   <= rdata_i;
  rresp   <= rresp_i;
  rvalid  <= rvalid_i;
  
  p_awready : process(clk);
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        awready_i <= '0';
      elsif (awready_i = '0' and awvalid = '1' and wvalid = '1') then
        awready_i <= '1';
      else
        awready_i <= '0';
      end if;
    end if;
  end process p_awready;

  p_awaddr : process(clk);
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        awaddr_i <= (others => '0');
      elsif (awready_i = '0' and awvalid = '1' and wvalid = '1') then
        awaddr_i <= awaddr;
      end if;
    end if;
  end process p_awaddr;

  p_wready : process(clk);
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        wready_i <= '0';
      elsif (wready_i = '0' and awvalid = '1' and wvalid = '1') then
        wready_i <= '1';
      else
        wready_i <= '0';
      end if;
    end if;
  end process p_wready;

  slv_reg_wren <= wready_i and wvalid and awready_i and awvalid;

  p_mm_select_write : process(clk);
  begin
    if areset_n = '0' then
      axi_rw_regs_i.reg0.run <= '0';
      axi_rw_regs_i.reg0.test_word <= (others => '0');
      axi_rw_regs_i.reg1 <= (others => '0');
      axi_rw_regs_i.reg2 <= '0';
      
    elsif rising_edge(clk) then
      if (slv_reg_wren = '1') then

        case awaddr_i is
          when C_ADDR_REG0 =>

            axi_rw_regs_i.reg0.run <= wdata(0);
            axi_rw_regs_i.reg0.test_word <= wdata(8 downto 1);

          when C_ADDR_REG1 =>

            axi_rw_regs_i.reg1 <= wdata;

          when C_ADDR_REG2 =>

            axi_rw_regs_i.reg2 <= wdata(0);

          when others =>
            null;

        end case;
      end if;
    end if;
  end process p_mm_select_write;

  p_write_response : process(clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        bvalid_i <= '0';
        bresp_i  <= "00";
      elsif (awready_i = '1' and awvalid = '1' and wready_i = '1' and wvalid = '1' and bvalid_i = '0') then
        bvalid_i <= '1';
        bresp_i  <= "00";
      elsif (bready = '1' and bvalid_i = '1') then
        bvalid_i <= '0';
      end if;
    end if;
  end process p_write_response;

  p_arready : process(clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        arready_i <= '0';
        araddr_i  <= (others => '0';
      elsif (arready_i = '0' and arvalid = '1') then
        arready_i <= '1';
        araddr_i  <= araddr;
      else
        arready_i <= '0';
      end if;
    end if;
  end process p_arready;

  p_arvalid : process(clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        rvalid_i <= '0';
        rresp_i  <= "00";
      elsif (arready_i = '1' and arvalid = '1' and rvalid_i = '0') then
        rvalid_i <= '1';
        rresp_i  <= "00";
      elsif (rvalid_i = '1' and rready = '1') then
        rvalid_i <= '0';
      end if;
    end if;
  end process p_arvalid;

  slv_reg_rden <= arready_i and arvalid and (not rvalid_i);

  p_mm_select_read : process (all)
  begin

    reg_data_out <= (others => '0');

    case aradrr_i is

      when C_ADDR_REG0 =>

        reg_data_out(0) <= axi_rw_regs_i.reg0.run;
        reg_data_out(8 downto 1) <= axi_rw_regs_i.reg0.test_word;

      when C_ADDR_REG1 =>

        reg_data_out <= axi_rw_regs_i.reg1;

      when C_ADDR_REG2 =>

        reg_data_out(0) <= axi_rw_regs_i.reg2;

      when C_ADDR_REG3 =>

        reg_data_out <= axi_ro_regs_i.reg3;

      when C_ADDR_REG4 =>

        reg_data_out(5 downto 0) <= axi_ro_regs_i.reg4.test;
        reg_data_out(6) <= axi_ro_regs_i.reg4.test2;

      when others =>
        null;

    end case;
  end process p_mm_select_read;

  p_output : process(clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        rdata_i <= (others => '0');
      elsif (slv_reg_rden = '1') then
        rdata_i <= reg_data_out;
      end if;
    end if;
  end process p_arvalid;

end behavior;