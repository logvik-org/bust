library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library bust;
use bust.axi_pkg.all;
use work.example_axi_pif_pkg.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library bitvis_vip_axilite;
use bitvis_vip_axilite.axilite_bfm_pkg.all;

-------------------------------------------------------------------------------

entity example_axi_axi_pif_tb is

end entity example_axi_axi_pif_tb;

-------------------------------------------------------------------------------

architecture tb of example_axi_axi_pif_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  -- component generics
  constant g_axi_baseaddr   : std_logic_vector(31 downto 0) := 32X"FFAA0000";
  constant g_check_baseaddr : boolean                       := true;

  -- component ports
  signal axi_rw_regs    : t_example_axi_rw_regs    := c_example_axi_rw_regs;
  signal axi_ro_regs    : t_example_axi_ro_regs    := c_example_axi_ro_regs;
  signal axi_pulse_regs : t_example_axi_pulse_regs := c_example_axi_pulse_regs;
  signal axi_clk        : std_logic                   := '1';
  signal axi_areset_n   : std_logic                   := '1';
  signal axi_in         : t_axi_mosi;
  signal axi_out        : t_axi_miso;

  -- Bitvis UVVM AXILITE BFM
  constant data_width : natural := 32;
  constant addr_width : natural := 32;
  signal axilite_if : t_axilite_if(write_address_channel(awaddr(addr_width -1 downto 0)),
                                   write_data_channel(wdata(data_width -1 downto 0),
                                                      wstrb((data_width/8) -1 downto 0)),
                                   read_address_channel(araddr(addr_width -1 downto 0)),
                                   read_data_channel(rdata(data_width -1 downto 0))) := init_axilite_if_signals(data_width, addr_width);
  signal axilite_bfm_config : t_axilite_bfm_config := C_AXILITE_BFM_CONFIG_DEFAULT;

  -- Unused AXILITE signals
  signal dummy_arprot : std_logic_vector(2 downto 0);
  signal dummy_awprot : std_logic_vector(2 downto 0);
  signal dummy_wstrb  : std_logic_vector((data_width/8)-1 downto 0);

  function f_addr (
    BASE : std_logic_vector(31 downto 0);
    REG  : std_logic_vector(31 downto 0))
    return unsigned is
    variable tmp : unsigned(31 downto 0);
  begin  -- function f_addr
    tmp := unsigned(BASE);
    tmp := tmp + unsigned(REG);
    return tmp;
  end function f_addr;

begin  -- architecture tb

  axilite_bfm_config.clock_period      <= C_CLK_PERIOD;
  axilite_bfm_config.setup_time        <= C_CLK_PERIOD/8;
  axilite_bfm_config.hold_time         <= C_CLK_PERIOD/8;
  axilite_bfm_config.num_b_pipe_stages <= 0;

  axi_in.araddr  <= axilite_if.read_address_channel.araddr;
  dummy_arprot   <= axilite_if.read_address_channel.arprot;
  axi_in.arvalid <= axilite_if.read_address_channel.arvalid;
  axi_in.awaddr  <= axilite_if.write_address_channel.awaddr;
  dummy_awprot   <= axilite_if.write_address_channel.awprot;
  axi_in.awvalid <= axilite_if.write_address_channel.awvalid;
  axi_in.bready  <= axilite_if.write_response_channel.bready;
  axi_in.rready  <= axilite_if.read_data_channel.rready;
  axi_in.wdata   <= axilite_if.write_data_channel.wdata;
  dummy_wstrb    <= axilite_if.write_data_channel.wstrb;
  axi_in.wvalid  <= axilite_if.write_data_channel.wvalid;

  axilite_if.read_address_channel.arready  <= axi_out.arready;
  axilite_if.write_address_channel.awready <= axi_out.awready;
  axilite_if.write_response_channel.bresp  <= axi_out.bresp;
  axilite_if.write_response_channel.bvalid <= axi_out.bvalid;
  axilite_if.read_data_channel.rdata       <= axi_out.rdata;
  axilite_if.read_data_channel.rresp       <= axi_out.rresp;
  axilite_if.read_data_channel.rvalid      <= axi_out.rvalid;
  axilite_if.write_data_channel.wready     <= axi_out.wready;

  -- component instantiation
  DUT : entity work.example_axi_axi_pif
    generic map (
      g_axi_baseaddr      => g_axi_baseaddr,
      g_check_baseaddr    => g_check_baseaddr)
    port map (
      axi_rw_regs         => axi_rw_regs,
      axi_ro_regs         => axi_ro_regs,
      axi_pulse_regs      => axi_pulse_regs,
      clk                 => axi_clk,
      areset_n            => axi_areset_n,
      awaddr              => axi_in.awaddr(C_EXAMPLE_AXI_ADDR_WIDTH-1 downto 0),
      awvalid             => axi_in.awvalid,
      awready             => axi_out.awready,
      wdata               => axi_in.wdata(C_EXAMPLE_AXI_DATA_WIDTH-1 downto 0),
      wvalid              => axi_in.wvalid,
      wready              => axi_out.wready,
      bresp               => axi_out.bresp,
      bvalid              => axi_out.bvalid,
      bready              => axi_in.bready,
      araddr              => axi_in.araddr(C_EXAMPLE_AXI_ADDR_WIDTH-1 downto 0),
      arvalid             => axi_in.arvalid,
      arready             => axi_out.arready,
      rdata               => axi_out.rdata(C_EXAMPLE_AXI_DATA_WIDTH-1 downto 0),
      rresp               => axi_out.rresp,
      rvalid              => axi_out.rvalid,
      rready              => axi_in.rready
      );

  -- clock generator
  clock_generator(axi_clk, C_CLK_PERIOD);

  -- main testbench
  p_main : process

    -- Overloads for convenience
    procedure log_hdr (
      constant msg : in string) is
    begin  -- procedure log_hdr
      log(ID_LOG_HDR, msg, C_SCOPE);
    end procedure log_hdr;

    -- Overloads for convenience
    procedure log_hdr_large (
      constant msg : in string) is
    begin  -- procedure log_hdr
      log(ID_LOG_HDR_LARGE, msg, C_SCOPE);
    end procedure log_hdr_large;

    procedure write(
      constant addr_value : in unsigned;
      constant data_value : in std_logic_vector;
      constant msg        : in string) is
    begin
      axilite_write(addr_value,
                    data_value,
                    msg,
                    axi_clk,
                    axilite_if,
                    C_SCOPE,
                    shared_msg_id_panel,
                    axilite_bfm_config);
    end;

    procedure read(
      constant addr_value : in  unsigned;
      variable data_value : out std_logic_vector;
      constant msg        : in  string) is
    begin
      axilite_read(addr_value,
                   data_value,
                   msg,
                   axi_clk,
                   axilite_if,
                   C_SCOPE,
                   shared_msg_id_panel,
                   axilite_bfm_config);
    end;
    variable dummy_data : std_logic_vector(31 downto 0);

    procedure check(
      constant addr_value : in unsigned;
      constant data_exp   : in std_logic_vector;
      constant msg        : in string) is
    begin
      axilite_check(addr_value,
                    data_exp,
                    msg,
                    axi_clk,
                    axilite_if,
                    error,
                    C_SCOPE,
                    shared_msg_id_panel,
                    axilite_bfm_config);
    end;

  begin

    -- enable_log_msg(ALL_MESSAGES);
    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);
    enable_log_msg(ID_LOG_HDR_LARGE, QUIET);
    enable_log_msg(ID_SEQUENCER, QUIET);
    -- enable_log_msg(ID_BFM, QUIET);
    -- enable_log_msg(ID_CLOCK_GEN, QUIET);
    -- enable_log_msg(ID_GEN_PULSE, QUIET);
    -- enable_log_msg(ID_POS_ACK, QUIET);

    -- report_global_ctrl(VOID);
    -- report_msg_id_panel(VOID);

    gen_pulse(axi_areset_n, '0', 500 ns, BLOCKING, "Reset for 500 ns");

    --

    log_hdr_large("Checking Register reg0 - RW std_logic");

    log_hdr("Check Default Value");

    check_value(axi_rw_regs.reg0, '0', error, "reg0 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG0), 32X"0", "reg0 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG0), 32X"0", "Setting all bits to zero");
    check_value(axi_rw_regs.reg0, '0', error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG0), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG0), 32X"1", "Check all bit fields");
    check_value(axi_rw_regs.reg0, '1', error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG0), 32X"1", "Check all bit fields");
    -- Return to zero
    write(f_addr(g_axi_baseaddr, C_ADDR_REG0), 32X"0", "Check all bit fields");
    check_value(axi_rw_regs.reg0, '0', error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG0), 32X"0", "Check all bit fields");

    --

    log_hdr_large("Checking Register reg1 - RW std_logic");

    log_hdr("Check Default Value");

    check_value(axi_rw_regs.reg1, '1', error, "reg1 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG1), 32X"1", "reg1 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG1), 32X"0", "Setting all bits to zero");
    check_value(axi_rw_regs.reg1, '0', error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG1), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG1), 32X"1", "Check all bit fields");
    check_value(axi_rw_regs.reg1, '1', error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG1), 32X"1", "Check all bit fields");
    -- Return to zero
    write(f_addr(g_axi_baseaddr, C_ADDR_REG1), 32X"0", "Check all bit fields");
    check_value(axi_rw_regs.reg1, '0', error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG1), 32X"0", "Check all bit fields");

    --

    log_hdr_large("Checking Register reg2 - RO std_logic");

    log_hdr("Check Default Value");

    check_value(axi_ro_regs.reg2, '0', error, "reg2 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG2), 32X"0", "reg2 default value");

    log_hdr("Set&Check Zero Value");

    axi_ro_regs.reg2 <= '0';
    await_value(axi_ro_regs.reg2, '0', 0 ns, 1 ns, error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG2), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    axi_ro_regs.reg2 <= '1';
    await_value(axi_ro_regs.reg2, '1', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG2), 32X"1", "Check all bit fields");
    -- Return to zero
    axi_ro_regs.reg2 <= '0';
    await_value(axi_ro_regs.reg2, '0', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG2), 32X"0", "Check all bit fields");

    --

    log_hdr_large("Checking Register reg3 - RW 8 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(axi_rw_regs.reg3, 8X"3", error, "reg3 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG3), 32X"3", "reg3 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG3), 32X"0", "Setting all bits to zero");
    check_value(axi_rw_regs.reg3, 8X"0", error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG3), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 7 loop
      write(f_addr(g_axi_baseaddr, C_ADDR_REG3), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      check_value(axi_rw_regs.reg3, std_logic_vector(to_unsigned(1, 8) sll i), error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG3), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      -- Return to zero
      write(f_addr(g_axi_baseaddr, C_ADDR_REG3), 32X"0", "Check all bit fields");
      check_value(axi_rw_regs.reg3, 8X"0", error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG3), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg4 - RO 14 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(axi_ro_regs.reg4, 14X"0", error, "reg4 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG4), 32X"0", "reg4 default value");

    log_hdr("Set&Check Zero Value");

    axi_ro_regs.reg4 <= 14X"0";
    await_value(axi_ro_regs.reg4, 14X"0", 0 ns, 1 ns, error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG4), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 13 loop
      axi_ro_regs.reg4 <= std_logic_vector(to_unsigned(1, 14) sll i);
      await_value(axi_ro_regs.reg4, std_logic_vector(to_unsigned(1, 14) sll i), 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG4), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      -- Return to zero
      axi_ro_regs.reg4 <= 14X"0";
      await_value(axi_ro_regs.reg4, 14X"0", 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG4), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg5 - RW 32 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(axi_rw_regs.reg5, 32X"FFFFFFFF", error, "reg5 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG5), 32X"FFFFFFFF", "reg5 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG5), 32X"0", "Setting all bits to zero");
    check_value(axi_rw_regs.reg5, 32X"0", error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG5), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 31 loop
      write(f_addr(g_axi_baseaddr, C_ADDR_REG5), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      check_value(axi_rw_regs.reg5, std_logic_vector(to_unsigned(1, 32) sll i), error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG5), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      -- Return to zero
      write(f_addr(g_axi_baseaddr, C_ADDR_REG5), 32X"0", "Check all bit fields");
      check_value(axi_rw_regs.reg5, 32X"0", error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG5), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg6 - RO 32 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(axi_ro_regs.reg6, 32X"0", error, "reg6 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG6), 32X"0", "reg6 default value");

    log_hdr("Set&Check Zero Value");

    axi_ro_regs.reg6 <= 32X"0";
    await_value(axi_ro_regs.reg6, 32X"0", 0 ns, 1 ns, error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG6), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 31 loop
      axi_ro_regs.reg6 <= std_logic_vector(to_unsigned(1, 32) sll i);
      await_value(axi_ro_regs.reg6, std_logic_vector(to_unsigned(1, 32) sll i), 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG6), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      -- Return to zero
      axi_ro_regs.reg6 <= 32X"0";
      await_value(axi_ro_regs.reg6, 32X"0", 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG6), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg7 - RW fields");

    log_hdr("Check Default Value");

    check_value(axi_rw_regs.reg7.field0, '1', error, "reg7.field0 default value");
    check_value(axi_rw_regs.reg7.field1, 4X"b", error, "reg7.field1 default value");
    check_value(axi_rw_regs.reg7.field2, '0', error, "reg7.field2 default value");
    check_value(axi_rw_regs.reg7.field3, 15X"2b", error, "reg7.field3 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"AD7", "reg7 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Setting all bits to zero");
    check_value(axi_rw_regs.reg7.field0, '0', error, "Setting all bits to zero");
    check_value(axi_rw_regs.reg7.field1, 4X"0", error, "Setting all bits to zero");
    check_value(axi_rw_regs.reg7.field2, '0', error, "Setting all bits to zero");
    check_value(axi_rw_regs.reg7.field3, 15X"0", error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields field0");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"1", "Check all bit fields");
    check_value(axi_rw_regs.reg7.field0, '1', error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"1", "Check all bit fields");
    -- Return to zero
    write(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
    check_value(axi_rw_regs.reg7.field0, '0', error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");

    log_hdr("Check all bit fields field1");

    for i in 0 to 3 loop
      write(f_addr(g_axi_baseaddr, C_ADDR_REG7), std_logic_vector(to_unsigned(1, data_width) sll i+1), "Check all bit fields");
      check_value(axi_rw_regs.reg7.field1, std_logic_vector(to_unsigned(1, 4) sll i), error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG7), std_logic_vector(to_unsigned(1, data_width) sll i+1), "Check all bit fields");
      -- Return to zero
      write(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
      check_value(axi_rw_regs.reg7.field1, 4X"0", error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
    end loop;

    log_hdr("Check all bit fields field2");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"20", "Check all bit fields");
    check_value(axi_rw_regs.reg7.field2, '1', error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"20", "Check all bit fields");
    -- Return to zero
    write(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
    check_value(axi_rw_regs.reg7.field2, '0', error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");

    log_hdr("Check all bit fields field3");

    for i in 0 to 14 loop
      write(f_addr(g_axi_baseaddr, C_ADDR_REG7), std_logic_vector(to_unsigned(1, data_width) sll i+6), "Check all bit fields");
      check_value(axi_rw_regs.reg7.field3, std_logic_vector(to_unsigned(1, 15) sll i), error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG7), std_logic_vector(to_unsigned(1, data_width) sll i+6), "Check all bit fields");
      -- Return to zero
      write(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
      check_value(axi_rw_regs.reg7.field3, 15X"0", error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg8 - RO fields");

    log_hdr("Check Default Value");

    check_value(axi_ro_regs.reg8.field0, '0', error, "reg8.field0 default value");
    check_value(axi_ro_regs.reg8.field1, 19X"0", error, "reg8.field1 default value");
    check_value(axi_ro_regs.reg8.field2, '0', error, "reg8.field2 default value");
    check_value(axi_ro_regs.reg8.field3, 3X"0", error, "reg8.field3 default value");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG8), 32X"0", "reg8 default value");

    log_hdr("Set&Check Zero Value");

    axi_ro_regs.reg8.field0 <= '0';
    axi_ro_regs.reg8.field1 <= (others => '0');
    axi_ro_regs.reg8.field2 <= '0';
    axi_ro_regs.reg8.field3 <= (others => '0');
    await_value(axi_ro_regs.reg8.field0, '0', 0 ns, 1 ns, error, "Setting all bits to zero");
    await_value(axi_ro_regs.reg8.field1, 19X"0", 0 ns, 1 ns, error, "Setting all bits to zero");
    await_value(axi_ro_regs.reg8.field2, '0', 0 ns, 1 ns, error, "Setting all bits to zero");
    await_value(axi_ro_regs.reg8.field3, 3X"0", 0 ns, 1 ns, error, "Setting all bits to zero");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG8), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields field0");

    axi_ro_regs.reg8.field0 <= '1';
    await_value(axi_ro_regs.reg8.field0, '1', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG8), 32X"1", "Check all bit fields");
    -- Return to zero
    axi_ro_regs.reg8.field0 <= '0';
    await_value(axi_ro_regs.reg8.field0, '0', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG8), 32X"0", "Check all bit fields");

    log_hdr("Check all bit fields field1");

    for i in 0 to 18 loop
      axi_ro_regs.reg8.field1 <= std_logic_vector(to_unsigned(1, 19) sll i);
      await_value(axi_ro_regs.reg8.field1, std_logic_vector(to_unsigned(1, 19) sll i), 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG8), std_logic_vector(to_unsigned(1, data_width) sll i+1), "Check all bit fields");
      -- Return to zero
      axi_ro_regs.reg8.field1 <= 19X"0";
      await_value(axi_ro_regs.reg8.field1, 19X"0", 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG8), 32X"0", "Check all bit fields");
    end loop;

    log_hdr("Check all bit fields field2");

    axi_ro_regs.reg8.field2 <= '1';
    await_value(axi_ro_regs.reg8.field2, '1', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG8), 32X"100000", "Check all bit fields");
    -- Return to zero
    axi_ro_regs.reg8.field2 <= '0';
    await_value(axi_ro_regs.reg8.field2, '0', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_axi_baseaddr, C_ADDR_REG8), 32X"0", "Check all bit fields");

    log_hdr("Check all bit fields field3");

    for i in 0 to 2 loop
      axi_ro_regs.reg8.field3 <= std_logic_vector(to_unsigned(1, 3) sll i);
      await_value(axi_ro_regs.reg8.field3, std_logic_vector(to_unsigned(1, 3) sll i), 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG8), std_logic_vector(to_unsigned(1, data_width) sll i+21), "Check all bit fields");
      -- Return to zero
      axi_ro_regs.reg8.field3 <= 3X"0";
      await_value(axi_ro_regs.reg8.field3, 3X"0", 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_axi_baseaddr, C_ADDR_REG8), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg9 - PULSE std_logic");

    log_hdr("Check Default Value");

    check_value(axi_pulse_regs.reg9, '1', error, "reg9 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG9), 32X"0", "Setting all bits to zero");
    check_value(axi_pulse_regs.reg9, '0', error, "Setting all bits to zero");
    await_stable(axi_pulse_regs.reg9, 4*C_CLK_PERIOD, FROM_LAST_EVENT, 4*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Setting all bits to zero");
    check_value(axi_pulse_regs.reg9, '0', error, "Setting all bits to zero");
    await_value(axi_pulse_regs.reg9, '1', 0 ns, 1 ns, error, "Setting all bits to zero");

    log_hdr("Check all bit fields");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG9), 32X"1", "Check all bit fields");
    check_value(axi_pulse_regs.reg9, '1', error, "Check all bit fields");
    await_stable(axi_pulse_regs.reg9, 4*C_CLK_PERIOD, FROM_LAST_EVENT, 4*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Check all bit fields");
    check_value(axi_pulse_regs.reg9, '1', error, "Check all bit fields");
    await_value(axi_pulse_regs.reg9, '1', 0 ns, 1 ns, error, "Check all bit fields");

    --

    log_hdr_large("Checking Register reg10 - PULSE 4 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(axi_pulse_regs.reg10, 4X"a", error, "reg10 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG10), 32X"0", "Setting all bits to zero");
    check_value(axi_pulse_regs.reg10, 4X"0", error, "Setting all bits to zero");
    await_stable(axi_pulse_regs.reg10, 1*C_CLK_PERIOD, FROM_LAST_EVENT, 1*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Setting all bits to zero");
    check_value(axi_pulse_regs.reg10, 4X"0", error, "Setting all bits to zero");
    await_value(axi_pulse_regs.reg10, 4X"a", 0 ns, 1 ns, error, "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 3 loop
      write(f_addr(g_axi_baseaddr, C_ADDR_REG10), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      check_value(axi_pulse_regs.reg10, std_logic_vector(to_unsigned(1, 4) sll i), error, "Check all bit fields");
      await_stable(axi_pulse_regs.reg10, 1*C_CLK_PERIOD, FROM_LAST_EVENT, 1*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Check all bit fields");
      check_value(axi_pulse_regs.reg10, std_logic_vector(to_unsigned(1, 4) sll i), error, "Check all bit fields");
      await_value(axi_pulse_regs.reg10, 4X"a", 0 ns, 1 ns, error, "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg11 - PULSE fields");

    log_hdr("Check Default Value");

    check_value(axi_pulse_regs.reg11.field0, 15X"3", error, "reg11.field0 default value");
    check_value(axi_pulse_regs.reg11.field1, '0', error, "reg11.field1 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG11), 32X"0", "Setting all bits to zero");
    check_value(axi_pulse_regs.reg11.field0, 15X"0", error, "Setting all bits to zero");
    check_value(axi_pulse_regs.reg11.field1, '0', error, "Setting all bits to zero");
    await_stable(axi_pulse_regs.reg11.field0, 50*C_CLK_PERIOD, FROM_LAST_EVENT, 50*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Setting all bits to zero");
    await_stable(axi_pulse_regs.reg11.field1, 50*C_CLK_PERIOD, FROM_LAST_EVENT, 50*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Setting all bits to zero");
    check_value(axi_pulse_regs.reg11.field0, 15X"0", error, "Setting all bits to zero");
    check_value(axi_pulse_regs.reg11.field1, '0', error, "Setting all bits to zero");
    await_value(axi_pulse_regs.reg11.field0, 15X"3", 0 ns, 1 ns, error, "Setting all bits to zero");
    await_value(axi_pulse_regs.reg11.field1, '0', 0 ns, 1 ns, error, "Setting all bits to zero");

    log_hdr("Check all bit fields field0");

    for i in 0 to 14 loop
      write(f_addr(g_axi_baseaddr, C_ADDR_REG11), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      check_value(axi_pulse_regs.reg11.field0, std_logic_vector(to_unsigned(1, 15) sll i), error, "Check all bit fields");
      await_stable(axi_pulse_regs.reg11.field0, 50*C_CLK_PERIOD, FROM_LAST_EVENT, 50*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Check all bit fields");
      check_value(axi_pulse_regs.reg11.field0, std_logic_vector(to_unsigned(1, 15) sll i), error, "Check all bit fields");
      await_value(axi_pulse_regs.reg11.field0, 15X"3", 0 ns, 1 ns, error, "Check all bit fields");
    end loop;

    log_hdr("Check all bit fields field1");

    write(f_addr(g_axi_baseaddr, C_ADDR_REG11), 32X"8000", "Check all bit fields");
    check_value(axi_pulse_regs.reg11.field1, '1', error, "Check all bit fields");
    await_stable(axi_pulse_regs.reg11.field1, 50*C_CLK_PERIOD, FROM_LAST_EVENT, 50*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Check all bit fields");
    check_value(axi_pulse_regs.reg11.field1, '1', error, "Check all bit fields");
    await_value(axi_pulse_regs.reg11.field1, '0', 0 ns, 1 ns, error, "Check all bit fields");

    --==================================================================================================
    -- Ending the simulation
    --------------------------------------------------------------------------------------
    wait for 100 ns;                    -- to allow some time for completion
    report_alert_counters(FINAL);  -- Report final counters and print conclusion for simulation (Success/Fail)
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);

    -- Finish the simulation
    std.env.stop;
    wait;                               -- to stop completely
  end process p_main;

end architecture tb;
