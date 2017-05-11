-------------------------------------------------------------------------------
--!@file        axi_module_name_reg.vhd
--!@author      author_name
--!@brief       module for handling the AXI signaling and registers
--!
--!
-------------------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.module_name_pkg.all;

--! AXI Register handling module
entity module_name_axi_handler is
  port (
    axi_ro_regs : in  t_module_name_ro_regs;
    axi_rw_regs : out t_module_name_rw_regs;
    --! global clock signal
    clk         : in  std_logic;
    --! global reset signal. this signal is active low
    areset_n    : in  std_logic;
    --! write address (issued by master, acceped by slave)
    awaddr      : in  t_module_name_addr;
    --! write address valid. this signal indicates that the master signaling
    --! valid write address and control information.
    awvalid     : in  std_logic;
    --! write address ready. this signal indicates that the slave is ready
    --! to accept an address and associated control signals.
    awready     : out std_logic;
    --! write data (issued by master, acceped by slave) 
    wdata       : in  t_module_name_data;
    --! write valid. this signal indicates that valid write
    --! data and strobes are available.
    wvalid      : in  std_logic;
    --! write ready. this signal indicates that the slave
    --! can accept the write data.
    wready      : out std_logic;
    --! write response. this signal indicates the status
    --! of the write transaction.
    bresp       : out std_logic_vector(1 downto 0);
    --! write response valid. this signal indicates that the channel
    --! is signaling a valid write response.
    bvalid      : out std_logic;
    --! response ready. this signal indicates that the master
    --! can accept a write response.
    bready      : in  std_logic;
    --! read address (issued by master, acceped by slave)
    araddr      : in  t_module_name_addr;
    --! read address valid. this signal indicates that the channel
    --! is signaling valid read address and control information.
    arvalid     : in  std_logic;
    --! read address ready. this signal indicates that the slave is
    --! ready to accept an address and associated control signals.
    arready     : out std_logic;
    --! read data (issued by slave)
    rdata       : out t_module_name_data;
    --! read response. this signal indicates the status of the
    --! read transfer.
    rresp       : out std_logic_vector(1 downto 0);
    --! read valid. this signal indicates that the channel is
    --! signaling the required read data.
    rvalid      : out std_logic;
    -- read ready. this signal indicates that the master can
    -- accept the read data and response information.
    rready      : in  std_logic
    );
end module_name_axi_handler;

architecture behavior of module_name_axi_handler is

  --! internal signal for readback
  signal axi_rw_regs_i : t_module_name_rw_regs;

  -- axi4lite signals
  signal awaddr_i  : t_module_name_addr;
  signal awready_i : std_logic;
  signal wready_i  : std_logic;
  signal bresp_i   : std_logic_vector(1 downto 0);
  signal bvalid_i  : std_logic;
  signal araddr_i  : t_module_name_addr;
  signal arready_i : std_logic;
  signal rdata_i   : t_module_name_data;
  signal rresp_i   : std_logic_vector(1 downto 0);
  signal rvalid_i  : std_logic;

  ------------------------------------------------
  ---- signals for user logic register space example
  --------------------------------------------------
  signal slv_reg_rden : std_logic;
  signal slv_reg_wren : std_logic;
  signal reg_data_out : t_module_name_data;
  signal byte_index   : integer;

begin
  axi_rw_regs <= axi_rw_regs_i;

  -- i/o connections assignments
  awready <= awready_i;
  wready  <= wready_i;
  bresp   <= bresp_i;
  bvalid  <= bvalid_i;
  arready <= arready_i;
  rdata   <= rdata_i;
  rresp   <= rresp_i;
  rvalid  <= rvalid_i;

  -----------------------------------------------------------------------------
  --! @brief implement awready_i generation
  --! @details awready_i is asserted for one clk clock cycle when both
  --! awvalid and wvalid are asserted. awready_i is
  --! de-asserted when reset is low.
  -----------------------------------------------------------------------------
  p_awready : process (clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        awready_i <= '0';
      else
        if (awready_i = '0' and awvalid = '1' and wvalid = '1') then
          -- slave is ready to accept write address when
          -- there is a valid write address and write data
          -- on the write address and data bus. this design 
          -- expects no outstanding transactions. 
          awready_i <= '1';
        else
          awready_i <= '0';
        end if;
      end if;
    end if;
  end process;

  -----------------------------------------------------------------------------
  --! @brief implement awaddr_i latching
  --! @details this process is used to latch the address when both 
  --! awvalid and wvalid are valid.
  -----------------------------------------------------------------------------
  p_awaddr : process (clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        awaddr_i <= (others => '0');
      else
        if (awready_i = '0' and awvalid = '1' and wvalid = '1') then
          -- write address latching
          awaddr_i <= awaddr;
        end if;
      end if;
    end if;
  end process;

  -----------------------------------------------------------------------------
  --! @brief implement wready_i generation
  --! @details wready_i is asserted for one clk clock cycle when both
  --! awvalid and wvalid are asserted. wready_i is 
  --! de-asserted when reset is low.
  -----------------------------------------------------------------------------
  p_wready : process (clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        wready_i <= '0';
      else
        if (wready_i = '0' and wvalid = '1' and awvalid = '1') then
          -- slave is ready to accept write data when 
          -- there is a valid write address and write data
          -- on the write address and data bus. this design 
          -- expects no outstanding transactions.           
          wready_i <= '1';
        else
          wready_i <= '0';
        end if;
      end if;
    end if;
  end process;

  -----------------------------------------------------------------------------
  --! @brief implement memory mapped register select and write logic generation
  --! @details the write data is accepted and written to memory mapped registers when
  --! awready_i, wvalid, wready_i and wvalid are asserted. write strobes are
  --! NOT used to
  --! select byte enables of slave registers while writing.
  --! these registers are cleared/defaulted when reset (active low) is applied.
  --! slave register write enable is asserted when valid address and data are available
  --! and the slave is ready to accept the write address and write data.
  -----------------------------------------------------------------------------
  slv_reg_wren <= wready_i and wvalid and awready_i and awvalid;

  p_mm_select_write : process (clk)
  begin
    if areset_n = '0' then
      axi_rw_regs_i.reg0.run       <= '0';
      axi_rw_regs_i.reg0.test_word <= 8X"0";
      axi_rw_regs_i.reg1           <= 16X"0";
      axi_rw_regs_i.reg2           <= '0';

    elsif rising_edge(clk) then
      if (slv_reg_wren = '1') then

        case awaddr_i is
          when C_addr_reg0 =>

            axi_rw_regs_i.reg0.run       <= wdata(0);
            axi_rw_regs_i.reg0.test_word <= wdata(8 downto 1);

          when C_addr_reg1 =>

            axi_rw_regs_i.reg1 <= wdata;

          when C_addr_reg2 =>

            axi_rw_regs_i.reg2 <= wdata(0);

          when others =>
            null;

        end case;
      end if;
    end if;
  end process;

  -----------------------------------------------------------------------------
  --! @brief implement write response logic generation
  --! @details the write response and response valid signals are asserted by the slave 
  --! when wready_i, wvalid, wready_i and wvalid are asserted.  
  --! this marks the acceptance of address and indicates the status of 
  --! write transaction.
  -----------------------------------------------------------------------------
  p_write_response : process (clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        bvalid_i <= '0';
        bresp_i  <= "00";               --need to work more on the responses
      else
        if (awready_i = '1' and awvalid = '1' and wready_i = '1' and wvalid = '1' and bvalid_i = '0') then
          bvalid_i <= '1';
          bresp_i  <= "00";
        elsif (bready = '1' and bvalid_i = '1') then  --check if bready is asserted while bvalid is high)
          bvalid_i <= '0';  -- (there is a possibility that bready is always asserted high)
        end if;
      end if;
    end if;
  end process;

  -----------------------------------------------------------------------------
  --! @brief implement arready_i generation
  --! @details arready_i is asserted for one clk clock cycle when
  --! arvalid is asserted. awready_i is 
  --! de-asserted when reset (active low) is asserted. 
  --! the read address is also latched when arvalid is 
  --! asserted. araddr_i is reset to zero on reset assertion.
  -----------------------------------------------------------------------------
  p_arready : process (clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        arready_i <= '0';
        araddr_i  <= (others => '1');
      else
        if (arready_i = '0' and arvalid = '1') then
          -- indicates that the slave has acceped the valid read address
          arready_i <= '1';
          -- read address latching 
          araddr_i  <= araddr;
        else
          arready_i <= '0';
        end if;
      end if;
    end if;
  end process;

  -----------------------------------------------------------------------------
  --! @brief implement axi_arvalid generation
  --! @details rvalid_i is asserted for one clk clock cycle when both 
  --! arvalid and arready_i are asserted. the slave registers 
  --! data are available on the rdata_i bus at this instance. the 
  --! assertion of rvalid_i marks the validity of read data on the 
  --! bus and rresp_i indicates the status of read transaction.rvalid_i 
  --! is deasserted on reset (active low). rresp_i and rdata_i are 
  --! cleared to zero on reset (active low).
  -----------------------------------------------------------------------------
  p_arvalid : process (clk)
  begin
    if rising_edge(clk) then
      if areset_n = '0' then
        rvalid_i <= '0';
        rresp_i  <= "00";
      else
        if (arready_i = '1' and arvalid = '1' and rvalid_i = '0') then
          -- valid read data is available at the read data bus
          rvalid_i <= '1';
          rresp_i  <= "00";             -- 'okay' response
        elsif (rvalid_i = '1' and rready = '1') then
          -- read data is accepted by the master
          rvalid_i <= '0';
        end if;
      end if;
    end if;
  end process;

  -----------------------------------------------------------------------------
  --! @brief implement memory mapped register select and read logic generation
  --! @details slave register read enable is asserted when valid address is available
  --! and the slave is ready to accept the read address.
  -----------------------------------------------------------------------------
  slv_reg_rden <= arready_i and arvalid and (not rvalid_i);

  p_mm_select_read : process (all)
  begin
    -- address decoding for reading registers
    reg_data_out <= (others => '0');
    case araddr_i is
      when C_addr_reg0 =>

        reg_data_out(0)          <= axi_rw_regs_i.reg0.run;
        reg_data_out(8 downto 1) <= axi_rw_regs_i.reg0.test_word;

      when C_addr_reg1 =>

        reg_data_out <= axi_rw_regs.reg1;

      when C_addr_reg2 =>

        reg_data_out(0) <= axi_rw_regs.reg2;

      when C_addr_reg3 =>
        reg_data_out <= axi_ro_regs.reg3;

      when others =>
        null;
    end case;
  end process;

  -----------------------------------------------------------------------------
  --! output register or memory read data
  -----------------------------------------------------------------------------
  p_output : process(clk) is
  begin
    if (rising_edge (clk)) then
      if (areset_n = '0') then
        rdata_i <= (others => '0');
      else
        if (slv_reg_rden = '1') then
          -- when there is a valid read address (arvalid) with 
          -- acceptance of read address by the slave (arready_i), 
          -- output the read dada 
          -- read address mux
          rdata_i <= reg_data_out;      -- register read data
        end if;
      end if;
    end if;
  end process;

end behavior;
