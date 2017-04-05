## The attributes of a axi data register
#
# @param name The name of the register, to be used in the reg record \n
# @param mode (r/rw) - true -> rw, false -> ro \n
# @param number Which regnumber in the module, word-addressable \n
class Reg(object):
    size = 0

    ## Constructor
    def __init__(self, name, mode, number=None):
        self.name = name
        self.mode = mode
        if number is None:
            self.number = Reg.size
        else:
            self.number = number
        Reg.size += 1
