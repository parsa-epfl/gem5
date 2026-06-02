# -*- mode:python -*-

from m5.SimObject import SimObject
from m5.params import *


class ArmTLBRestorer(SimObject):
    type = "ArmTLBRestorer"
    cxx_class = "gem5::ArmISA::TLBRestorer"
    cxx_header = "arch/arm/tlb_restorer.hh"

    cpu = Param.BaseCPU("CPU whose TLBs will be restored")
    itb = Param.ArmTLB("Instruction TLB (ArmITB from cpu.mmu)")
    dtb = Param.ArmTLB("Data TLB (ArmDTB from cpu.mmu)")
    cpu_id = Param.Int(0, "CPU index used for checkpoint section naming")
    checkpoint_file = Param.String(
        "",
        "Path to mmu-cpuN.cpt sidecar checkpoint file",
    )
