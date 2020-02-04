library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library ipbus;
use ipbus.ipbus.all;

use work.example_ipbus_pif_pkg.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library vip_ipbus;
use vip_ipbus.ipbus_bfm_pkg.all;

-------------------------------------------------------------------------------

entity example_ipbus_ipb_pif_tb is

end entity example_ipbus_ipb_pif_tb;

-------------------------------------------------------------------------------

architecture tb of example_ipbus_ipb_pif_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  -- component generics
  constant g_ipb_baseaddr : std_logic_vector(31 downto 0) := 32X"FFAA0000";
  constant g_instance_num : natural                       := 0;

  -- component ports
  signal ipb_rw_regs    : t_example_ipbus_rw_regs    := c_example_ipbus_rw_regs;
  signal ipb_ro_regs    : t_example_ipbus_ro_regs    := c_example_ipbus_ro_regs;
  signal ipb_pulse_regs : t_example_ipbus_pulse_regs := c_example_ipbus_pulse_regs;
  signal ipb_clk        : std_logic                   := '1';
  signal ipb_reset      : std_logic                   := '0';
  signal ipb_in         : ipb_wbus;
  signal ipb_out        : ipb_rbus;

  -- vip_ipbus BFM
  constant data_width : natural := 32;
  constant addr_width : natural := 32;
  signal ipbus_if : t_ipbus_if := init_ipbus_if_signals;
  signal ipbus_bfm_config : t_ipbus_bfm_config := C_IPBUS_BFM_CONFIG_DEFAULT;

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

  ipbus_bfm_config.clock_period <= C_CLK_PERIOD;
  ipbus_bfm_config.setup_time   <= C_CLK_PERIOD/8;
  ipbus_bfm_config.hold_time    <= C_CLK_PERIOD/8;

  ipb_in.ipb_wdata  <= ipbus_if.wdata;
  ipb_in.ipb_write  <= ipbus_if.wr;
  ipb_in.ipb_addr  <= ipbus_if.addr;
  ipb_in.ipb_strobe  <= ipbus_if.strobe;

  ipbus_if.rdata  <= ipb_out.ipb_rdata;
  ipbus_if.ack  <= ipb_out.ipb_ack;
  ipbus_if.err  <= ipb_out.ipb_err;

  -- component instantiation
  DUT : entity work.example_ipbus_ipb_pif
    generic map (
      g_ipb_baseaddr      => g_ipb_baseaddr)
    port map (
      ipb_rw_regs         => ipb_rw_regs,
      ipb_ro_regs         => ipb_ro_regs,
      ipb_pulse_regs      => ipb_pulse_regs,
      clk                 => ipb_clk,
      reset               => ipb_reset,
      ipb_in              => ipb_in,
      ipb_out             => ipb_out
      );

  -- clock generator
  clock_generator(ipb_clk, C_CLK_PERIOD);

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
      ipbus_write(addr_value,
                    data_value,
                    msg,
                    ipb_clk,
                    ipbus_if,
                    C_SCOPE,
                    shared_msg_id_panel,
                    ipbus_bfm_config);
    end;

    procedure read(
      constant addr_value : in  unsigned;
      variable data_value : out std_logic_vector;
      constant msg        : in  string) is
    begin
      ipbus_read(addr_value,
                   data_value,
                   msg,
                   ipb_clk,
                   ipbus_if,
                   C_SCOPE,
                   shared_msg_id_panel,
                   ipbus_bfm_config);
    end;
    variable dummy_data : std_logic_vector(31 downto 0);

    procedure check(
      constant addr_value : in unsigned;
      constant data_exp   : in std_logic_vector;
      constant msg        : in string) is
    begin
      ipbus_check(addr_value,
                    data_exp,
                    msg,
                    ipb_clk,
                    ipbus_if,
                    error,
                    C_SCOPE,
                    shared_msg_id_panel,
                    ipbus_bfm_config);
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

    gen_pulse(ipb_reset, '1', 500 ns, BLOCKING, "Reset for 500 ns");

    --

    log_hdr_large("Checking Register reg0 - RW std_logic");

    log_hdr("Check Default Value");

    check_value(ipb_rw_regs.reg0, '0', error, "reg0 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG0), 32X"0", "reg0 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG0), 32X"0", "Setting all bits to zero");
    check_value(ipb_rw_regs.reg0, '0', error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG0), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG0), 32X"1", "Check all bit fields");
    check_value(ipb_rw_regs.reg0, '1', error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG0), 32X"1", "Check all bit fields");
    -- Return to zero
    write(f_addr(g_ipb_baseaddr, C_ADDR_REG0), 32X"0", "Check all bit fields");
    check_value(ipb_rw_regs.reg0, '0', error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG0), 32X"0", "Check all bit fields");

    --

    log_hdr_large("Checking Register reg1 - RW std_logic");

    log_hdr("Check Default Value");

    check_value(ipb_rw_regs.reg1, '1', error, "reg1 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG1), 32X"1", "reg1 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG1), 32X"0", "Setting all bits to zero");
    check_value(ipb_rw_regs.reg1, '0', error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG1), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG1), 32X"1", "Check all bit fields");
    check_value(ipb_rw_regs.reg1, '1', error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG1), 32X"1", "Check all bit fields");
    -- Return to zero
    write(f_addr(g_ipb_baseaddr, C_ADDR_REG1), 32X"0", "Check all bit fields");
    check_value(ipb_rw_regs.reg1, '0', error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG1), 32X"0", "Check all bit fields");

    --

    log_hdr_large("Checking Register reg2 - RO std_logic");

    log_hdr("Check Default Value");

    check_value(ipb_ro_regs.reg2, '0', error, "reg2 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG2), 32X"0", "reg2 default value");

    log_hdr("Set&Check Zero Value");

    ipb_ro_regs.reg2 <= '0';
    await_value(ipb_ro_regs.reg2, '0', 0 ns, 1 ns, error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG2), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    ipb_ro_regs.reg2 <= '1';
    await_value(ipb_ro_regs.reg2, '1', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG2), 32X"1", "Check all bit fields");
    -- Return to zero
    ipb_ro_regs.reg2 <= '0';
    await_value(ipb_ro_regs.reg2, '0', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG2), 32X"0", "Check all bit fields");

    --

    log_hdr_large("Checking Register reg3 - RW 8 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(ipb_rw_regs.reg3, 8X"3", error, "reg3 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG3), 32X"3", "reg3 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG3), 32X"0", "Setting all bits to zero");
    check_value(ipb_rw_regs.reg3, 8X"0", error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG3), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 7 loop
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG3), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      check_value(ipb_rw_regs.reg3, std_logic_vector(to_unsigned(1, 8) sll i), error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG3), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      -- Return to zero
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG3), 32X"0", "Check all bit fields");
      check_value(ipb_rw_regs.reg3, 8X"0", error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG3), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg4 - RO 14 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(ipb_ro_regs.reg4, 14X"0", error, "reg4 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG4), 32X"0", "reg4 default value");

    log_hdr("Set&Check Zero Value");

    ipb_ro_regs.reg4 <= 14X"0";
    await_value(ipb_ro_regs.reg4, 14X"0", 0 ns, 1 ns, error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG4), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 13 loop
      ipb_ro_regs.reg4 <= std_logic_vector(to_unsigned(1, 14) sll i);
      await_value(ipb_ro_regs.reg4, std_logic_vector(to_unsigned(1, 14) sll i), 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG4), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      -- Return to zero
      ipb_ro_regs.reg4 <= 14X"0";
      await_value(ipb_ro_regs.reg4, 14X"0", 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG4), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg5 - RW 32 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(ipb_rw_regs.reg5, 32X"FFFFFFFF", error, "reg5 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG5), 32X"FFFFFFFF", "reg5 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG5), 32X"0", "Setting all bits to zero");
    check_value(ipb_rw_regs.reg5, 32X"0", error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG5), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 31 loop
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG5), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      check_value(ipb_rw_regs.reg5, std_logic_vector(to_unsigned(1, 32) sll i), error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG5), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      -- Return to zero
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG5), 32X"0", "Check all bit fields");
      check_value(ipb_rw_regs.reg5, 32X"0", error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG5), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg6 - RO 32 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(ipb_ro_regs.reg6, 32X"0", error, "reg6 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG6), 32X"0", "reg6 default value");

    log_hdr("Set&Check Zero Value");

    ipb_ro_regs.reg6 <= 32X"0";
    await_value(ipb_ro_regs.reg6, 32X"0", 0 ns, 1 ns, error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG6), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 31 loop
      ipb_ro_regs.reg6 <= std_logic_vector(to_unsigned(1, 32) sll i);
      await_value(ipb_ro_regs.reg6, std_logic_vector(to_unsigned(1, 32) sll i), 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG6), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      -- Return to zero
      ipb_ro_regs.reg6 <= 32X"0";
      await_value(ipb_ro_regs.reg6, 32X"0", 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG6), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg7 - RW fields");

    log_hdr("Check Default Value");

    check_value(ipb_rw_regs.reg7.field0, '1', error, "reg7.field0 default value");
    check_value(ipb_rw_regs.reg7.field1, 4X"b", error, "reg7.field1 default value");
    check_value(ipb_rw_regs.reg7.field2, '0', error, "reg7.field2 default value");
    check_value(ipb_rw_regs.reg7.field3, 15X"2b", error, "reg7.field3 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"AD7", "reg7 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Setting all bits to zero");
    check_value(ipb_rw_regs.reg7.field0, '0', error, "Setting all bits to zero");
    check_value(ipb_rw_regs.reg7.field1, 4X"0", error, "Setting all bits to zero");
    check_value(ipb_rw_regs.reg7.field2, '0', error, "Setting all bits to zero");
    check_value(ipb_rw_regs.reg7.field3, 15X"0", error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields field0");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"1", "Check all bit fields");
    check_value(ipb_rw_regs.reg7.field0, '1', error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"1", "Check all bit fields");
    -- Return to zero
    write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
    check_value(ipb_rw_regs.reg7.field0, '0', error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");

    log_hdr("Check all bit fields field1");

    for i in 0 to 3 loop
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), std_logic_vector(to_unsigned(1, data_width) sll i+1), "Check all bit fields");
      check_value(ipb_rw_regs.reg7.field1, std_logic_vector(to_unsigned(1, 4) sll i), error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), std_logic_vector(to_unsigned(1, data_width) sll i+1), "Check all bit fields");
      -- Return to zero
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
      check_value(ipb_rw_regs.reg7.field1, 4X"0", error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
    end loop;

    log_hdr("Check all bit fields field2");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"20", "Check all bit fields");
    check_value(ipb_rw_regs.reg7.field2, '1', error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"20", "Check all bit fields");
    -- Return to zero
    write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
    check_value(ipb_rw_regs.reg7.field2, '0', error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");

    log_hdr("Check all bit fields field3");

    for i in 0 to 14 loop
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), std_logic_vector(to_unsigned(1, data_width) sll i+6), "Check all bit fields");
      check_value(ipb_rw_regs.reg7.field3, std_logic_vector(to_unsigned(1, 15) sll i), error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), std_logic_vector(to_unsigned(1, data_width) sll i+6), "Check all bit fields");
      -- Return to zero
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
      check_value(ipb_rw_regs.reg7.field3, 15X"0", error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG7), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg8 - RO fields");

    log_hdr("Check Default Value");

    check_value(ipb_ro_regs.reg8.field0, '0', error, "reg8.field0 default value");
    check_value(ipb_ro_regs.reg8.field1, 19X"0", error, "reg8.field1 default value");
    check_value(ipb_ro_regs.reg8.field2, '0', error, "reg8.field2 default value");
    check_value(ipb_ro_regs.reg8.field3, 3X"0", error, "reg8.field3 default value");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), 32X"0", "reg8 default value");

    log_hdr("Set&Check Zero Value");

    ipb_ro_regs.reg8.field0 <= '0';
    ipb_ro_regs.reg8.field1 <= (others => '0');
    ipb_ro_regs.reg8.field2 <= '0';
    ipb_ro_regs.reg8.field3 <= (others => '0');
    await_value(ipb_ro_regs.reg8.field0, '0', 0 ns, 1 ns, error, "Setting all bits to zero");
    await_value(ipb_ro_regs.reg8.field1, 19X"0", 0 ns, 1 ns, error, "Setting all bits to zero");
    await_value(ipb_ro_regs.reg8.field2, '0', 0 ns, 1 ns, error, "Setting all bits to zero");
    await_value(ipb_ro_regs.reg8.field3, 3X"0", 0 ns, 1 ns, error, "Setting all bits to zero");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), 32X"0", "Setting all bits to zero");

    log_hdr("Check all bit fields field0");

    ipb_ro_regs.reg8.field0 <= '1';
    await_value(ipb_ro_regs.reg8.field0, '1', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), 32X"1", "Check all bit fields");
    -- Return to zero
    ipb_ro_regs.reg8.field0 <= '0';
    await_value(ipb_ro_regs.reg8.field0, '0', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), 32X"0", "Check all bit fields");

    log_hdr("Check all bit fields field1");

    for i in 0 to 18 loop
      ipb_ro_regs.reg8.field1 <= std_logic_vector(to_unsigned(1, 19) sll i);
      await_value(ipb_ro_regs.reg8.field1, std_logic_vector(to_unsigned(1, 19) sll i), 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), std_logic_vector(to_unsigned(1, data_width) sll i+1), "Check all bit fields");
      -- Return to zero
      ipb_ro_regs.reg8.field1 <= 19X"0";
      await_value(ipb_ro_regs.reg8.field1, 19X"0", 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), 32X"0", "Check all bit fields");
    end loop;

    log_hdr("Check all bit fields field2");

    ipb_ro_regs.reg8.field2 <= '1';
    await_value(ipb_ro_regs.reg8.field2, '1', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), 32X"100000", "Check all bit fields");
    -- Return to zero
    ipb_ro_regs.reg8.field2 <= '0';
    await_value(ipb_ro_regs.reg8.field2, '0', 0 ns, 1 ns, error, "Check all bit fields");
    check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), 32X"0", "Check all bit fields");

    log_hdr("Check all bit fields field3");

    for i in 0 to 2 loop
      ipb_ro_regs.reg8.field3 <= std_logic_vector(to_unsigned(1, 3) sll i);
      await_value(ipb_ro_regs.reg8.field3, std_logic_vector(to_unsigned(1, 3) sll i), 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), std_logic_vector(to_unsigned(1, data_width) sll i+21), "Check all bit fields");
      -- Return to zero
      ipb_ro_regs.reg8.field3 <= 3X"0";
      await_value(ipb_ro_regs.reg8.field3, 3X"0", 0 ns, 1 ns, error, "Check all bit fields");
      check(f_addr(g_ipb_baseaddr, C_ADDR_REG8), 32X"0", "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg9 - PULSE std_logic");

    log_hdr("Check Default Value");

    check_value(ipb_pulse_regs.reg9, '1', error, "reg9 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG9), 32X"0", "Setting all bits to zero");
    check_value(ipb_pulse_regs.reg9, '0', error, "Setting all bits to zero");
    await_stable(ipb_pulse_regs.reg9, 4*C_CLK_PERIOD, FROM_LAST_EVENT, 4*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Setting all bits to zero");
    check_value(ipb_pulse_regs.reg9, '0', error, "Setting all bits to zero");
    await_value(ipb_pulse_regs.reg9, '1', 0 ns, 1 ns, error, "Setting all bits to zero");

    log_hdr("Check all bit fields");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG9), 32X"1", "Check all bit fields");
    check_value(ipb_pulse_regs.reg9, '1', error, "Check all bit fields");
    await_stable(ipb_pulse_regs.reg9, 4*C_CLK_PERIOD, FROM_LAST_EVENT, 4*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Check all bit fields");
    check_value(ipb_pulse_regs.reg9, '1', error, "Check all bit fields");
    await_value(ipb_pulse_regs.reg9, '1', 0 ns, 1 ns, error, "Check all bit fields");

    --

    log_hdr_large("Checking Register reg10 - PULSE 4 bit std_logic_vector");

    log_hdr("Check Default Value");

    check_value(ipb_pulse_regs.reg10, 4X"a", error, "reg10 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG10), 32X"0", "Setting all bits to zero");
    check_value(ipb_pulse_regs.reg10, 4X"0", error, "Setting all bits to zero");
    await_stable(ipb_pulse_regs.reg10, 1*C_CLK_PERIOD, FROM_LAST_EVENT, 1*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Setting all bits to zero");
    check_value(ipb_pulse_regs.reg10, 4X"0", error, "Setting all bits to zero");
    await_value(ipb_pulse_regs.reg10, 4X"a", 0 ns, 1 ns, error, "Setting all bits to zero");

    log_hdr("Check all bit fields");

    for i in 0 to 3 loop
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG10), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      check_value(ipb_pulse_regs.reg10, std_logic_vector(to_unsigned(1, 4) sll i), error, "Check all bit fields");
      await_stable(ipb_pulse_regs.reg10, 1*C_CLK_PERIOD, FROM_LAST_EVENT, 1*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Check all bit fields");
      check_value(ipb_pulse_regs.reg10, std_logic_vector(to_unsigned(1, 4) sll i), error, "Check all bit fields");
      await_value(ipb_pulse_regs.reg10, 4X"a", 0 ns, 1 ns, error, "Check all bit fields");
    end loop;

    --

    log_hdr_large("Checking Register reg11 - PULSE fields");

    log_hdr("Check Default Value");

    check_value(ipb_pulse_regs.reg11.field0, 15X"3", error, "reg11.field0 default value");
    check_value(ipb_pulse_regs.reg11.field1, '0', error, "reg11.field1 default value");

    log_hdr("Set&Check Zero Value");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG11), 32X"0", "Setting all bits to zero");
    check_value(ipb_pulse_regs.reg11.field0, 15X"0", error, "Setting all bits to zero");
    check_value(ipb_pulse_regs.reg11.field1, '0', error, "Setting all bits to zero");
    await_stable(ipb_pulse_regs.reg11.field0, 50*C_CLK_PERIOD, FROM_LAST_EVENT, 50*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Setting all bits to zero");
    await_stable(ipb_pulse_regs.reg11.field1, 50*C_CLK_PERIOD, FROM_LAST_EVENT, 50*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Setting all bits to zero");
    check_value(ipb_pulse_regs.reg11.field0, 15X"0", error, "Setting all bits to zero");
    check_value(ipb_pulse_regs.reg11.field1, '0', error, "Setting all bits to zero");
    await_value(ipb_pulse_regs.reg11.field0, 15X"3", 0 ns, 1 ns, error, "Setting all bits to zero");
    await_value(ipb_pulse_regs.reg11.field1, '0', 0 ns, 1 ns, error, "Setting all bits to zero");

    log_hdr("Check all bit fields field0");

    for i in 0 to 14 loop
      write(f_addr(g_ipb_baseaddr, C_ADDR_REG11), std_logic_vector(to_unsigned(1, data_width) sll i), "Check all bit fields");
      check_value(ipb_pulse_regs.reg11.field0, std_logic_vector(to_unsigned(1, 15) sll i), error, "Check all bit fields");
      await_stable(ipb_pulse_regs.reg11.field0, 50*C_CLK_PERIOD, FROM_LAST_EVENT, 50*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Check all bit fields");
      check_value(ipb_pulse_regs.reg11.field0, std_logic_vector(to_unsigned(1, 15) sll i), error, "Check all bit fields");
      await_value(ipb_pulse_regs.reg11.field0, 15X"3", 0 ns, 1 ns, error, "Check all bit fields");
    end loop;

    log_hdr("Check all bit fields field1");

    write(f_addr(g_ipb_baseaddr, C_ADDR_REG11), 32X"8000", "Check all bit fields");
    check_value(ipb_pulse_regs.reg11.field1, '1', error, "Check all bit fields");
    await_stable(ipb_pulse_regs.reg11.field1, 50*C_CLK_PERIOD, FROM_LAST_EVENT, 50*C_CLK_PERIOD, FROM_LAST_EVENT, error, "Check all bit fields");
    check_value(ipb_pulse_regs.reg11.field1, '1', error, "Check all bit fields");
    await_value(ipb_pulse_regs.reg11.field1, '0', 0 ns, 1 ns, error, "Check all bit fields");

    --

    log_hdr_large("Checking that invalid register returns ERR");

    ipbus_bfm_config.expected_response <= ERR;

    log_hdr("Check erroneous read");

    read(32X"FFFFFFFF", dummy_data, "Read from register that does not exist");
    check_value(dummy_data, 32X"DEADBEEF", error, "Check that the returned data is rubbish");

    log_hdr("Check erroneous write");

    write(32X"FFFFFFFF", 32X"0", "Write to register that does not exist");

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
