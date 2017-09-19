if {[batch_mode]} {
  onerror {abort all; exit -f -code 1}
} else {
  onerror {abort all}
}
#Just in case...
quietly quit -sim   


# Set up module_name_path and lib_name
#------------------------------------------------------
quietly set lib_name "module_name"
quietly set part_name "module_name"
# path from mpf-file in sim
quietly set module_name_part_path "../..//$part_name"

if { [info exists 1] } {
  # path from this part to target part
  quietly set module_name_part_path "$1/..//$part_name"
  unset 1
}


# (Re-)Generate library and Compile source files
#--------------------------------------------------
echo "\n\nRe-gen lib and compile $lib_name source\n"
if {[file exists $module_name_part_path/sim/$lib_name]} {
  file delete -force $module_name_part_path/sim/$lib_name
}
if {![file exists $module_name_part_path/sim]} {
  file mkdir $module_name_part_path/sim
}

vlib $module_name_part_path/sim/$lib_name
vmap $lib_name $module_name_part_path/sim/$lib_name

set compdirectives "-2008 -work $lib_name"

eval vcom  $compdirectives  $module_name_part_path/hdl/axi_pkg.vhd
eval vcom  $compdirectives  $module_name_part_path/hdl/module_name_pkg.vhd
eval vcom  $compdirectives  $module_name_part_path/hdl/module_name_axi_handler.vhd
eval vcom  $compdirectives  $module_name_part_path/hdl/module_name.vhd

