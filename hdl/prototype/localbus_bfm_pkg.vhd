-- UVVM bus functional model for the protocol-agnostic local bus.
--
-- Drives single-beat transactions on t_lb_m2s / t_lb_s2m and checks the
-- response using uvvm_util (alerts, logging, check_value). It follows the
-- direct-BFM style used by vip_ipbus in this project: a config record, a
-- scope, and a msg_id_panel per call.
--
-- The local bus has no separate stall wire, so the BFM holds the request until
-- it observes ack or err (bounded by config.max_wait_cycles). Responses are
-- sampled on the falling edge, after the regfile's clocked ack/err has settled.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

use work.prototype_localbus_pkg.all;

package localbus_bfm_pkg is

  constant C_SCOPE : string := "LOCALBUS_BFM";

  type t_localbus_bfm_config is record
    max_wait_cycles          : integer;       -- response timeout, in clk cycles
    max_wait_cycles_severity : t_alert_level;  -- alert raised on timeout
    id_for_bfm               : t_msg_id;       -- msg_id for transaction logging
  end record;

  constant C_LOCALBUS_BFM_CONFIG_DEFAULT : t_localbus_bfm_config := (
    max_wait_cycles          => 256,
    max_wait_cycles_severity => failure,
    id_for_bfm               => ID_BFM);

  procedure localbus_write(
    constant addr_value    : in    std_logic_vector;
    constant data_value    : in    std_logic_vector;
    constant msg           : in    string;
    signal   clk           : in    std_logic;
    signal   lb_m2s        : inout t_lb_m2s;
    signal   lb_s2m        : in    t_lb_s2m;
    constant scope         : in    string                := C_SCOPE;
    constant msg_id_panel  : in    t_msg_id_panel        := shared_msg_id_panel;
    constant config        : in    t_localbus_bfm_config := C_LOCALBUS_BFM_CONFIG_DEFAULT);

  procedure localbus_read(
    constant addr_value    : in    std_logic_vector;
    variable data_value    : out   std_logic_vector;
    constant msg           : in    string;
    signal   clk           : in    std_logic;
    signal   lb_m2s        : inout t_lb_m2s;
    signal   lb_s2m        : in    t_lb_s2m;
    constant scope         : in    string                := C_SCOPE;
    constant msg_id_panel  : in    t_msg_id_panel        := shared_msg_id_panel;
    constant config        : in    t_localbus_bfm_config := C_LOCALBUS_BFM_CONFIG_DEFAULT);

  procedure localbus_check(
    constant addr_value    : in    std_logic_vector;
    constant data_exp      : in    std_logic_vector;
    constant msg           : in    string;
    signal   clk           : in    std_logic;
    signal   lb_m2s        : inout t_lb_m2s;
    signal   lb_s2m        : in    t_lb_s2m;
    constant alert_level   : in    t_alert_level         := error;
    constant scope         : in    string                := C_SCOPE;
    constant msg_id_panel  : in    t_msg_id_panel        := shared_msg_id_panel;
    constant config        : in    t_localbus_bfm_config := C_LOCALBUS_BFM_CONFIG_DEFAULT);

  -- Negative tests: drive a transaction and require err (not ack).
  procedure localbus_check_err(
    constant addr_value    : in    std_logic_vector;
    constant is_write      : in    boolean;
    constant msg           : in    string;
    signal   clk           : in    std_logic;
    signal   lb_m2s        : inout t_lb_m2s;
    signal   lb_s2m        : in    t_lb_s2m;
    constant alert_level   : in    t_alert_level         := error;
    constant scope         : in    string                := C_SCOPE;
    constant msg_id_panel  : in    t_msg_id_panel        := shared_msg_id_panel;
    constant config        : in    t_localbus_bfm_config := C_LOCALBUS_BFM_CONFIG_DEFAULT);

end package localbus_bfm_pkg;

package body localbus_bfm_pkg is

  -- Wait for the regfile to assert ack or err, sampling on the falling edge so
  -- the clocked response has settled. Times out after config.max_wait_cycles.
  procedure await_response(
    signal   clk          : in std_logic;
    signal   lb_s2m       : in t_lb_s2m;
    constant config       : in t_localbus_bfm_config;
    constant scope        : in string;
    constant proc_call    : in string) is
    variable v_cycles : integer := 0;
  begin
    loop
      wait until falling_edge(clk);
      exit when lb_s2m.ack = '1' or lb_s2m.err = '1';
      v_cycles := v_cycles + 1;
      if v_cycles >= config.max_wait_cycles then
        alert(config.max_wait_cycles_severity,
              proc_call & " timeout: no ack/err within " &
              integer'image(config.max_wait_cycles) & " cycles.", scope);
        exit;
      end if;
    end loop;
  end procedure;

  procedure localbus_write(
    constant addr_value    : in    std_logic_vector;
    constant data_value    : in    std_logic_vector;
    constant msg           : in    string;
    signal   clk           : in    std_logic;
    signal   lb_m2s        : inout t_lb_m2s;
    signal   lb_s2m        : in    t_lb_s2m;
    constant scope         : in    string                := C_SCOPE;
    constant msg_id_panel  : in    t_msg_id_panel        := shared_msg_id_panel;
    constant config        : in    t_localbus_bfm_config := C_LOCALBUS_BFM_CONFIG_DEFAULT) is
    constant proc_call : string := "localbus_write(0x" & to_hstring(addr_value) &
                                   ", 0x" & to_hstring(data_value) & ")";
    variable v_addr : std_logic_vector(lb_m2s.address'range) := (others => '0');
    variable v_data : std_logic_vector(lb_m2s.wdata'range)   := (others => '0');
  begin
    v_addr(addr_value'length-1 downto 0) := addr_value;
    v_data(data_value'length-1 downto 0) := data_value;

    wait until falling_edge(clk);
    lb_m2s.address <= v_addr;
    lb_m2s.wdata   <= v_data;
    lb_m2s.wen     <= '1';

    await_response(clk, lb_s2m, config, scope, proc_call);
    lb_m2s.wen <= '0';

    check_value(lb_s2m.ack = '1' and lb_s2m.err = '0', config.max_wait_cycles_severity,
                proc_call & " expected ack.", scope, msg_id => ID_NEVER,
                msg_id_panel => msg_id_panel);
    log(config.id_for_bfm, proc_call & " " & msg, scope, msg_id_panel);
  end procedure;

  procedure localbus_read(
    constant addr_value    : in    std_logic_vector;
    variable data_value    : out   std_logic_vector;
    constant msg           : in    string;
    signal   clk           : in    std_logic;
    signal   lb_m2s        : inout t_lb_m2s;
    signal   lb_s2m        : in    t_lb_s2m;
    constant scope         : in    string                := C_SCOPE;
    constant msg_id_panel  : in    t_msg_id_panel        := shared_msg_id_panel;
    constant config        : in    t_localbus_bfm_config := C_LOCALBUS_BFM_CONFIG_DEFAULT) is
    constant proc_call : string := "localbus_read(0x" & to_hstring(addr_value) & ")";
    variable v_addr : std_logic_vector(lb_m2s.address'range) := (others => '0');
  begin
    v_addr(addr_value'length-1 downto 0) := addr_value;

    wait until falling_edge(clk);
    lb_m2s.address <= v_addr;
    lb_m2s.ren     <= '1';

    await_response(clk, lb_s2m, config, scope, proc_call);
    lb_m2s.ren <= '0';

    check_value(lb_s2m.ack = '1' and lb_s2m.err = '0', config.max_wait_cycles_severity,
                proc_call & " expected ack.", scope, msg_id => ID_NEVER,
                msg_id_panel => msg_id_panel);
    data_value := lb_s2m.rdata(data_value'length-1 downto 0);
    log(config.id_for_bfm, proc_call & "=> 0x" & to_hstring(lb_s2m.rdata) & " " & msg,
        scope, msg_id_panel);
  end procedure;

  procedure localbus_check(
    constant addr_value    : in    std_logic_vector;
    constant data_exp      : in    std_logic_vector;
    constant msg           : in    string;
    signal   clk           : in    std_logic;
    signal   lb_m2s        : inout t_lb_m2s;
    signal   lb_s2m        : in    t_lb_s2m;
    constant alert_level   : in    t_alert_level         := error;
    constant scope         : in    string                := C_SCOPE;
    constant msg_id_panel  : in    t_msg_id_panel        := shared_msg_id_panel;
    constant config        : in    t_localbus_bfm_config := C_LOCALBUS_BFM_CONFIG_DEFAULT) is
    constant proc_call : string := "localbus_check(0x" & to_hstring(addr_value) &
                                   ", 0x" & to_hstring(data_exp) & ")";
    variable v_data : std_logic_vector(lb_s2m.rdata'range);
  begin
    localbus_read(addr_value, v_data, msg, clk, lb_m2s, lb_s2m, scope, msg_id_panel, config);
    check_value(v_data, std_logic_vector(resize(unsigned(data_exp), v_data'length)),
                alert_level, proc_call & " " & msg, scope, msg_id_panel => msg_id_panel);
  end procedure;

  procedure localbus_check_err(
    constant addr_value    : in    std_logic_vector;
    constant is_write      : in    boolean;
    constant msg           : in    string;
    signal   clk           : in    std_logic;
    signal   lb_m2s        : inout t_lb_m2s;
    signal   lb_s2m        : in    t_lb_s2m;
    constant alert_level   : in    t_alert_level         := error;
    constant scope         : in    string                := C_SCOPE;
    constant msg_id_panel  : in    t_msg_id_panel        := shared_msg_id_panel;
    constant config        : in    t_localbus_bfm_config := C_LOCALBUS_BFM_CONFIG_DEFAULT) is
    constant proc_call : string := "localbus_check_err(0x" & to_hstring(addr_value) & ")";
    variable v_addr : std_logic_vector(lb_m2s.address'range) := (others => '0');
  begin
    v_addr(addr_value'length-1 downto 0) := addr_value;

    wait until falling_edge(clk);
    lb_m2s.address <= v_addr;
    if is_write then
      lb_m2s.wdata <= (others => '0');
      lb_m2s.wen   <= '1';
    else
      lb_m2s.ren   <= '1';
    end if;

    await_response(clk, lb_s2m, config, scope, proc_call);
    lb_m2s.wen <= '0';
    lb_m2s.ren <= '0';

    check_value(lb_s2m.err = '1' and lb_s2m.ack = '0', alert_level,
                proc_call & " expected err. " & msg, scope, msg_id_panel => msg_id_panel);
    log(config.id_for_bfm, proc_call & " " & msg, scope, msg_id_panel);
  end procedure;

end package body localbus_bfm_pkg;
