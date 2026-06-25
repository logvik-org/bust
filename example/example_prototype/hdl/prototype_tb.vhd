-- Generated UVVM testbench for the prototype module (AXI4-Lite).
-- Drives the prototype top entity with the stock Bitvis AXI-Lite VIP and
-- self-checks every plain software read-write register (write then read back).
-- Registers with access-mode side effects (onread/onwrite/singlepulse, enum,
-- hardware-driven) are not exercised here yet.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library bitvis_vip_axilite;
use bitvis_vip_axilite.axilite_bfm_pkg.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_tb is
end entity prototype_tb;

architecture tb of prototype_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  constant C_BASE : std_logic_vector(31 downto 0) := 32x"0";

  signal clk      : std_logic := '0';
  signal areset_n : std_logic := '1';

  signal to_hw    : t_prototype_to_hw;
  signal from_hw  : t_prototype_from_hw := (
    reg1 => (field0 => (value => (others => '0'), we => '0'), field1 => '0', field2 => (value => '0', wel => '1')),
    reg4 => (field0 => (value => (others => '0'), we => '0'), field1 => (set => '0', clr => '0')));

  constant C_DATA_W : natural := 32;
  constant C_ADDR_W : natural := 32;
  signal axilite_if : t_axilite_if(write_address_channel(awaddr(C_ADDR_W-1 downto 0)),
                                   write_data_channel(wdata(C_DATA_W-1 downto 0),
                                                      wstrb((C_DATA_W/8)-1 downto 0)),
                                   read_address_channel(araddr(C_ADDR_W-1 downto 0)),
                                   read_data_channel(rdata(C_DATA_W-1 downto 0)))
                      := init_axilite_if_signals(C_DATA_W, C_ADDR_W);
  signal axilite_bfm_config : t_axilite_bfm_config := C_AXILITE_BFM_CONFIG_DEFAULT;

  function f_addr(base : std_logic_vector(31 downto 0);
                  reg  : std_logic_vector(31 downto 0)) return unsigned is
  begin
    return unsigned(base) + unsigned(reg);
  end function;

begin

  clock_generator(clk, C_CLK_PERIOD);

  DUT : entity work.prototype
    generic map (
      G_BASE_ADDRESS       => unsigned(C_BASE),
      G_CHECK_BASE_ADDRESS => true)
    port map (
      clk      => clk,
      areset_n => areset_n,
      awaddr   => axilite_if.write_address_channel.awaddr,
      awvalid  => axilite_if.write_address_channel.awvalid,
      awready  => axilite_if.write_address_channel.awready,
      wdata    => axilite_if.write_data_channel.wdata,
      wvalid   => axilite_if.write_data_channel.wvalid,
      wready   => axilite_if.write_data_channel.wready,
      bresp    => axilite_if.write_response_channel.bresp,
      bvalid   => axilite_if.write_response_channel.bvalid,
      bready   => axilite_if.write_response_channel.bready,
      araddr   => axilite_if.read_address_channel.araddr,
      arvalid  => axilite_if.read_address_channel.arvalid,
      arready  => axilite_if.read_address_channel.arready,
      rdata    => axilite_if.read_data_channel.rdata,
      rresp    => axilite_if.read_data_channel.rresp,
      rvalid   => axilite_if.read_data_channel.rvalid,
      rready   => axilite_if.read_data_channel.rready,      to_hw    => to_hw,      from_hw  => from_hw);

  p_main : process is

    procedure axi_write(constant addr : in unsigned;
                        constant data : in std_logic_vector;
                        constant msg  : in string) is
    begin
      axilite_write(addr, data, msg, clk, axilite_if, C_SCOPE,
                    shared_msg_id_panel, axilite_bfm_config);
    end procedure;

    procedure axi_check(constant addr : in unsigned;
                        constant data : in std_logic_vector;
                        constant msg  : in string) is
    begin
      axilite_check(addr, data, msg, clk, axilite_if, error, C_SCOPE,
                    shared_msg_id_panel, axilite_bfm_config);
    end procedure;

  begin
    axilite_bfm_config.clock_period <= C_CLK_PERIOD;

    disable_log_msg(ALL_MESSAGES, QUIET);
    enable_log_msg(ID_LOG_HDR, QUIET);

    gen_pulse(areset_n, '0', 500 ns, BLOCKING, "Reset for 500 ns");

    log(ID_LOG_HDR, "reg0: software read-write round-trip", C_SCOPE);
    axi_write(f_addr(C_BASE, C_ADDR_REG0), 32x"00000007", "write reg0");
    axi_check(f_addr(C_BASE, C_ADDR_REG0), 32x"00000007", "reg0 reads back");

    log(ID_LOG_HDR, "reg3: software read-write round-trip", C_SCOPE);
    axi_write(f_addr(C_BASE, C_ADDR_REG3), 32x"000000FF", "write reg3");
    axi_check(f_addr(C_BASE, C_ADDR_REG3), 32x"000000FF", "reg3 reads back");

    log(ID_LOG_HDR, "reg9: software read-write round-trip", C_SCOPE);
    axi_write(f_addr(C_BASE, C_ADDR_REG9), 32x"000000FF", "write reg9");
    axi_check(f_addr(C_BASE, C_ADDR_REG9), 32x"000000FF", "reg9 reads back");

    wait for 10*C_CLK_PERIOD;
    report_alert_counters(FINAL);
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);
    std.env.stop;
    wait;
  end process p_main;

end architecture tb;
