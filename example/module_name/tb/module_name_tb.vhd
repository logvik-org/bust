library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library uvvm_util;
context uvvm_util.uvvm_util_context;

library uvvm_vvc_framework;
use uvvm_vvc_framework.ti_vvc_framework_support_pkg.all;

library bitvis_vip_axilite;
use bitvis_vip_axilite.axilite_bfm_pkg.all;
use bitvis_vip_axilite.vvc_methods_pkg.all;
use bitvis_vip_axilite.td_vvc_framework_common_methods_pkg.all;

entity module_name_tb is
end entity module_name_tb;


architecture func of module_name_tb is

  constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;
  constant C_CLK_PERIOD : time   := 10 ns;

  -- Log overload procedure for simplification
  procedure log(
    msg : string) is
  begin
    log(ID_SEQUENCER, msg, C_SCOPE);
  end;

begin  -- architecture func

  -----------------------------------------------------------------------------
  -- Instantiate test harness, containing DUT and Executors
  -----------------------------------------------------------------------------
  module_name_th_i : entity work.module_name_th;


  -- PROCESS: p_main
  ------------------------------------------------
  p_main : process
  begin

    -- Wait for UVVM to finish initialization
    await_uvvm_initialization(VOID);

    -- Print the configuration to the log
    report_global_ctrl(VOID);
    report_msg_id_panel(VOID);

    --enable_log_msg(ALL_MESSAGES);
    disable_log_msg(ALL_MESSAGES);
    enable_log_msg(ID_LOG_HDR);
    enable_log_msg(ID_SEQUENCER);
    enable_log_msg(ID_UVVM_SEND_CMD);

    disable_log_msg(AXILITE_VVCT, 0, ALL_MESSAGES);
    enable_log_msg(AXILITE_VVCT, 0, ID_BFM);
    enable_log_msg(AXILITE_VVCT, 0, ID_FINISH_OR_STOP);

    shared_axilite_vvc_config(0).inter_bfm_delay.delay_type    := TIME_FINISH2START;
    shared_axilite_vvc_config(0).inter_bfm_delay.delay_in_time := 0*C_CLK_PERIOD;



    log(ID_LOG_HDR, "Starting simulation of TB for UART using VVCs", C_SCOPE);
    ------------------------------------------------------------

    log("Wait 10 clock period for reset to be turned off");
    wait for (10 * C_CLK_PERIOD);       -- for reset to be turned off

    axilite_check(AXILITE_VVCT, 0, 32X"0", 32X"0", "Reg check");
    axilite_write(AXILITE_VVCT, 0, 32X"0", 9X"1A5", "Reg check");
    axilite_check(AXILITE_VVCT, 0, 32X"0", 32X"1A5", "Reg check");

    axilite_check(AXILITE_VVCT, 0, 32X"2", 32X"0", "Reg check");
    axilite_write(AXILITE_VVCT, 0, 32X"2", 16X"A5A5", "Reg check");
    axilite_check(AXILITE_VVCT, 0, 32X"2", 32X"A5A5", "Reg check");

    axilite_check(AXILITE_VVCT, 0, 32X"4", 32X"0", "Reg check");
    axilite_write(AXILITE_VVCT, 0, 32X"4", 1X"1", "Reg check");
    axilite_check(AXILITE_VVCT, 0, 32X"4", 32X"1", "Reg check");

    axilite_check(AXILITE_VVCT, 0, 32X"6", 32X"A5", "Reg check");

    axilite_check(AXILITE_VVCT, 0, 32X"8", 32X"4F", "Reg check");

    await_completion(AXILITE_VVCT, 0, 2500 us);

    -----------------------------------------------------------------------------
    -- Ending the simulation
    -----------------------------------------------------------------------------
    wait for 1000 ns;                   -- to allow some time for completion
    report_alert_counters(FINAL);  -- Report final counters and print conclusion for simulation (Success/Fail)
    log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);

    -- Finish the simulation
    std.env.stop;
    wait;                               -- to stop completely

  end process p_main;


end architecture func;
