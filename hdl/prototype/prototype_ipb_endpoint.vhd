-- IPBus wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output), verified with the stock
-- vip_ipbus VIP, proving the IPBus-to-local-bus bridge before the generator
-- emits it.
--
-- IPBus is itself a single-beat, hold-until-ack protocol, so the bridge is thin:
-- a strobe starts one local-bus transaction (wen for write, ren for read),
-- held until the regfile answers with ack/err, which is forwarded back as
-- ipb_ack/ipb_err. The address is forwarded unchanged; the regfile slices the
-- module window from it (low bits select the register, upper bits check the
-- base), exactly as the AXI endpoint and the v1 PIFs do. IPBus's sync
-- active-high reset is passed straight to the regfile.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library ipbus;
use ipbus.ipbus.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_ipb_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
  );
  port (
    clk     : in  std_logic;
    reset   : in  std_logic;
    ipb_in  : in  ipb_wbus;
    ipb_out : out ipb_rbus;
    to_hw   : out t_prototype_to_hw;
    from_hw : in  t_prototype_from_hw
  );
end entity prototype_ipb_endpoint;

architecture rtl of prototype_ipb_endpoint is

  type t_state is (ST_IDLE, ST_BUSY);
  signal state : t_state := ST_IDLE;

  signal m2s : t_lb_m2s := C_LB_M2S_IDLE;
  signal s2m : t_lb_s2m;

  signal ipb_out_i : ipb_rbus := (ipb_rdata => (others => '0'),
                                  ipb_ack   => '0',
                                  ipb_err   => '0');

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_RESET_ACTIVE_LOW   => false)      -- IPBus reset is sync active-high
    port map (
      clk     => clk,
      reset   => reset,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_ipb : process (clk) is
  begin
    if rising_edge(clk) then
      if reset = '1' then
        state     <= ST_IDLE;
        m2s       <= C_LB_M2S_IDLE;
        ipb_out_i <= (ipb_rdata => (others => '0'), ipb_ack => '0', ipb_err => '0');
      else
        -- ack/err are single-cycle.
        ipb_out_i.ipb_ack <= '0';
        ipb_out_i.ipb_err <= '0';

        case state is
          when ST_IDLE =>
            -- Start on a strobe, but not while still presenting a response
            -- (ack/err high). This gates re-triggering the just-acked access
            -- and handles back-to-back strobes without the master having to
            -- drop strobe between transactions.
            if ipb_in.ipb_strobe = '1'
               and ipb_out_i.ipb_ack = '0' and ipb_out_i.ipb_err = '0' then
              m2s.address <= ipb_in.ipb_addr;
              m2s.wdata   <= ipb_in.ipb_wdata;
              m2s.wen     <= ipb_in.ipb_write;
              m2s.ren     <= not ipb_in.ipb_write;
              state       <= ST_BUSY;
            end if;

          when ST_BUSY =>
            if s2m.ack = '1' or s2m.err = '1' then
              m2s.wen             <= '0';
              m2s.ren             <= '0';
              ipb_out_i.ipb_rdata <= s2m.rdata;
              ipb_out_i.ipb_ack   <= s2m.ack;
              ipb_out_i.ipb_err   <= s2m.err;
              state               <= ST_IDLE;
            end if;
        end case;
      end if;
    end if;
  end process p_ipb;

  ipb_out <= ipb_out_i;

end architecture rtl;
