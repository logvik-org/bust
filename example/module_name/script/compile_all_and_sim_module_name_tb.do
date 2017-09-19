if {[batch_mode]} {
  onerror {abort all; exit -f -code 1}
  onbreak {abort all; exit -f}
} else {
  onerror {abort all}
}

quit -sim

# Argument number 1 : VHDL Version. Default 2002
quietly set vhdl_version "2008"
if { [info exists 1] } {
  quietly set vhdl_version "$1"
  unset 1
}

quietly set tb_part_path ../../module_name
do $tb_part_path/script/1_compile_src.do  $tb_part_path $vhdl_version
do $tb_part_path/script/2_compile_util.do $tb_part_path $vhdl_version
do $tb_part_path/script/3_compile_tb_dep_ex_util.do $tb_part_path $vhdl_version
do $tb_part_path/script/4_compile_module_name_tb.do  $tb_part_path $vhdl_version
do $tb_part_path/script/5_simulate_module_name_tb.do $tb_part_path $vhdl_version


