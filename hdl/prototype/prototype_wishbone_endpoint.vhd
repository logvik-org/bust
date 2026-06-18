-- Wishbone (B4 classic) wrapper prototype for the local-bus register file.
-- One of the protocol wrappers in the target architecture:
--   <bus> wrapper -> local bus (t_lb_m2s / t_lb_s2m) -> regfile
-- Hand-written reference HDL (not generator output). UVVM ships no Wishbone VIP,
-- so it is verified with a small hand-written classic-cycle Wishbone master BFM
-- in the testbench, proving the Wishbone-to-local-bus bridge before the
-- generator emits it.
--
-- Classic Wishbone is a single-beat, hold-until-ack protocol, so the bridge is
-- thin and mirrors the IPBus endpoint: a qualified cycle (cyc_i and stb_i) starts
-- one local-bus transaction (we_i selects write vs read), held until the regfile
-- answers, then ack_o or err_o is pulsed for one clock with dat_o valid. Wishbone
-- has a native err_o line, so a regfile decode error maps to err_o (unlike SBI,
-- where it folds into the single ready beat); dat_o is still forced to 0 on err
-- so reads of invalid addresses are deterministic. A one-cycle guard (ack_o/err_o
-- still registered high the cycle after BUSY) blocks re-triggering the
-- just-completed cycle. Wishbone's sync active-high reset passes straight to the
-- regfile, and the master drives a byte address mapped directly onto the local
-- bus.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

use work.localbus_pkg.all;
use work.prototype_regfile_pkg.all;

entity prototype_wishbone_endpoint is
  generic (
    G_BASE_ADDRESS       : unsigned(31 downto 0) := x"00000000";
    G_CHECK_BASE_ADDRESS : boolean               := true
  );
  port (
    clk_i   : in  std_logic;
    rst_i   : in  std_logic;

    -- Wishbone B4 classic subordinate interface
    cyc_i   : in  std_logic;
    stb_i   : in  std_logic;
    we_i    : in  std_logic;
    adr_i   : in  std_logic_vector(31 downto 0);
    dat_i   : in  std_logic_vector(31 downto 0);
    dat_o   : out std_logic_vector(31 downto 0);
    ack_o   : out std_logic;
    err_o   : out std_logic;

    -- hardware side of the register file
    to_hw   : out t_prototype_to_hw;
    from_hw : in  t_prototype_from_hw
  );
end entity prototype_wishbone_endpoint;

architecture rtl of prototype_wishbone_endpoint is

  type t_state is (ST_IDLE, ST_BUSY);
  signal state : t_state := ST_IDLE;

  signal m2s : t_lb_m2s := C_LB_M2S_IDLE;
  signal s2m : t_lb_s2m;

  signal dat_o_i : std_logic_vector(31 downto 0) := (others => '0');
  signal ack_o_i : std_logic := '0';
  signal err_o_i : std_logic := '0';

begin

  i_regfile : entity work.prototype_regfile
    generic map (
      G_BASE_ADDRESS       => G_BASE_ADDRESS,
      G_CHECK_BASE_ADDRESS => G_CHECK_BASE_ADDRESS,
      G_RESET_ACTIVE_LOW   => false)      -- Wishbone reset is sync active-high
    port map (
      clk     => clk_i,
      reset   => rst_i,
      lb_m2s  => m2s,
      lb_s2m  => s2m,
      to_hw   => to_hw,
      from_hw => from_hw);

  p_wb : process (clk_i) is
  begin
    if rising_edge(clk_i) then
      if rst_i = '1' then
        state   <= ST_IDLE;
        m2s     <= C_LB_M2S_IDLE;
        dat_o_i <= (others => '0');
        ack_o_i <= '0';
        err_o_i <= '0';
      else
        ack_o_i <= '0';                   -- ack/err are single-cycle
        err_o_i <= '0';

        case state is
          when ST_IDLE =>
            -- Start a qualified classic cycle, but not while still presenting a
            -- response (ack/err high): that gates re-triggering the just-acked
            -- cycle and handles a master that holds cyc/stb across beats.
            if cyc_i = '1' and stb_i = '1'
               and ack_o_i = '0' and err_o_i = '0' then
              m2s.address <= adr_i;
              m2s.wdata   <= dat_i;
              m2s.wen     <= we_i;
              m2s.ren     <= not we_i;
              state       <= ST_BUSY;
            end if;

          when ST_BUSY =>
            if s2m.ack = '1' or s2m.err = '1' then
              m2s.wen <= '0';
              m2s.ren <= '0';
              if s2m.err = '1' then
                dat_o_i <= (others => '0');
                err_o_i <= '1';
              else
                dat_o_i <= s2m.rdata;
                ack_o_i <= '1';
              end if;
              state <= ST_IDLE;
            end if;
        end case;
      end if;
    end if;
  end process p_wb;

  dat_o <= dat_o_i;
  ack_o <= ack_o_i;
  err_o <= err_o_i;

end architecture rtl;
