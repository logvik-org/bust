-- APB (AMBA APB) wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output). UVVM ships no APB VIP, so it
-- is verified with a small hand-written APB master BFM in the testbench, proving
-- the APB-to-local-bus bridge before the generator emits it.
--
-- APB is a two-phase protocol: a SETUP cycle (psel asserted, penable low) is
-- followed by one or more ACCESS cycles (psel and penable both high) until the
-- slave raises pready. The bridge starts the local-bus transaction on the SETUP
-- cycle so the regfile's one-cycle latency overlaps the first ACCESS cycle, holds
-- until the regfile answers, then raises pready for one clock with prdata valid.
-- The SETUP phase (penable low) delimits every transfer, so no extra re-trigger
-- guard is needed. APB has a native pslverr, so a regfile decode error maps to
-- pslverr (prdata still forced to 0). APB's reset (presetn) is active-low and
-- async, handed to the regfile via G_RESET_ACTIVE_LOW; the master drives a byte
-- address mapped directly onto the local bus.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_apb_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
  );
  port (
    pclk    : in  std_logic;
    presetn : in  std_logic;

    -- APB subordinate interface
    psel    : in  std_logic;
    penable : in  std_logic;
    pwrite  : in  std_logic;
    paddr   : in  std_logic_vector(31 downto 0);
    pwdata  : in  std_logic_vector(31 downto 0);
    prdata  : out std_logic_vector(31 downto 0);
    pready  : out std_logic;
    pslverr : out std_logic;

    -- hardware side of the register file
    to_hw   : out t_prototype_to_hw;
    from_hw : in  t_prototype_from_hw
  );
end entity prototype_apb_endpoint;

architecture rtl of prototype_apb_endpoint is

  type t_state is (ST_IDLE, ST_ACCESS);
  signal state : t_state := ST_IDLE;

  signal m2s : t_lb_m2s := C_LB_M2S_IDLE;
  signal s2m : t_lb_s2m;

  signal prdata_i  : std_logic_vector(31 downto 0) := (others => '0');
  signal pready_i  : std_logic := '0';
  signal pslverr_i : std_logic := '0';

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_RESET_ACTIVE_LOW   => true)       -- APB presetn is active-low
    port map (
      clk     => pclk,
      reset   => presetn,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_apb : process (pclk, presetn) is
  begin
    if presetn = '0' then
      state     <= ST_IDLE;
      m2s       <= C_LB_M2S_IDLE;
      prdata_i  <= (others => '0');
      pready_i  <= '0';
      pslverr_i <= '0';
    elsif rising_edge(pclk) then
      pready_i  <= '0';                   -- pready/pslverr are single-cycle beats
      pslverr_i <= '0';

      case state is
        when ST_IDLE =>
          -- SETUP cycle: psel high, penable low. Latch the request and start the
          -- local-bus transaction so its latency overlaps the ACCESS phase.
          if psel = '1' and penable = '0' then
            m2s.address <= paddr;
            m2s.wdata   <= pwdata;
            m2s.wen     <= pwrite;
            m2s.ren     <= not pwrite;
            state       <= ST_ACCESS;
          end if;

        when ST_ACCESS =>
          if s2m.ack = '1' or s2m.err = '1' then
            m2s.wen   <= '0';
            m2s.ren   <= '0';
            prdata_i  <= (others => '0');
            pslverr_i <= s2m.err;
            if s2m.err = '0' then
              prdata_i <= s2m.rdata;
            end if;
            pready_i <= '1';
            state    <= ST_IDLE;
          end if;
      end case;
    end if;
  end process p_apb;

  prdata  <= prdata_i;
  pready  <= pready_i;
  pslverr <= pslverr_i;

end architecture rtl;
