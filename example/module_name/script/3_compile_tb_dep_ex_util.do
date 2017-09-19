# This file may be called with an argument
# arg 1: Part directory of this library/module

# Overload quietly (Modelsim specific command) to let it work in Riviera-Pro
proc quietly { args } {
  if {[llength $args] == 0} {
    puts "quietly"
  } else {
    # this works since tcl prompt only prints the last command given. list prints "".
    uplevel $args; list;
  }
}

if {[batch_mode]} {
  onerror {abort all; exit -f -code 1}
} else {
  onerror {abort all}
}
#Just in case...
quietly quit -sim   

# Set up part_path for uvvm_vvc_framework
#------------------------------------------------------
quietly set part_name "uvvm_vvc_framework"
# path from mpf-file in sim
quietly set uvvm_part_path "../../$part_name"

if { [info exists 1] } {
  # path from this part to target part
  quietly set uvvm_part_path "$1/../$part_name"
  unset 1
}

do $uvvm_part_path/script/compile_src.do $uvvm_part_path

# Compile Bitvis VIP axilite
#----------------------------------

# Set up vip_axilite_part_path
#------------------------------------------------------
quietly set part_name "bitvis_vip_axilite"
# path from mpf-file in sim
quietly set vip_axilite_part_path "../../$part_name"

if { [info exists 1] } {
  # path from this part to target part
  quietly set vip_axilite_part_path "$1/../$part_name"
  unset 1
}

do $vip_axilite_part_path/script/compile_src.do $vip_axilite_part_path
