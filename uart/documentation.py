from pylatexenc.latexencode import utf8tolatex
from uart.utils import indent_string


class Documentation(object):
    """Class for auto-generation of module documentation

    """

    

    
    def __init__(self, module):
        self.module = module

    def return_tex_documentation(self):
        s = tex_top
        s += "\n\n"
        s += r"\title{" + utf8tolatex(self.module.name) + "}\n"
        s += r"\author{}" + "\n"
        s += r"\date{}" + "\n"
        s += "\n"
        s += r"\begin{document}" + "\n"
        s += "\n"
        s += r"\maketitle" + "\n"
        s += "\n"
        s += r"\begin{description}[leftmargin=!,labelwidth=\widthof{\bfseries Address width: }]" + "\n"
        s += r"\item [Address width: ] " + utf8tolatex(str(self.module.addr_width)) + "\n"
        s += r"\item [Data width: ] " + utf8tolatex(str(self.module.data_width)) + "\n"
        s += r"\item [Base address: ] " + utf8tolatex("0x{0:0{1}X}".format(self.module.baseaddr, 8)) + "\n"
        s += r"\end{description}" + "\n\n\n"

        s += utf8tolatex(self.module.description) + "\n\n"

        s += r"\section{Register List}" + "\n\n"
        s += tex_table_top + "\n"
        for i, reg in enumerate(self.module.registers):
            p = str(i) + " & "
            p += utf8tolatex(reg.name) + " & "
            p += reg.mode.upper() + " & "
            p += r"\texttt{"
            p += '0x{0:0{1}X}'.format(reg.address, int(self.module.addr_width/4)) + "} & "
            p += reg.sig_type.upper() + " & "
            p += str(reg.length) + " & "
            p += r"\texttt{"
            p += '0x' + format(int(reg.reset, 16), 'X') + "} \\\\\n"
            p += r"\hline" + "\n"
            s += indent_string(p, 3)
        s += tex_table_bot

        s += "\n\n" r"\section{Registers}" + "\n\n"

        for reg in self.module.registers:

            s += r"\begin{register}{H}{" + utf8tolatex(reg.name) + " - "
            s += reg.mode.upper() + "}{" + '0x{0:0{1}X}'.format(reg.address, int(self.module.addr_width/4))
            s += "}\n"
            s += indent_string(r"\par " + utf8tolatex(reg.description) + r" \regnewline" + "\n")
            s += indent_string(r"\label{" + reg.name + "}\n")

            if reg.length < self.module.data_width:
                p = r"\regfield{unused}{"
                p += str(self.module.data_width - reg.length) + "}{"
                p += str(reg.length) + "}{-}\n"
                s += indent_string(p)

            if reg.sig_type != "fields":

                p = r"\regfield{}{" + str(reg.length) + "}{0}{"
                if reg.length < 2:
                    p += str(int(reg.reset, 16))
                else:
                    p += '{0x' + format(int(reg.reset, 16), 'X') + "}"
                p += "}\n"
                
                s += indent_string(p)

            else:
                for field in reversed(reg.fields):
                    p = r"\regfield{" + utf8tolatex(field.name) + "}{"
                    p += str(field.length) + "}{"
                    p += str(field.pos_low) + "}{"
                    if field.length < 2:
                        p += str(int(field.reset, 16))
                    else:
                        p += '{0x' + format(int(field.reset, 16), 'X') + "}"
                    p += "}\n"
                    s += indent_string(p)
    
            s += r"\reglabel{Reset}\regnewline" + "\n"

            if reg.sig_type == "fields":

                p = r"\begin{regdesc}\begin{reglist}["
                # Get the longest field name and indent the list based on that length
                gen = [field.name for field in reg.fields]
                longest = max(gen, key=len)
                p += utf8tolatex(longest)
                p += "]\n"
                s += indent_string(p)
                for field in reg.fields:
                    p = r"\item [" + utf8tolatex(field.name) + "] "
                    p += utf8tolatex(field.description)
                    s += indent_string(p, 2)
                s += indent_string(r"\end{reglist}\end{regdesc}" + "\n")

            s += r"\end{register}" + "\n\n"

        s += tex_bot

        return s


tex_top = r"""\documentclass{article}
\usepackage[margin=1in]{geometry}
\usepackage{register}
\usepackage{enumitem}
\setlist[description]{leftmargin=\parindent,labelindent=\parindent}
\usepackage{calc}
\usepackage{tabularx}

\usepackage{listings}
\lstdefinelanguage{VHDL}{
   morekeywords=[1]{
     library,use,all,entity,is,port,in,out,end,architecture,of,
     begin,and,others
   },
   morecomment=[l]--
}
 
\lstdefinestyle{vhdl}{
   language     = VHDL,
   basicstyle   = \ttfamily,
}"""

tex_bot = r"""\section{Example VHDL Register Access}

\par
All registers are bundled in records based on their mode. E.g. all RW registers are accessed through the record \textit{bustype\_rw\_regs}. Access is also dependent on the type of register. All register of type SL, SLV and DEFAULT are all directly accessed by just specifying the mode record signal. E.g. the RW register \textit{reg0} can be assigned a value like this (assuming AXI-bus):

\begin{lstlisting}[style=vhdl]
axi_rw_regs.reg0 <= (others => '0');
\end{lstlisting}

\par Registers of type FIELD cannot be directly accessed without specification of a certain field. This is because the registers are implemented as a record in VHDL (thus a record of records). E.g. if the RO register \textit{reg1} contains the field \textit{field3} it can be accessed like this (assuming AXI-bus):

\begin{lstlisting}[style=vhdl]
axi_ro_regs.reg1.field3 <= (others => '0');
\end{lstlisting}

\end{document}"""


tex_table_top = r"""\begin{table}[h!]
  \begin{center}
    \label{tab:table1}
    \begin{tabularx}{\linewidth}{|l|X|l|l|l|c|l|}
      \hline
      \textbf{\#} & \textbf{Name} & \textbf{Mode} & \textbf{Address} & \textbf{Type} & \textbf{Length} &
      \textbf{Reset} \\
      \hline"""

tex_table_bot = r"""    \end{tabularx}
  \end{center}
\end{table}"""
